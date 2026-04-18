import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import require_user, require_chat_context, get_session_channel_id, get_session_guild_id, embed, err, is_dm
from src.core.matchmaking import QueueEntry, ChatType
from src.core.antibot import run_captcha, account_old_enough


class ConnectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.choice = None

    @discord.ui.button(label="💬 Text Chat", style=discord.ButtonStyle.primary)
    async def text(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.choice = ChatType.TEXT
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="🎙 Voice Call", style=discord.ButtonStyle.secondary)
    async def voice(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.choice = ChatType.VOICE
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        self.stop()


class Connect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="omegleconnect", description="Connect with a random stranger")
    async def omegleconnect(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        if mm is None:
            await interaction.response.send_message(embed=err("Error", "Matchmaking unavailable. Try again shortly."), ephemeral=True)
            return

        if await mm.get_session(interaction.user.id):
            await interaction.response.send_message(embed=err("Already in Chat", "Use `/next` or `/stop` first."), ephemeral=True)
            return
        if mm.is_in_queue(interaction.user.id):
            await interaction.response.send_message(embed=err("Already Searching", "You're already in the queue."), ephemeral=True)
            return
        if not account_old_enough(interaction.user):
            await interaction.response.send_message(embed=err("Account Too New", "Your Discord account must be at least 7 days old."), ephemeral=True)
            return

        user = await self.bot.db.get_user(interaction.user.id)
        if not user["captcha_passed"]:
            passed = await run_captcha(interaction)
            if passed:
                await self.bot.db.update_user(interaction.user.id, captcha_passed=True)
            return

        # Voice chat not available in DMs
        if is_dm(interaction):
            chat_type = ChatType.TEXT
            channel_id = await get_session_channel_id(interaction)
            guild_id = 0
        else:
            view = ConnectView()
            await interaction.response.send_message(embed=embed("🌍 Connect", "Choose your chat type:"), view=view, ephemeral=True)
            await view.wait()

            if view.choice is None:
                await interaction.edit_original_response(embed=err("Timed Out", "You didn't choose a chat type in time."), view=None)
                return

            chat_type = view.choice
            channel_id = interaction.channel_id
            guild_id = interaction.guild_id

            if chat_type == ChatType.VOICE:
                server = await self.bot.db.get_server(guild_id)
                if server and server["voice_channel_id"]:
                    member = interaction.user
                    if not member or not member.voice:
                        await interaction.edit_original_response(
                            embed=err("Join Voice First", f"Join <#{server['voice_channel_id']}> then run `/omegleconnect` again."),
                            view=None
                        )
                        return

        entry = QueueEntry(
            discord_id=interaction.user.id,
            guild_id=guild_id,
            channel_id=channel_id,
            chat_type=chat_type,
            premium=user["premium"],
            interests=list(user["interests"] or []),
        )
        result = await mm.enqueue(entry)
        qs = mm.get_queue_sizes()
        t = "voice" if chat_type == ChatType.VOICE else "text"

        responses = {
            "rate_limited": err("Slow Down", "Please wait 10 seconds before connecting again."),
            "already_in_queue": err("Already Searching", "You're already in the queue."),
            "in_session": err("Already in Chat", "Use `/stop` to leave your current chat first."),
            "queued": embed("🔍 Searching...", f"Looking for a {t} chat partner...\n**{qs[t]}** people in queue\n\nUse `/stop` to cancel."),
        }

        if is_dm(interaction):
            await interaction.response.send_message(embed=responses[result])
        else:
            await interaction.edit_original_response(embed=responses[result], view=None)


async def setup(bot):
    await bot.add_cog(Connect(bot))
