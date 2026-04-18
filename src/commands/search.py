import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import require_user, embed, err, info


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search", description="Search for a Domegle user by username")
    @app_commands.describe(username="Username to search for")
    async def search(self, interaction: discord.Interaction, username: str):
        if not await require_user(interaction):
            return

        user = await self.bot.db.get_user_by_username(username)
        if not user:
            await interaction.response.send_message(
                embed=err("Not Found", f"No user named **{username}** exists on Domegle."),
                ephemeral=True
            )
            return

        me = await self.bot.db.get_user(interaction.user.id)
        already_friends = await self.bot.db.are_friends(interaction.user.id, user["discord_id"])
        blocked = await self.bot.db.is_blocked(interaction.user.id, user["discord_id"])

        async with self.bot.db.pool.acquire() as conn:
            friend_count = await conn.fetchval(
                "SELECT COUNT(*) FROM friends WHERE user_id=$1 AND status='accepted'",
                user["discord_id"]
            )

        badges = []
        if user["premium"]: badges.append("💎 Premium")
        if user["chat_count"] >= 100: badges.append("🏆 Veteran")
        elif user["chat_count"] >= 50: badges.append("⭐ Regular")
        elif user["chat_count"] >= 10: badges.append("🌱 Active")

        name = ("💎 " if user["premium"] else "") + user["username"]
        e = discord.Embed(title=f"🔍 {name}", color=0x3498DB)
        e.add_field(name="💬 Chats", value=str(user["chat_count"]), inline=True)
        e.add_field(name="⭐ Reputation", value=str(user["reputation"]), inline=True)
        e.add_field(name="👥 Friends", value=str(friend_count), inline=True)
        e.add_field(name="🎯 Interests", value=", ".join(user["interests"]) if user["interests"] else "None", inline=False)

        status_parts = []
        if already_friends: status_parts.append("👥 You are friends")
        if blocked: status_parts.append("🚫 You have blocked this user")
        if status_parts:
            e.add_field(name="Status", value="\n".join(status_parts), inline=False)

        if not already_friends and not blocked and user["discord_id"] != interaction.user.id:
            e.set_footer(text=f"Use /friend_add {user['username']} to add them!")
        else:
            e.set_footer(text="🌍 Domegle")

        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Search(bot))
