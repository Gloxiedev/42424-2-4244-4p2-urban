import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, ok, err


class Block(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="block", description="Block the current stranger permanently")
    async def block(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(embed=err("Not in Chat", "You need to be in a chat to block someone."), ephemeral=True)
            return

        partner_id = mm.get_partner_id(interaction.user.id)
        if not partner_id:
            await interaction.response.send_message(embed=err("Error", "Could not find the user to block."), ephemeral=True)
            return

        await self.bot.db.block_user(interaction.user.id, partner_id)
        ended = await mm.end_session(interaction.user.id)

        if ended:
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
            if ended.voice_channel_id:
                await mm.cleanup_voice_session(ended)

        await interaction.response.send_message(
            embed=ok("🚫 Blocked", "User blocked. You will never be matched with them again."),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Block(bot))
