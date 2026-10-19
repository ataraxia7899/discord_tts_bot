"""네트워크나 Discord 접속 없이 실행하는 TTS 회귀 테스트."""
import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import discord

from src.config import Config, SettingsSaveError
from src.commands import setup as commands
from src.handlers import message_handler as handler
from src.tts import edge_tts_engine as engine

original_sleep = asyncio.sleep


def response_error(status, retry_after=None):
    headers = {} if retry_after is None else {'Retry-After': retry_after}
    return aiohttp.WSServerHandshakeError(
        NS(real_url='https://tts.invalid'), (), status=status, headers=headers
    )


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        engine._generation_semaphore = asyncio.Semaphore(1)
        engine._cooldown_until = 0.0
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.filename = str(Path(self.directory.name) / 'audio.mp3')

    async def check_retries(self, errors):
        delays = []
        attempts = iter(errors)

        async def save(filename):
            Path(filename).write_bytes(b'partial')
            error = next(attempts, None)
            if error:
                raise error
            Path(filename).write_bytes(b'complete audio')

        async def sleep(delay):
            delays.append(delay)
            engine._cooldown_until = 0.0

        factory = Mock(return_value=NS(save=AsyncMock(side_effect=save)))
        with patch.object(engine.edge_tts, 'Communicate', factory), \
             patch.object(engine.random, 'uniform', return_value=0), \
             patch.object(engine.asyncio, 'sleep', sleep):
            await engine.EdgeTTSEngine().generate('text', self.filename)
        self.assertEqual(Path(self.filename).read_bytes(), b'complete audio')
        return factory, delays

    async def test_429_exponential_backoff_and_new_communicate_each_attempt(self):
        factory, delays = await self.check_retries([response_error(429) for _ in range(3)])
        self.assertEqual(factory.call_count, 4)
        for actual, expected in zip(delays, [2, 4, 8]):
            self.assertAlmostEqual(actual, expected, delta=0.1)

    async def test_retry_after_is_respected(self):
        _, delays = await self.check_retries([response_error(429, '12')])
        self.assertAlmostEqual(delays[0], 12, delta=0.1)

    async def test_transient_network_error_retries(self):
        _, delays = await self.check_retries([aiohttp.ClientConnectionError()])
        self.assertEqual(delays, [2])

    async def test_non_retryable_error_fails_immediately_and_removes_partial_audio(self):
        async def save(filename):
            Path(filename).write_bytes(b'partial')
            raise response_error(401)

        save_mock = AsyncMock(side_effect=save)
        with patch.object(engine.edge_tts, 'Communicate', return_value=NS(save=save_mock)):
            with self.assertRaises(aiohttp.ClientResponseError):
                await engine.EdgeTTSEngine().generate('text', self.filename)
        self.assertEqual(save_mock.await_count, 1)
        self.assertFalse(Path(self.filename).exists())

    async def test_retry_limit_and_empty_audio_cleanup(self):
        async def save(filename):
            Path(filename).write_bytes(b'')

        save_mock = AsyncMock(side_effect=save)
        with patch.object(engine.edge_tts, 'Communicate', return_value=NS(save=save_mock)), \
             patch.object(engine.asyncio, 'sleep', AsyncMock()):
            with self.assertRaises(engine.NoAudioReceived):
                await engine.EdgeTTSEngine().generate('text', self.filename)
        self.assertEqual(save_mock.await_count, 4)
        self.assertFalse(Path(self.filename).exists())

    async def test_global_concurrency_limit_across_engines(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        active = 0
        maximum = 0

        async def save(filename):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            entered.set()
            try:
                await release.wait()
                Path(filename).write_bytes(b'audio')
            finally:
                active -= 1

        factory = Mock(return_value=NS(save=AsyncMock(side_effect=save)))
        with patch.object(engine.edge_tts, 'Communicate', factory):
            first = asyncio.create_task(engine.EdgeTTSEngine().generate('one', self.filename))
            await entered.wait()
            second = asyncio.create_task(engine.EdgeTTSEngine().generate(
                'two', str(Path(self.directory.name) / 'second.mp3')
            ))
            await original_sleep(0)
            self.assertEqual(factory.call_count, 1)
            release.set()
            await asyncio.gather(first, second)
        self.assertEqual(maximum, 1)

    async def test_cancelled_backoff_preserves_cooldown_for_other_guilds(self):
        async def cancelled_sleep(delay):
            raise asyncio.CancelledError()

        with patch.object(engine.edge_tts, 'Communicate', return_value=NS(
                save=AsyncMock(side_effect=response_error(429, '15')))), \
             patch.object(engine.asyncio, 'sleep', cancelled_sleep):
            with self.assertRaises(asyncio.CancelledError):
                await engine.EdgeTTSEngine().generate('text', self.filename)
        self.assertFalse(Path(self.filename).exists())

        async def save(filename):
            Path(filename).write_bytes(b'audio')

        sleep_mock = AsyncMock()
        with patch.object(engine.edge_tts, 'Communicate', return_value=NS(save=save)), \
             patch.object(engine.asyncio, 'sleep', sleep_mock):
            await engine.EdgeTTSEngine().generate('next guild', self.filename)
        self.assertGreater(sleep_mock.call_args.args[0], 14)

    def test_retry_after_http_date_and_invalid_values(self):
        date = datetime.now(timezone.utc) + timedelta(seconds=30)
        self.assertGreater(engine.retry_after_seconds(format_datetime(date)), 28)
        for value in [None, '', '-5', 'invalid', 'nan', 'inf']:
            self.assertEqual(engine.retry_after_seconds(value), 0)


class FakeVoiceClient:
    def __init__(self):
        self.source = None
        self.connected = True
        self.channel = NS(name='voice')
        self.after = None

    def is_connected(self):
        return self.connected

    def is_playing(self):
        return self.source is not None

    def is_paused(self):
        return False

    def play(self, source, after):
        self.source = source
        self.after = after

    def stop(self):
        self.source = None
        if self.after:
            self.after(None)
            self.after = None

    async def disconnect(self, **kwargs):
        self.stop()
        self.connected = False


class PlaybackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handler.playback_states.clear()
        handler.tts_engines.clear()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        original_mkstemp = tempfile.mkstemp
        self.patchers = [
            patch.object(handler.tempfile, 'mkstemp', side_effect=lambda **kwargs:
                         original_mkstemp(dir=self.directory.name, **kwargs)),
            patch.object(handler, 'get_tts_engine', return_value=NS(generate=self.generate)),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.voice = FakeVoiceClient()
        self.config = NS()
        self.state = handler.get_playback_state(1)

    async def asyncTearDown(self):
        await handler.clear_playback(1, self.voice)

    async def generate(self, text, filename):
        Path(filename).write_bytes(text.encode())

    async def enqueue(self, text):
        async with self.state.lock:
            return handler.enqueue_tts(1, text, self.voice, self.config, self.state)

    async def test_simultaneous_messages_have_one_worker(self):
        entered = asyncio.Event()

        async def generation(text, filename):
            entered.set()
            await asyncio.Event().wait()

        with patch.object(handler, 'get_tts_engine', return_value=NS(generate=generation)), \
             patch.object(handler, 'play_tts_loop', wraps=handler.play_tts_loop) as worker:
            await asyncio.gather(self.enqueue('one'), self.enqueue('two'))
            await entered.wait()
            self.assertEqual(worker.call_count, 1)
            await handler.clear_playback(1, self.voice)

    async def test_queue_has_a_hard_limit(self):
        async with self.state.lock:
            for index in range(handler.MAX_QUEUE_SIZE):
                self.assertTrue(handler.enqueue_tts(1, str(index), self.voice, self.config, self.state))
            self.assertFalse(handler.enqueue_tts(1, 'overflow', self.voice, self.config, self.state))
        self.assertEqual(self.state.queue.qsize(), handler.MAX_QUEUE_SIZE)

    async def test_failed_generation_never_starts_ffmpeg_and_next_message_can_play(self):
        async def generation(text, filename):
            Path(filename).write_bytes(b'partial')
            if text == 'fail':
                raise RuntimeError('generation failed')

        played = []

        async def play(voice, filename):
            played.append(Path(filename).read_bytes())
            handler.remove_audio(filename)

        with patch.object(handler, 'get_tts_engine', return_value=NS(generate=generation)), \
             patch.object(handler.discord, 'FFmpegOpusAudio') as ffmpeg, \
             patch.object(handler, 'play_from_file', play):
            await self.enqueue('fail')
            await self.enqueue('success')
            await self.state.worker
            ffmpeg.assert_not_called()
        self.assertEqual(played, [b'partial'])
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_empty_generation_never_starts_ffmpeg(self):
        async def generation(text, filename):
            pass

        with patch.object(handler, 'get_tts_engine', return_value=NS(generate=generation)), \
             patch.object(handler.discord, 'FFmpegOpusAudio') as ffmpeg:
            await self.enqueue('empty')
            await self.state.worker
            ffmpeg.assert_not_called()
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_clear_during_generation_deletes_partial_file(self):
        entered = asyncio.Event()

        async def generation(text, filename):
            Path(filename).write_bytes(b'partial')
            entered.set()
            await asyncio.Event().wait()

        with patch.object(handler, 'get_tts_engine', return_value=NS(generate=generation)), \
             patch.object(handler.discord, 'FFmpegOpusAudio') as ffmpeg:
            await self.enqueue('cancel me')
            await entered.wait()
            await handler.clear_playback(1, self.voice)
            ffmpeg.assert_not_called()
        self.assertIsNone(self.state.worker)
        self.assertIsNone(self.state.generation)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def check_clear_prefetch(self, generating):
        prefetched = asyncio.Event()
        played = []

        async def generation(text, filename):
            await self.generate(text, filename)
            if text == 'second':
                prefetched.set()
                if generating:
                    await asyncio.Event().wait()

        async def play(voice, filename):
            played.append(Path(filename).read_text())
            await asyncio.Event().wait()

        with patch.object(handler, 'get_tts_engine', return_value=NS(generate=generation)), \
             patch.object(handler, 'play_from_file', play):
            await self.enqueue('first')
            await self.enqueue('second')
            await prefetched.wait()
            await original_sleep(0)
            await handler.clear_playback(1, self.voice)
        self.assertEqual(played, ['first'])
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])
        self.assertIsNone(self.state.worker)

    async def test_clear_removes_completed_prefetch(self):
        await self.check_clear_prefetch(generating=False)

    async def test_clear_cancels_in_progress_prefetch(self):
        await self.check_clear_prefetch(generating=True)

    async def test_clear_then_new_message_plays_normally(self):
        entered = asyncio.Event()
        played = []

        async def play(voice, filename):
            text = Path(filename).read_text()
            played.append(text)
            if text == 'old':
                entered.set()
                await asyncio.Event().wait()
            handler.remove_audio(filename)

        with patch.object(handler, 'play_from_file', play):
            await self.enqueue('old')
            await entered.wait()
            await handler.clear_playback(1, self.voice)
            await self.enqueue('new')
            await self.state.worker
        self.assertEqual(played, ['old', 'new'])
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_cancelled_playback_stops_source_and_cleans_audio(self):
        filename = Path(self.directory.name) / 'audio.mp3'
        filename.write_bytes(b'audio')
        source = Mock()
        with patch.object(handler.discord, 'FFmpegOpusAudio', return_value=source):
            task = asyncio.create_task(handler.play_from_file(self.voice, str(filename)))
            await original_sleep(0)
            self.assertIs(self.voice.source, source)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            # A late callback must be ignored after cancellation.
            await original_sleep(0)
        source.cleanup.assert_called_once()
        self.assertFalse(filename.exists())
        self.assertIsNone(self.voice.source)

    async def test_clear_cancels_429_backoff_without_starting_ffmpeg(self):
        engine._generation_semaphore = asyncio.Semaphore(1)
        engine._cooldown_until = 0
        sleeping = asyncio.Event()

        async def sleep(delay):
            sleeping.set()
            await asyncio.Event().wait()

        with patch.object(handler, 'get_tts_engine', return_value=engine.EdgeTTSEngine()), \
             patch.object(engine.edge_tts, 'Communicate', return_value=NS(
                 save=AsyncMock(side_effect=response_error(429, '15')))), \
             patch.object(engine.asyncio, 'sleep', sleep), \
             patch.object(handler.discord, 'FFmpegOpusAudio') as ffmpeg:
            await self.enqueue('rate limited')
            await sleeping.wait()
            await handler.clear_playback(1, self.voice)
            ffmpeg.assert_not_called()
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])
        self.assertGreater(engine._cooldown_until, asyncio.get_running_loop().time())

    async def test_new_message_waits_for_clear_cleanup(self):
        playing = asyncio.Event()
        cleaning = asyncio.Event()
        release = asyncio.Event()
        played = []

        async def play(voice, filename):
            text = Path(filename).read_text()
            played.append(text)
            if text == 'old':
                playing.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaning.set()
                    await release.wait()
            handler.remove_audio(filename)

        with patch.object(handler, 'play_from_file', play):
            await self.enqueue('old')
            await playing.wait()
            clear_task = asyncio.create_task(handler.clear_playback(1, self.voice))
            await cleaning.wait()
            enqueue_task = asyncio.create_task(self.enqueue('new'))
            await original_sleep(0)
            self.assertFalse(enqueue_task.done())
            release.set()
            await clear_task
            await enqueue_task
            await self.state.worker
        self.assertEqual(played, ['old', 'new'])
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_playback_timeout_ignores_late_callback(self):
        filename = Path(self.directory.name) / 'timeout.mp3'
        filename.write_bytes(b'audio')
        source = Mock()
        errors = []
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        try:
            with patch.object(handler.discord, 'FFmpegOpusAudio', return_value=source), \
                 patch.object(handler, 'PLAYBACK_TIMEOUT', 0.001):
                await handler.play_from_file(self.voice, str(filename))
                await original_sleep(0)
            self.assertEqual(errors, [])
            self.assertFalse(filename.exists())
            source.cleanup.assert_called_once()
        finally:
            loop.set_exception_handler(previous_handler)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'settings.json'
        self.original = '{"1": {"channel_id": 10}}'
        self.path.write_text(self.original, encoding='utf-8')
        self.config = object.__new__(Config)
        self.config.SETTINGS_FILE = str(self.path)
        self.config.guild_settings = {1: {'channel_id': 10}}

    def assert_preserved(self):
        self.assertEqual(self.path.read_text(), self.original)
        self.assertEqual(self.config.guild_settings, {1: {'channel_id': 10}})
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])

    def test_partial_write_failure_preserves_file_and_memory(self):
        def fail(data, stream, **kwargs):
            stream.write('{')
            raise OSError('disk write failed')

        with patch('src.config.json.dump', fail):
            with self.assertRaises(SettingsSaveError):
                self.config.set_voice(1, 'new voice')
        self.assert_preserved()

    def test_replace_failure_preserves_file_and_memory(self):
        with patch('src.config.os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(SettingsSaveError):
                self.config.remove_guild_settings(1)
        self.assert_preserved()

    def test_sync_failure_preserves_file_and_memory(self):
        with patch('src.config.os.fsync', side_effect=OSError('fsync failed')):
            with self.assertRaises(SettingsSaveError):
                self.config.set_guild_settings(2, 20)
        self.assert_preserved()

    def test_success_updates_file_and_memory(self):
        self.config.set_voice(1, 'new voice')
        self.assertEqual(json.loads(self.path.read_text())['1']['voice'], 'new voice')
        self.assertEqual(self.config.get_voice(1), 'new voice')
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])


class CommandTests(unittest.IsolatedAsyncioTestCase):
    def register(self, config):
        client = discord.Client(intents=discord.Intents.none())
        tree = discord.app_commands.CommandTree(client)
        with patch.object(commands, 'Config', return_value=config):
            commands.register_commands(NS(tree=tree))
        return tree

    def interaction(self):
        return NS(guild_id=1, guild=NS(voice_client=FakeVoiceClient(), name='guild'),
                  response=NS(defer=AsyncMock(), send_message=AsyncMock(), is_done=lambda: False),
                  followup=NS(send=AsyncMock()))

    async def test_clear_command_awaits_cleanup_and_uses_deferred_response(self):
        tree = self.register(NS())
        interaction = self.interaction()
        with patch.object(commands, 'clear_playback', AsyncMock(return_value=2)) as clear:
            await tree.get_command('clear').callback(interaction)
        clear.assert_awaited_once_with(1, interaction.guild.voice_client)
        interaction.response.defer.assert_awaited_once()
        interaction.followup.send.assert_awaited_once()

    async def test_disable_cancels_playback_after_successful_save(self):
        config = NS(get_guild_settings=lambda guild_id: {'channel_id': 10},
                    remove_guild_settings=Mock())
        tree = self.register(config)
        interaction = self.interaction()
        with patch.object(commands, 'clear_playback', AsyncMock()) as clear:
            await tree.get_command('setup').callback(interaction)
        config.remove_guild_settings.assert_called_once_with(1)
        clear.assert_awaited_once_with(1, interaction.guild.voice_client)
        interaction.followup.send.assert_awaited_once()

    async def test_settings_command_does_not_report_success_after_save_failure(self):
        config = NS(get_guild_settings=lambda guild_id: {'channel_id': 10},
                    set_voice=Mock(side_effect=SettingsSaveError()))
        tree = self.register(config)
        interaction = self.interaction()
        await tree.get_command('voice').callback(
            interaction, discord.app_commands.Choice(name='voice', value='voice')
        )
        args = interaction.response.send_message.call_args
        self.assertIn('저장하지 못했습니다', args.args[0])
        interaction.followup.send.assert_not_awaited()

    async def test_leave_cancels_work_before_disconnecting(self):
        tree = self.register(NS())
        interaction = self.interaction()
        with patch.object(commands, 'disconnect_playback', AsyncMock()) as disconnect:
            await tree.get_command('leave').callback(interaction)
        disconnect.assert_awaited_once_with(1, interaction.guild.voice_client)
        interaction.followup.send.assert_awaited_once()

    async def test_settings_failure_sends_error_instead_of_success(self):
        interaction = NS(response=NS(is_done=lambda: False, send_message=AsyncMock()),
                         followup=NS(send=AsyncMock()))
        saved = await commands.save_config(interaction, Mock(side_effect=SettingsSaveError()))
        self.assertFalse(saved)
        interaction.response.send_message.assert_awaited_once()
        interaction.followup.send.assert_not_awaited()

    async def test_deferred_settings_failure_uses_followup(self):
        interaction = NS(response=NS(is_done=lambda: True, send_message=AsyncMock()),
                         followup=NS(send=AsyncMock()))
        saved = await commands.save_config(interaction, Mock(side_effect=SettingsSaveError()))
        self.assertFalse(saved)
        interaction.followup.send.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
