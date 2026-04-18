import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import require_user, require_chat_context, embed, err
from src.core.matchmaking import MatchmakingEngine

MOODS = {
    "happy": ("😊", 0x2ECC71, "in a great mood"),
    "sad": ("😢", 0x3498DB, "feeling a bit down"),
    "bored": ("😴", 0x95A5A6, "bored and looking for fun"),
    "excited": ("🤩", 0xF39C12, "super excited"),
    "anxious": ("😰", 0x9B59B6, "feeling a bit anxious"),
    "chill": ("😎", 0x1ABC9C, "totally chilling"),
    "angry": ("😤", 0xE74C3C, "a bit frustrated"),
    "lonely": ("🥺", 0xE8D5B7, "feeling lonely"),
    "hyper": ("⚡", 0xF1C40F, "absolutely hyper"),
    "mysterious": ("🎭", 0x2C3E50, "feeling mysterious"),
}


class Mood(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mood", description="Share your current mood with your chat partner")
    @app_commands.describe(mood="How are you feeling right now?")
    @app_commands.choices(mood=[
        app_commands.Choice(name=f"{v[0]} {k.capitalize()}", value=k)
        for k, v in MOODS.items()
    ])
    async def mood(self, interaction: discord.Interaction, mood: str):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm: MatchmakingEngine = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to share your mood."),
                ephemeral=True
            )
            return

        emoji, color, desc = MOODS[mood]
        user = await self.bot.db.get_user(interaction.user.id)
        my_name = ("💎 " if user["premium"] else "") + user["username"]

        partner_ch_id = session.channel_b if session.user_a == interaction.user.id else session.channel_a
        partner_ch = self.bot.get_channel(partner_ch_id)
        if partner_ch is None:
            try:
                partner_ch = await self.bot.fetch_channel(partner_ch_id)
            except Exception:
                partner_ch = None

        e = discord.Embed(
            title=f"{emoji} Mood Check",
            description=f"**{my_name}** is {desc}.",
            color=color
        )
        e.set_footer(text="Use /mood to share yours!")

        await interaction.response.send_message(embed=e)
        if partner_ch:
            try:
                await partner_ch.send(embed=e)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Mood(bot))
