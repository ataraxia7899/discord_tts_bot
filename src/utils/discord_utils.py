"""
공통 Discord 유틸리티

에러 응답, Embed 생성 등 공통 기능을 제공합니다.
"""
import discord
from typing import Optional


def create_success_embed(title: str, description: str, fields: Optional[list] = None) -> discord.Embed:
    """
    성공 응답용 Embed를 생성합니다.
    
    Args:
        title: Embed 제목
        description: Embed 설명
        fields: 추가 필드 리스트 [{"name": str, "value": str, "inline": bool}, ...]
        
    Returns:
        discord.Embed 객체
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green()
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", True)
            )
    
    return embed


def create_error_embed(title: str, description: str) -> discord.Embed:
    """
    에러 응답용 Embed를 생성합니다.
    
    Args:
        title: Embed 제목
        description: Embed 설명
        
    Returns:
        discord.Embed 객체
    """
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )


def create_info_embed(title: str, description: str) -> discord.Embed:
    """
    정보 응답용 Embed를 생성합니다.
    
    Args:
        title: Embed 제목
        description: Embed 설명
        
    Returns:
        discord.Embed 객체
    """
    return discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue()
    )


# 공통 에러 메시지
ERROR_SETUP_REQUIRED = "먼저 `/setup` 명령어로 TTS를 설정해주세요."
ERROR_GCTTS_REQUIRED = (
    "이 명령어는 Google Cloud TTS 엔진을 사용하는 서버에서만 사용할 수 있습니다.\n"
    "`/setup` 명령어에서 'Google Cloud TTS'를 선택해주세요."
)
