import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, err
from core.matchmaking import MatchmakingEngine
import random

ICEBREAKERS = [
    "What's the last show you binged?",
    "If you could live anywhere in the world, where would it be?",
    "What's your most controversial food opinion?",
    "What's a skill you wish you had?",
    "Night owl or early bird?",
    "What's the best thing that happened to you this week?",
    "If you could have dinner with anyone alive or dead, who?",
    "What's your go-to comfort food?",
    "What's a hobby you recently picked up?",
    "Dogs or cats?",
    "What's the most underrated movie you've seen?",
    "If you won the lottery tomorrow, what's the first thing you'd buy?",
    "What's your dream job?",
    "What song is always stuck in your head?",
    "What's the weirdest dream you've ever had?",
    "Coffee, tea, or energy drinks?",
    "What's your favourite season and why?",
    "If you had a time machine, past or future?",
    "What's a random fact you know that most people don't?",
    "What video game have you spent the most hours on?",
    "Beach or mountains?",
    "What's the best advice you've ever been given?",
    "What's something you're proud of but rarely talk about?",
    "Morning shower or night shower?",
    "What's the last thing you googled?",
    "What's a movie/show everyone loves but you don't get?",
    "If you could master any instrument instantly, which?",
    "What's your hot take on pineapple on pizza?",
    "What superpower would you pick?",
    "What's your most used emoji?",
]

DARES = [
    "Tell your partner your most embarrassing moment.",
    "Describe yourself in exactly 3 words.",
    "What's the biggest lie you've ever told?",
    "Confess something you've never told anyone.",
    "What's your biggest fear?",
    "Tell the most awkward story from school.",
    "What's a secret talent you have?",
    "Describe your personality as a weather forecast.",
    "What's the worst purchase you've ever made?",
    "Admit something you're irrationally afraid of.",
]


class Icebreaker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="icebreaker", description="Send a random conversation starter to your chat partner")
    async def icebreaker(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm: MatchmakingEngine = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to use an icebreaker."),
                ephemeral=True
            )
            return

        question = random.choice(ICEBREAKERS)
        partner_id = mm.get_partner_id(interaction.user.id)

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
            title="🎯 Icebreaker!",
            description=f"**{my_name}** sent an icebreaker:\n\n> {question}",
            color=0xE67E22
        )
        e.set_footer(text="Use /icebreaker to send one too!")

        await interaction.response.send_message(embed=e)
        if partner_ch:
            try:
                await partner_ch.send(embed=e)
            except Exception:
                pass

    @app_commands.command(name="dare", description="Send a random dare to your chat partner")
    async def dare(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm: MatchmakingEngine = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to send a dare."),
                ephemeral=True
            )
            return

        dare = random.choice(DARES)
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
            title="🎲 Dare!",
            description=f"**{my_name}** dares you:\n\n> {dare}",
            color=0xE74C3C
        )
        e.set_footer(text="Use /dare to send one back!")

        await interaction.response.send_message(embed=e)
        if partner_ch:
            try:
                await partner_ch.send(embed=e)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Icebreaker(bot))
