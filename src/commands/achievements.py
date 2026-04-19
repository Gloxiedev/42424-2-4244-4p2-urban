import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import require_user, embed
from src.core.achievements import get_user_achievements, ACHIEVEMENT_MAP


class Achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="achievements", description="View your Domegle achievements")
    async def achievements(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        earned_ids = await get_user_achievements(self.bot.db, interaction.user.id)
        earned_set = set(earned_ids)

        earned_lines = []
        locked_lines = []
        for ach_id, (_, name, desc, _) in ACHIEVEMENT_MAP.items():
            if ach_id in earned_set:
                earned_lines.append(f"✅ **{name}** — {desc}")
            else:
                locked_lines.append(f"🔒 {name} — {desc}")

        e = discord.Embed(
            title="🏆 Achievements",
            description=f"**{len(earned_ids)}/{len(ACHIEVEMENT_MAP)}** unlocked",
            color=0xF1C40F
        )
        if earned_lines:
            e.add_field(name="Unlocked", value="\n".join(earned_lines[:10]), inline=False)
        if locked_lines:
            e.add_field(name="Locked", value="\n".join(locked_lines[:10]), inline=False)
        e.set_footer(text="Keep chatting to unlock more achievements!")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Achievements(bot))
