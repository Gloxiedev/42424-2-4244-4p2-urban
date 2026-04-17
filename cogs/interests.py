import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, ok, err


class Interests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="interests", description="Set interests for better matches")
    @app_commands.describe(interests="Space-separated tags e.g. gaming coding music")
    async def interests(self, interaction: discord.Interaction, interests: str):
        if not await require_user(interaction):
            return
        tags = [t.strip().lower() for t in interests.split() if t.strip()]
        if len(tags) > 10:
            await interaction.response.send_message(embed=err("Too Many", "Max 10 interests."), ephemeral=True)
            return
        if any(len(t) > 30 for t in tags):
            await interaction.response.send_message(embed=err("Too Long", "Each interest must be under 30 characters."), ephemeral=True)
            return
        await self.bot.db.set_interests(interaction.user.id, tags)
        formatted = " • ".join(f"`{t}`" for t in tags)
        await interaction.response.send_message(
            embed=ok("✅ Interests Set", f"{formatted}\n\nYou'll be matched with people who share similar interests!"),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Interests(bot))
