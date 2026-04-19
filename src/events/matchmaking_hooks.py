import discord
from discord.ext import commands
import time
from src.core.economy import award_coins, CHAT_REWARD, LONG_CHAT_BONUS

_session_start: dict = {}


class MatchmakingHooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_session_start(self, user_a_id: int, user_b_id: int):
        now = time.time()
        _session_start[user_a_id] = now
        _session_start[user_b_id] = now

    async def on_session_end(self, user_a_id: int, user_b_id: int):
        now = time.time()
        for uid in [user_a_id, user_b_id]:
            start = _session_start.pop(uid, None)
            if start is None:
                continue
            duration = now - start
            await award_coins(self.bot.db, uid, CHAT_REWARD, "chat completed")
            if duration >= 300:
                await award_coins(self.bot.db, uid, LONG_CHAT_BONUS, "long chat bonus")
            try:
                await self.bot.db.update_user(uid, chat_count=None)
                async with self.bot.db.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET chat_count = chat_count + 1 WHERE discord_id = $1", uid
                    )
            except Exception:
                pass
            from src.core.achievements import check_and_award
            new_ach = await check_and_award(self.bot.db, uid)
            if new_ach:
                discord_user = self.bot.get_user(uid)
                if discord_user:
                    try:
                        names = " • ".join(a[1] for a in new_ach)
                        e = discord.Embed(
                            title="🏆 Achievement Unlocked!",
                            description=names,
                            color=0xF1C40F
                        )
                        await discord_user.send(embed=e)
                    except Exception:
                        pass


async def setup(bot):
    await bot.add_cog(MatchmakingHooks(bot))
