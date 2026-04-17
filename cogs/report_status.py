import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, embed, info


class ReportStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mystatus", description="View your Domegle account status and standing")
    async def mystatus(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return

        user = await self.bot.db.get_user(interaction.user.id)

        async with self.bot.db.pool.acquire() as conn:
            reports_against = await conn.fetchval(
                "SELECT COUNT(*) FROM reports WHERE reported_id=$1 AND reviewed=FALSE",
                interaction.user.id
            )
            reports_filed = await conn.fetchval(
                "SELECT COUNT(*) FROM reports WHERE reporter_id=$1",
                interaction.user.id
            )
            friend_count = await conn.fetchval(
                "SELECT COUNT(*) FROM friends WHERE user_id=$1 AND status='accepted'",
                interaction.user.id
            )
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE banned=FALSE")
            rank = await conn.fetchval(
                "SELECT COUNT(*)+1 FROM users WHERE chat_count > $1 AND banned=FALSE",
                user["chat_count"]
            )

        if reports_against == 0:
            standing = "✅ Good Standing"
            standing_color = 0x2ECC71
        elif reports_against < 3:
            standing = "⚠️ Caution"
            standing_color = 0xF39C12
        else:
            standing = "🚨 At Risk"
            standing_color = 0xE74C3C

        e = discord.Embed(title="📋 Your Account Status", color=standing_color)
        e.add_field(name="👤 Username", value=("💎 " if user["premium"] else "") + user["username"], inline=True)
        e.add_field(name="🛡 Standing", value=standing, inline=True)
        e.add_field(name="💎 Premium", value="Yes ✅" if user["premium"] else "No ❌", inline=True)
        e.add_field(name="💬 Total Chats", value=str(user["chat_count"]), inline=True)
        e.add_field(name="🏅 Global Rank", value=f"#{rank} of {total_users}", inline=True)
        e.add_field(name="⭐ Reputation", value=str(user["reputation"]), inline=True)
        e.add_field(name="👥 Friends", value=str(friend_count), inline=True)
        e.add_field(name="🚨 Reports Against You", value=str(reports_against), inline=True)
        e.add_field(name="📝 Reports Filed", value=str(reports_filed), inline=True)
        e.add_field(name="🎯 Interests", value=", ".join(user["interests"]) if user["interests"] else "None set", inline=False)
        e.set_footer(text="🌍 Domegle — Account Status")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReportStatus(bot))
