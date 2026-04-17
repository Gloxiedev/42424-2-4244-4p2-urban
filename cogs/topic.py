import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, err
from core.matchmaking import MatchmakingEngine
import random

TOPICS = {
    "gaming": [
        "What game are you currently playing?",
        "PC, console, or mobile?",
        "What's your all-time favourite game?",
        "What game do you wish you could play for the first time again?",
        "Favourite game genre?",
    ],
    "music": [
        "What are you listening to lately?",
        "Concerts or studio albums?",
        "What song perfectly describes your life right now?",
        "Most overplayed song you secretly still like?",
        "Favourite decade for music?",
    ],
    "movies": [
        "Last movie you watched?",
        "Cinema or streaming at home?",
        "Most rewatched movie ever?",
        "A movie everyone loves but you don't?",
        "Favourite movie genre?",
    ],
    "life": [
        "What's something you're working towards right now?",
        "What does your perfect day look like?",
        "What's the best decision you've ever made?",
        "If you could change one thing about your life, what would it be?",
        "What's something small that makes you happy?",
    ],
    "random": [
        "If animals could talk, which would be the rudest?",
        "What's a useless talent you have?",
        "If you could only eat one food for a year, what?",
        "What's the most unusual thing near you right now?",
        "If you could instantly know any language, which?",
    ],
    "debate": [
        "Is a hot dog a sandwich? Defend your answer.",
        "Pineapple on pizza: yes or no and why?",
        "Which is better: summer or winter?",
        "Is cereal a soup? Explain.",
        "Would you rather be able to fly or be invisible?",
    ],
}


class Topic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="topic", description="Start a conversation on a specific topic with your partner")
    @app_commands.describe(category="Choose a topic category")
    @app_commands.choices(category=[
        app_commands.Choice(name="🎮 Gaming", value="gaming"),
        app_commands.Choice(name="🎵 Music", value="music"),
        app_commands.Choice(name="🎬 Movies", value="movies"),
        app_commands.Choice(name="🌱 Life", value="life"),
        app_commands.Choice(name="🎲 Random", value="random"),
        app_commands.Choice(name="⚡ Debate", value="debate"),
    ])
    async def topic(self, interaction: discord.Interaction, category: str):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm: MatchmakingEngine = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to start a topic."),
                ephemeral=True
            )
            return

        question = random.choice(TOPICS[category])
        user = await self.bot.db.get_user(interaction.user.id)
        my_name = ("💎 " if user["premium"] else "") + user["username"]

        category_labels = {
            "gaming": "🎮 Gaming",
            "music": "🎵 Music",
            "movies": "🎬 Movies",
            "life": "🌱 Life",
            "random": "🎲 Random",
            "debate": "⚡ Debate",
        }

        partner_ch_id = session.channel_b if session.user_a == interaction.user.id else session.channel_a
        partner_ch = self.bot.get_channel(partner_ch_id)
        if partner_ch is None:
            try:
                partner_ch = await self.bot.fetch_channel(partner_ch_id)
            except Exception:
                partner_ch = None

        e = discord.Embed(
            title=f"{category_labels[category]} Topic",
            description=f"**{my_name}** wants to talk about:\n\n> {question}",
            color=0x9B59B6
        )
        e.set_footer(text="Use /topic to start a conversation!")

        await interaction.response.send_message(embed=e)
        if partner_ch:
            try:
                await partner_ch.send(embed=e)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Topic(bot))
