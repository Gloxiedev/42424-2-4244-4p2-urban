import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, ok, err, is_dm


class Stop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stop", description="Leave the current chat or queue")
    async def stop_cmd(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        in_queue = mm.is_in_queue(interaction.user.id)

        if not session and not in_queue:
            await interaction.response.send_message(embed=err("Nothing to Stop", "You're not in a chat or queue."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if in_queue and not session:
            await mm.dequeue(interaction.user.id)
            await interaction.followup.send(embed=ok("🛑 Left Queue", "You've been removed from the queue."), ephemeral=True)
            return

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

        await interaction.followup.send(embed=ok("🛑 Disconnected", "You've left the chat."), ephemeral=True)

        if not is_dm(interaction):
            try:
                await interaction.channel.send(embed=embed("📴 Chat Ended", "A stranger has left the chat."))
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Stop(bot))
