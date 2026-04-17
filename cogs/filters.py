import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, ok, err

_user_filters: dict = {}

SUPPORTED_REGIONS = ["na", "eu", "asia", "any"]
SUPPORTED_LANGUAGES = ["english", "spanish", "french", "german", "portuguese", "any"]


class Filters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="filters", description="Set optional matchmaking filters")
    @app_commands.describe(
        region="Preferred region (na/eu/asia/any)",
        language="Preferred chat language",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="🌎 North America", value="na"),
            app_commands.Choice(name="🌍 Europe", value="eu"),
            app_commands.Choice(name="🌏 Asia", value="asia"),
            app_commands.Choice(name="🌐 Any Region", value="any"),
        ],
        language=[
            app_commands.Choice(name="🇬🇧 English", value="english"),
            app_commands.Choice(name="🇪🇸 Spanish", value="spanish"),
            app_commands.Choice(name="🇫🇷 French", value="french"),
            app_commands.Choice(name="🇩🇪 German", value="german"),
            app_commands.Choice(name="🇧🇷 Portuguese", value="portuguese"),
            app_commands.Choice(name="🌐 Any Language", value="any"),
        ],
    )
    async def filters(
        self,
        interaction: discord.Interaction,
        region: str = "any",
        language: str = "any",
    ):
        if not await require_user(interaction):
            return

        _user_filters[interaction.user.id] = {
            "region": region,
            "language": language,
        }

        region_labels = {"na": "🌎 North America", "eu": "🌍 Europe", "asia": "🌏 Asia", "any": "🌐 Any"}
        lang_labels = {"english": "🇬🇧 English", "spanish": "🇪🇸 Spanish", "french": "🇫🇷 French", "german": "🇩🇪 German", "portuguese": "🇧🇷 Portuguese", "any": "🌐 Any"}

        e = discord.Embed(title="⚙️ Filters Updated", color=0x2ECC71)
        e.add_field(name="Region", value=region_labels.get(region, region), inline=True)
        e.add_field(name="Language", value=lang_labels.get(language, language), inline=True)
        e.add_field(
            name="Note",
            value="Filters help narrow your matches but may increase wait time. Set everything to **Any** for fastest matching.",
            inline=False
        )
        e.set_footer(text="Filters apply to your next /omegleconnect")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="filters_clear", description="Clear all matchmaking filters")
    async def filters_clear(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        _user_filters.pop(interaction.user.id, None)
        await interaction.response.send_message(embed=ok("✅ Cleared", "All filters removed. You'll match with everyone."), ephemeral=True)


def get_user_filters(discord_id: int) -> dict:
    return _user_filters.get(discord_id, {"region": "any", "language": "any"})


async def setup(bot):
    await bot.add_cog(Filters(bot))
