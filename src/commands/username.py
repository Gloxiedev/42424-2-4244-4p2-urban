import discord
from discord import app_commands
from discord.ext import commands
import re
from src.core.utils import ok, err, db_check

BANNED_WORDS = ["admin", "moderator", "domegle", "discord", "nigger", "faggot"]
REGEX = re.compile(r"^[a-zA-Z0-9]{3,16}$")


class Username(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="username", description="Create or change your Domegle username")
    @app_commands.describe(name="3–16 letters/numbers only")
    async def username(self, interaction: discord.Interaction, name: str):
        if not await db_check(interaction):
            return
        if not REGEX.match(name):
            await interaction.response.send_message(embed=err("Invalid", "3–16 characters, letters and numbers only."), ephemeral=True)
            return
        if any(w in name.lower() for w in BANNED_WORDS):
            await interaction.response.send_message(embed=err("Blocked", "That username contains a blocked word."), ephemeral=True)
            return
        existing = await self.bot.db.get_user_by_username(name)
        if existing and existing["discord_id"] != interaction.user.id:
            await interaction.response.send_message(embed=err("Taken", f"**{name}** is already taken."), ephemeral=True)
            return
        user = await self.bot.db.get_user(interaction.user.id)
        if user:
            await self.bot.db.update_user(interaction.user.id, username=name)
            await interaction.response.send_message(embed=ok("✅ Updated", f"Username changed to **{name}**."), ephemeral=True)
        else:
            success = await self.bot.db.create_user(interaction.user.id, name)
            if not success:
                await interaction.response.send_message(embed=err("Taken", "Username already taken."), ephemeral=True)
                return
            e = discord.Embed(
                title="✅ Welcome to Domegle!",
                description=f"Username set to **{name}** 🎉\n\nRun `/omegleconnect` to find a stranger!\nSet interests with `/interests` for better matches.",
                color=0x2ECC71
            )
            e.set_footer(text="🌍 Domegle")
            await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Username(bot))
