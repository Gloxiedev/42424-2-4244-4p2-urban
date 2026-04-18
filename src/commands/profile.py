import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import utcnow
from src.core.utils import require_user, embed, err, db_check
from datetime import timezone


def human_time(dt) -> str:
    if not dt:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = int((utcnow() - dt).total_seconds())
    if diff < 60: return "just now"
    if diff < 3600: return f"{diff // 60}m ago"
    if diff < 86400: return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View your Domegle profile card")
    @app_commands.describe(username="Leave empty to view your own profile")
    async def profile(self, interaction: discord.Interaction, username: str = None):
        if not await db_check(interaction):
            return
        if username:
            user = await self.bot.db.get_user_by_username(username)
            if not user:
                await interaction.response.send_message(embed=err("Not Found", f"No user **{username}** exists."), ephemeral=True)
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

        badges = []
        if user["premium"]:
            badges.append("💎 Premium")
        if user["chat_count"] >= 100:
            badges.append("🏆 Veteran")
        elif user["chat_count"] >= 50:
            badges.append("⭐ Regular")
        elif user["chat_count"] >= 10:
            badges.append("🌱 Active")
        if friend_count >= 10:
            badges.append("👥 Social")
        if user["reputation"] >= 10:
            badges.append("✨ Reputable")

        name = ("💎 " if user["premium"] else "") + user["username"]
        e = discord.Embed(title=f"🌍 {name}", color=0x5865F2)
        e.add_field(name="💬 Chats", value=str(user["chat_count"]), inline=True)
        e.add_field(name="🏅 Rank", value=f"#{rank}", inline=True)
        e.add_field(name="⭐ Reputation", value=str(user["reputation"]), inline=True)
        e.add_field(name="👥 Friends", value=str(friend_count), inline=True)
        e.add_field(name="🎯 Interests", value=", ".join(user["interests"]) if user["interests"] else "None set", inline=True)
        e.add_field(name="🕒 Last Seen", value=human_time(user["last_seen"]), inline=True)
        if badges:
            e.add_field(name="🏷 Badges", value=" • ".join(badges), inline=False)
        e.set_footer(text="Domegle member since")
        e.timestamp = user["created_at"]
        await interaction.response.send_message(embed=e, ephemeral=not bool(username))


async def setup(bot):
    await bot.add_cog(Profile(bot))
