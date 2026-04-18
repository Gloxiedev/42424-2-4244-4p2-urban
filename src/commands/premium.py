import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import db_check


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="premium", description="Learn about Domegle Premium")
    async def premium(self, interaction: discord.Interaction):
        if not await db_check(interaction):
            return
        user = await self.bot.db.get_user(interaction.user.id)
        already = user and user["premium"]

        e = discord.Embed(title="💎 Domegle Premium", color=0xF1C40F)

        if already:
            e.description = "✅ **You already have Premium!** Enjoy your perks below."
            e.color = 0x2ECC71
        else:
            e.description = "Unlock the best Domegle experience with Premium."

        e.add_field(name="💎 Premium Perks", value=(
            "• **Priority matchmaking** — skip the queue, match faster\n"
            "• **💎 Badge** shown next to your username in all chats\n"
            "• **Unlimited `/next`** — skip strangers freely\n"
            "• **Interest priority** — matched by interests first\n"
            "• **Premium-to-premium pool** — higher quality matches\n"
            "• **Early access** to new features"
        ), inline=False)

        if not already:
            e.add_field(name="📩 How to Get Premium", value=(
                "Premium is granted by Domegle admins.\n"
                "Contact a developer to purchase."
            ), inline=False)

        e.add_field(name="🆓 Free vs 💎 Premium", value=(
            "```\n"
            "Feature          Free    Premium\n"
            "─────────────────────────────────\n"
            "Text Chat         ✅       ✅\n"
            "Voice Chat        ✅       ✅\n"
            "Friends           ✅       ✅\n"
            "Queue Priority    ❌       ✅\n"
            "💎 Badge          ❌       ✅\n"
            "Interest Match    Basic    Priority\n"
            "```"
        ), inline=False)

        e.set_footer(text="🌍 Domegle — Global Anonymous Chat")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Premium(bot))
