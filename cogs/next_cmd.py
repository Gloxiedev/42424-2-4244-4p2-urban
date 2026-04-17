import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, get_session_channel_id, embed, err, is_dm
from core.matchmaking import QueueEntry, ChatType


class Next(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="next", description="End current chat and find a new stranger")
    async def next_cmd(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        in_queue = mm.is_in_queue(interaction.user.id)

        if not session and not in_queue:
            await interaction.response.send_message(embed=err("Not in Chat", "Use `/omegleconnect` to start."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        user = await self.bot.db.get_user(interaction.user.id)

        if session:
            partner_id = mm.get_partner_id(interaction.user.id)
            ended = await mm.end_session(interaction.user.id)
            if partner_id and ended:
                ch_id = ended.channel_b if ended.user_a == interaction.user.id else ended.channel_a
                ch = self.bot.get_channel(ch_id)
                if ch is None:
                    try:
                        ch = await self.bot.fetch_channel(ch_id)
                    except Exception:
                        ch = None
                if ch:
                    try:
                        await ch.send(embed=embed("👋 Stranger Left", "Use `/omegleconnect` to find someone new."))
                    except Exception:
                        pass
            if ended and ended.voice_channel_id:
                await mm.cleanup_voice_session(ended)

        chat_type = session.chat_type if session else ChatType.TEXT
        channel_id = await get_session_channel_id(interaction)
        guild_id = interaction.guild_id or 0

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

        if result == "rate_limited":
            await interaction.followup.send(embed=err("Slow Down", "Wait a moment before searching again."), ephemeral=True)
        else:
            await interaction.followup.send(
                embed=embed("🔍 Searching...", f"Looking for a new stranger...\n**{qs['text']}** in queue"),
                ephemeral=True
            )

        if not is_dm(interaction):
            try:
                await interaction.channel.send(embed=embed("📴 Chat Ended", "Stranger skipped — searching for someone new."))
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Next(bot))
