import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import utcnow
from core.utils import require_user, embed, info
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


class Recent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="recent", description="View people you recently chatted with")
    async def recent(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        rows = await self.bot.db.get_recent_met(interaction.user.id)
        if not rows:
            await interaction.response.send_message(
                embed=info("🕒 Recently Met", "You haven't chatted with anyone yet.\nUse `/omegleconnect` to get started!"),
                ephemeral=True
            )
            return
        lines = []
        for r in rows:
            badge = "💎 " if r["premium"] else ""
            lines.append(f"• {badge}**{r['username']}** — {human_time(r['met_at'])}")
        desc = "\n".join(lines)
        desc += "\n\nUse `/friend_add <username>` to add someone as a friend!"
        await interaction.response.send_message(embed=embed("🕒 Recently Met", desc), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Recent(bot))
