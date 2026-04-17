import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, ok, err

AUTO_BAN_THRESHOLD = 5
REASONS = ["Harassment", "Spam / Flooding", "NSFW Content", "Hate Speech", "Scam / Phishing", "Other"]


class ReasonSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select a reason...",
            options=[discord.SelectOption(label=r, value=r) for r in REASONS]
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.reason = self.values[0]
        self.view.stop()
        await interaction.response.defer()


class ReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.reason = None
        self.add_item(ReasonSelect())


class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="report", description="Report the person you're chatting with")
    async def report(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(embed=err("Not in Chat", "You need to be in a chat to report someone."), ephemeral=True)
            return

        view = ReportView()
        await interaction.response.send_message(embed=embed("🚨 Report", "Select a reason for your report:"), view=view, ephemeral=True)
        await view.wait()

        if not view.reason:
            await interaction.edit_original_response(embed=err("Cancelled", "Report cancelled."), view=None)
            return

        partner_id = mm.get_partner_id(interaction.user.id)
        if not partner_id:
            await interaction.edit_original_response(embed=err("Error", "Could not identify the user to report."), view=None)
            return

        await self.bot.db.file_report(interaction.user.id, partner_id, view.reason, session.session_id)
        count = await self.bot.db.get_report_count(partner_id)

        if count >= AUTO_BAN_THRESHOLD:
            await self.bot.db.ban_user(partner_id, f"Auto-banned: {count} reports")
            ended = await mm.end_session(partner_id)
            if ended:
                ch_id = ended.channel_b if ended.user_a == partner_id else ended.channel_a
                ch = self.bot.get_channel(ch_id)
                if ch is None:
                    try:
                        ch = await self.bot.fetch_channel(ch_id)
                    except Exception:
                        ch = None
                if ch:
                    try:
                        await ch.send(embed=err("🔨 Removed", "You have been removed from Domegle."))
                    except Exception:
                        pass
            if ended and ended.voice_channel_id:
                await mm.cleanup_voice_session(ended)

        await interaction.edit_original_response(
            embed=ok("✅ Reported", f"Report submitted.\nReason: **{view.reason}**\n\nThank you for keeping Domegle safe."),
            view=None
        )


async def setup(bot):
    await bot.add_cog(Report(bot))
