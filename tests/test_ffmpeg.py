"""실제 FFmpeg의 Opus 출력을 확인합니다. 네트워크·Discord 연결은 없습니다."""
import asyncio
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import discord

from src.handlers import message_handler as handler


class LocalPlayer:
    def __init__(self, source, client, after):
        self.source = source
        self.client = client
        self.after = after
        client.source = source

    def start(self):
        def read():
            error = None
            try:
                while packet := self.source.read():
                    self.client.packets.append(packet)
            except Exception as exception:
                error = exception
            finally:
                self.source.cleanup()
                self.after(error)
        threading.Thread(target=read, daemon=True).start()


class LocalClient:
    play = discord.VoiceClient.play

    def __init__(self):
        self.source = None
        self.packets = []

    def is_connected(self):
        return True

    def is_playing(self):
        return False

    def stop(self):
        self.source = None


class FFmpegTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_opus_packets_without_python_opus_encoder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.mp3'
            result = subprocess.run(
                [handler.FFMPEG_EXECUTABLE, '-hide_banner', '-loglevel', 'error',
                 '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.3',
                 '-codec:a', 'libmp3lame', str(path)],
                capture_output=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            client = LocalClient()
            with patch('discord.voice_client.opus.Encoder', side_effect=discord.opus.OpusNotLoaded()) as encoder, \
                 patch('discord.voice_client.AudioPlayer', LocalPlayer):
                await asyncio.wait_for(handler.play_from_file(client, str(path)), timeout=10)
            encoder.assert_not_called()
            self.assertGreater(len(client.packets), 0)
            self.assertFalse(path.exists())
