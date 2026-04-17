import discord
from discord import app_commands
from discord.ext import commands


class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rules", description="View Domegle rules and what will get you banned")
    async def rules(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="📜 Domegle Rules",
            description="By using Domegle, you agree to follow these rules. Violations result in warnings, temporary restrictions, or a **permanent network ban**.",
            color=0xE74C3C
        )

        e.add_field(
            name="✅ You Must",
            value=(
                "• Treat others with basic respect\n"
                "• Follow Discord's Terms of Service\n"
                "• Use Domegle commands only in the designated channel\n"
                "• Report rule-breakers using `/report`"
            ),
            inline=False
        )

        e.add_field(
            name="🚫 Instant Ban Offences",
            value=(
                "• **CSAM or any sexual content involving minors** — zero tolerance, reported to authorities\n"
                "• **Threats of violence** against another user\n"
                "• **Doxxing** — sharing real personal information of any user\n"
                "• **Scams or phishing links** — sending fraudulent links or impersonating services\n"
                "• **Automated bots or selfbots** using Domegle"
            ),
            inline=False
        )

        e.add_field(
            name="⚠️ Will Get You Banned",
            value=(
                "• **Hate speech** — racism, homophobia, transphobia, sexism, or slurs\n"
                "• **Harassment or stalking** — repeatedly targeting or following a user\n"
                "• **NSFW content** — explicit text, images, or links\n"
                "• **Spam or flooding** — repetitive messages, raid behaviour\n"
                "• **Impersonating Domegle staff** or developers\n"
                "• **Ban evasion** — creating new accounts after a ban"
            ),
            inline=False
        )

        e.add_field(
            name="🔨 How Bans Work",
            value=(
                "• **5 reports** from different users triggers an automatic review ban\n"
                "• Bans are **network-wide** — you're removed from every server using Domegle\n"
                "• Ban evasion results in all accounts being permanently banned\n"
                "• To appeal a ban, contact a Domegle developer"
            ),
            inline=False
        )

        e.add_field(
            name="🛡 Your Safety",
            value=(
                "• **Never share personal info** — real name, location, social media, phone number\n"
                "• **Block immediately** if someone makes you uncomfortable — `/block`\n"
                "• **Report don't engage** — use `/report` and move on with `/next`\n"
                "• Domegle staff will **never ask for your password or token**"
            ),
            inline=False
        )

        e.set_footer(text="🌍 Domegle — Rules last updated by the Domegle team")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Rules(bot))
