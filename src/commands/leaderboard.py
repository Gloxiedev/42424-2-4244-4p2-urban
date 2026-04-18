import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import embed, db_check

MEDALS = ["🥇", "🥈", "🥉"]


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Top chatters on the Domegle network")
    @app_commands.describe(category="What to rank by")
    @app_commands.choices(category=[
        app_commands.Choice(name="Most Chats", value="chats"),
        app_commands.Choice(name="Best Reputation", value="reputation"),
        app_commands.Choice(name="Most Friends", value="friends"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, category: str = "chats"):
        if not await db_check(interaction):
            return
        await interaction.response.defer()

        async with self.bot.db.pool.acquire() as conn:
            if category == "chats":
                rows = await conn.fetch(
                    "SELECT username, premium, chat_count as value FROM users WHERE banned = FALSE ORDER BY chat_count DESC LIMIT 10"
                )
                title, value_label = "💬 Most Chats", "chats"
            elif category == "reputation":
                rows = await conn.fetch(
                    "SELECT username, premium, reputation as value FROM users WHERE banned = FALSE ORDER BY reputation DESC LIMIT 10"
                )
                title, value_label = "⭐ Best Reputation", "rep"
            else:
                rows = await conn.fetch("""
                    SELECT u.username, u.premium, COUNT(f.friend_id) as value
                    FROM users u
                    LEFT JOIN friends f ON f.user_id = u.discord_id AND f.status = 'accepted'
                    WHERE u.banned = FALSE
                    GROUP BY u.discord_id, u.username, u.premium
                    ORDER BY value DESC
                    LIMIT 10
                """)
                title, value_label = "👥 Most Friends", "friends"

        if not rows:
            await interaction.followup.send(embed=embed("📊 Leaderboard", "No data yet!"))
            return

        me = await self.bot.db.get_user(interaction.user.id)
        lines = []
        for i, row in enumerate(rows):
            medal = MEDALS[i] if i < 3 else f"`{i+1}.`"
            name = ("💎 " if row["premium"] else "") + row["username"]
            is_me = me and row["username"] == me["username"]
            lines.append(f"{medal} **{name}** — {row['value']} {value_label}" + (" ← you" if is_me else ""))

        e = discord.Embed(title=f"🌍 Leaderboard — {title}", description="\n".join(lines), color=0xF1C40F)
        e.set_footer(text="🌍 Domegle Global Network")
        await interaction.followup.send(embed=e)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
