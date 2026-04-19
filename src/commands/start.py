import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import ok, db_check


class Start(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start", description="Get started with Domegle")
    async def start(self, interaction: discord.Interaction):
        if not await db_check(interaction):
            return
        user = await self.bot.db.get_user(interaction.user.id)
        if user:
            await interaction.response.send_message(
                embed=ok("🌍 Welcome Back!", f"You're registered as **{user['username']}**.\nUse `/omegleconnect` to chat!"),
                ephemeral=True
            )
            return
        e = discord.Embed(
            title="🌍 Welcome to Domegle!",
            description=(
                "Connect with random strangers across Discord.\n"
                "Your Discord account stays **completely anonymous**.\n\n"
                "**📜 Rules**\n"
                "• Be respectful\n"
                "• No harassment or hate speech\n"
                "• No spam\n"
                "• No NSFW content\n"
                "• Follow Discord's Terms of Service\n\n"
                "**Create your username to begin:**\n```\n/username <your_name>\n```"
            ),
            color=0x5865F2
        )
        e.set_footer(text="🌍 Domegle — Global Anonymous Chat")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Start(bot))
