import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import db_check


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View Domegle network statistics")
    async def stats(self, interaction: discord.Interaction):
        if not await db_check(interaction):
            return
        s = await self.bot.db.get_global_stats()
        mm = self.bot.matchmaking
        qs = mm.get_queue_sizes() if mm else {"text": 0, "voice": 0, "active_sessions": 0}
        e = discord.Embed(title="🌍 Domegle Network", color=0x5865F2)
        e.add_field(name="💬 Active Chats", value=str(qs["active_sessions"]), inline=True)
        e.add_field(name="🔍 Searching", value=str(qs["text"] + qs["voice"]), inline=True)
        e.add_field(name="🌐 Servers", value=str(s["total_servers"]), inline=True)
        e.add_field(name="📊 Matches Today", value=str(s["matches_today"]), inline=True)
        e.add_field(name="🏆 Total Matches", value=str(s["total_matches"]), inline=True)
        e.add_field(name="👤 Total Users", value=str(s["total_users"]), inline=True)
        e.set_footer(text="🌍 Domegle — Global Anonymous Chat")
        await interaction.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Stats(bot))
