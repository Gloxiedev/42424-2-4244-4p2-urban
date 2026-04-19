import sys
import os
sys.path.insert(0, '/usr/lib/python3/dist-packages')
import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import db_check, require_user, err
from src.core.profile_card import generate_profile_card
from src.core.achievements import get_user_achievements, ACHIEVEMENT_MAP
import io


def human_time(dt) -> str:
    from discord.utils import utcnow
    from datetime import timezone
    if not dt:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = int((utcnow() - dt).total_seconds())
    if diff < 60: return "just now"
    if diff < 3600: return f"{diff // 60}m ago"
    if diff < 86400: return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


class ProfileCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="card", description="Generate a visual profile card image")
    @app_commands.describe(username="Leave empty for your own card")
    async def card(self, interaction: discord.Interaction, username: str = None):
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            return  # Interaction expired

        if not await db_check(interaction):
            return

        if username:
            user = await self.bot.db.get_user_by_username(username)
            if not user:
                await interaction.followup.send(embed=err("Not Found", f"No user **{username}** exists."), ephemeral=True)
                return
        else:
            if not await require_user(interaction):
                return
            user = await self.bot.db.get_user(interaction.user.id)

        async with self.bot.db.pool.acquire() as conn:
            friend_count = await conn.fetchval(
                "SELECT COUNT(*) FROM friends WHERE user_id = $1 AND status = 'accepted'",
                user["discord_id"]
            )
            rank = await conn.fetchval(
                "SELECT COUNT(*) + 1 FROM users WHERE chat_count > $1 AND banned = FALSE",
                user["chat_count"]
            )

        earned_ids = await get_user_achievements(self.bot.db, user["discord_id"])
        badges = [ACHIEVEMENT_MAP[aid][1] for aid in earned_ids if aid in ACHIEVEMENT_MAP]

        if user["discord_id"] == interaction.user.id:
            discord_user = interaction.user
        else:
            discord_user = self.bot.get_user(user["discord_id"])
            if discord_user is None:
                try:
                    discord_user = await self.bot.fetch_user(user["discord_id"])
                except Exception:
                    discord_user = None

        avatar_url = str(discord_user.display_avatar.url) if discord_user else None

        title = user.get("title") or ""
        coins = user.get("coins") or 0
        streak = user.get("daily_streak") or 0

        buf = await generate_profile_card(
            username=user["username"],
            coins=coins,
            reputation=user["reputation"],
            chat_count=user["chat_count"],
            friends=friend_count,
            rank=rank,
            badges=badges,
            title=title,
            premium=user["premium"],
            avatar_url=avatar_url,
            daily_streak=streak,
        )

        file = discord.File(buf, filename="profile.png")
        e = discord.Embed(title=f"🌍 {user['username']}'s Profile", color=0x5865F2)
        e.set_image(url="attachment://profile.png")
        e.set_footer(text="🌍 Domegle • /card to generate yours")
        await interaction.followup.send(embed=e, file=file)


async def setup(bot):
    await bot.add_cog(ProfileCard(bot))
