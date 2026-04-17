import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, ok, err, info, embed
from core.economy import get_balance, award_coins, spend_coins, DAILY_REWARD
import asyncio
from datetime import date, timezone


SHOP_ITEMS = {
    "priority_match": {"name": "⚡ Priority Match",   "cost": 200, "desc": "Jump to front of queue for your next 3 matches"},
    "extra_rep":      {"name": "⭐ Reputation Boost", "cost": 150, "desc": "Give +2 rep instead of +1 for your next chat"},
    "title_chill":    {"name": "😎 'Chill Guy' Title", "cost": 300, "desc": "Show 'Chill Guy' below your username"},
    "title_debater":  {"name": "⚡ 'Debater' Title",  "cost": 300, "desc": "Show 'Debater' below your username"},
    "title_shadow":   {"name": "🌑 'Shadow' Title",   "cost": 300, "desc": "Show 'Shadow' below your username"},
    "title_cosmic":   {"name": "🌌 'Cosmic' Title",   "cost": 300, "desc": "Show 'Cosmic' below your username"},
    "coin_streak":    {"name": "🔥 Streak Shield",    "cost": 100, "desc": "Protect your daily streak once"},
}

PRIORITY_USERS: dict = {}
BOOSTED_REP: dict = {}


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your coin balance")
    async def balance(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        coins = await get_balance(self.bot.db, interaction.user.id)
        user = await self.bot.db.get_user(interaction.user.id)
        e = discord.Embed(title="💰 Your Balance", color=0xF1C40F)
        e.add_field(name="Coins", value=f"**{coins:,}** 💰", inline=True)
        e.add_field(name="Reputation", value=f"**{user['reputation']}** ⭐", inline=True)
        e.add_field(name="How to earn", value=(
            "• `+5` per chat completed\n"
            "• `+15` bonus for chats over 5 min\n"
            "• `+100` daily reward\n"
            "• `+10` when someone gives you rep"
        ), inline=False)
        e.set_footer(text="🌍 Domegle Economy")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily coin reward")
    async def daily(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return

        async with self.bot.db.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", interaction.user.id)
            last_daily = user.get("last_daily")
            streak = user.get("daily_streak") or 0
            today = date.today()

            if last_daily is not None:
                if hasattr(last_daily, 'date'):
                    last_date = last_daily.date() if last_daily.tzinfo else last_daily
                else:
                    last_date = last_daily
                if hasattr(last_date, 'date'):
                    last_date = last_date.date()
                if last_date == today:
                    import datetime
                    tomorrow = datetime.datetime.combine(today, datetime.time.min, tzinfo=timezone.utc) + datetime.timedelta(days=1)
                    now_utc = discord.utils.utcnow()
                    remaining = int((tomorrow - now_utc).total_seconds())
                    h, rem = divmod(remaining, 3600)
                    m = rem // 60
                    await interaction.response.send_message(
                        embed=info("⏰ Already Claimed", f"Come back in **{h}h {m}m** for your next daily reward!\nCurrent streak: **{streak} days** 🔥"),
                        ephemeral=True
                    )
                    return

                import datetime
                yesterday = today - datetime.timedelta(days=1)
                if last_date == yesterday:
                    streak += 1
                else:
                    streak = 1
            else:
                streak = 1

            reward = DAILY_REWARD + (streak - 1) * 10
            if streak > 1:
                reward = min(reward, 500)

            await conn.execute(
                "UPDATE users SET last_daily = NOW(), daily_streak = $1, coins = coins + $2 WHERE discord_id = $3",
                streak, reward, interaction.user.id
            )

        from core.achievements import check_and_award
        new_ach = await check_and_award(self.bot.db, interaction.user.id)

        e = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **{reward:,}** 💰 coins!\n\n🔥 Streak: **{streak} days**",
            color=0xF1C40F
        )
        if streak > 1:
            e.add_field(name="Streak Bonus", value=f"+{(streak-1)*10} coins for {streak}-day streak", inline=False)
        e.set_footer(text="Come back tomorrow to keep your streak!")

        if new_ach:
            names = " • ".join(f"{a[1]}" for a in new_ach)
            e.add_field(name="🏆 Achievement Unlocked!", value=names, inline=False)

        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="shop", description="Browse the Domegle coin shop")
    async def shop(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        coins = await get_balance(self.bot.db, interaction.user.id)
        e = discord.Embed(title="🛍️ Domegle Shop", description=f"Your balance: **{coins:,}** 💰", color=0x5865F2)
        for item_id, item in SHOP_ITEMS.items():
            e.add_field(
                name=f"{item['name']} — {item['cost']:,} 💰",
                value=f"`/buy {item_id}` — {item['desc']}",
                inline=False
            )
        e.set_footer(text="Use /buy <item_id> to purchase")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item="Item ID from /shop")
    async def buy(self, interaction: discord.Interaction, item: str):
        if not await require_user(interaction):
            return
        if item not in SHOP_ITEMS:
            await interaction.response.send_message(embed=err("Not Found", f"No item `{item}`. Use `/shop` to see available items."), ephemeral=True)
            return

        shop_item = SHOP_ITEMS[item]
        success = await spend_coins(self.bot.db, interaction.user.id, shop_item["cost"])
        if not success:
            await interaction.response.send_message(embed=err("Insufficient Coins", f"This costs **{shop_item['cost']:,}** 💰. Use `/daily` to earn more coins!"), ephemeral=True)
            return

        if item == "priority_match":
            PRIORITY_USERS[interaction.user.id] = 3
        elif item == "extra_rep":
            BOOSTED_REP[interaction.user.id] = True
        elif item.startswith("title_"):
            title = item.split("_", 1)[1].capitalize()
            await self.bot.db.update_user(interaction.user.id, title=title)

        await interaction.response.send_message(
            embed=ok(f"✅ Purchased!", f"**{shop_item['name']}** is now active!\n{shop_item['desc']}"),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))
