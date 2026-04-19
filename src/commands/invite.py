import discord
from discord import app_commands
from discord.ext import commands


class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get the bot invite link to add Domegle to your server")
    async def invite(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="🌍 Invite Domegle to Your Server!",
            description="Click the button below to invite Domegle to your Discord server and start connecting with people worldwide!",
            color=0x5865F2
        )

        e.add_field(
            name="🤖 Bot Features",
            value="• Connect with strangers\n• Voice chat matchmaking\n• Friend system\n• Premium features\n• Profile cards",
            inline=False
        )

        e.set_footer(text="🌍 Domegle - Connect the World")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 Invite Bot",
            style=discord.ButtonStyle.link,
            url="https://discord.com/oauth2/authorize?client_id=1494742012514140320&permissions=8866461497818945&integration_type=0&scope=bot"
        ))

        await interaction.response.send_message(embed=e, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Invite(bot))
