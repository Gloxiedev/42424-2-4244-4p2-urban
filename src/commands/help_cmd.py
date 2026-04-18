import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all Domegle commands")
    async def help_cmd(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="🌍 Domegle Help",
            description="Connect anonymously with strangers across Discord.\nWorks in servers and DMs!",
            color=0x5865F2
        )
        e.add_field(name="🚀 Getting Started", value=(
            "`/start` — Register\n"
            "`/username <n>` — Create your identity\n"
            "`/rules` — Read the rules\n"
            "`/ping` — Check bot status"
        ), inline=False)
        e.add_field(name="💬 Chat", value=(
            "`/omegleconnect` — Find a stranger\n"
            "`/next` — Skip to next stranger\n"
            "`/stop` — Leave the chat\n"
            "`/reveal` — Reveal your Discord profile\n"
            "`/filters` — Set region/language filters"
        ), inline=False)
        e.add_field(name="🎯 In-Chat Tools", value=(
            "`/icebreaker` — Random conversation starter\n"
            "`/topic <category>` — Start a topic (gaming, music, debate...)\n"
            "`/dare` — Send your partner a dare\n"
            "`/mood <feeling>` — Share your current mood\n"
            "`/rep` — Give +1 rep after a good chat"
        ), inline=False)
        e.add_field(name="🎉 Party Mode", value=(
            "`/party_create` — Create a group chat (up to 5)\n"
            "`/party_join <code>` — Join a party\n"
            "`/party_start` — Start the party chat\n"
            "`/party_leave` — Leave the party"
        ), inline=False)
        e.add_field(name="👥 Friends", value=(
            "`/friend_add <user>` — Send a friend request\n"
            "`/friend_accept <user>` — Accept a request\n"
            "`/friend_remove <user>` — Remove a friend\n"
            "`/friend_list` — View friends & requests\n"
            "`/friend_chat <user>` — Private chat with friend"
        ), inline=False)
        e.add_field(name="🪙 Economy", value=(
            "`/balance` — Check your coin balance\n"
            "`/daily` — Claim daily reward (streak bonus!)\n"
            "`/shop` — Browse the coin shop\n"
            "`/buy <item>` — Purchase a shop item"
        ), inline=False)
        e.add_field(name="🏆 Profile & Stats", value=(
            "`/profile [username]` — View profile card\n"
            "`/card [username]` — Generate profile image\n"
            "`/achievements` — View your achievements\n"
            "`/mystatus` — Your account standing\n"
            "`/leaderboard` — Top chatters\n"
            "`/stats` — Network statistics"
        ), inline=False)
        e.add_field(name="🔍 Discovery", value=(
            "`/search <username>` — Look up a user\n"
            "`/recent` — Recently chatted users\n"
            "`/interests <tags>` — Set match interests"
        ), inline=False)
        e.add_field(name="🛡 Safety", value=(
            "`/report` — Report current stranger\n"
            "`/block` — Block current stranger"
        ), inline=False)
        e.add_field(name="⚙️ Server Admin", value=(
            "`/setdomeglechat #channel`\n"
            "`/setdomeglevoice #channel`\n"
            "`/domeglesetup`"
        ), inline=False)
        e.set_footer(text="🌍 Domegle — Your identity stays anonymous")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
