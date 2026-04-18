import logging

log = logging.getLogger("domegle.economy")

CHAT_REWARD = 5
LONG_CHAT_BONUS = 15
DAILY_REWARD = 100
REP_BONUS = 10


async def award_coins(db, discord_id: int, amount: int, reason: str = ""):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET coins = coins + $1 WHERE discord_id = $2",
            amount, discord_id
        )
    if reason:
        log.info(f"Awarded {amount} coins to {discord_id}: {reason}")


async def spend_coins(db, discord_id: int, amount: int) -> bool:
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT coins FROM users WHERE discord_id = $1", discord_id)
        if not row or row["coins"] < amount:
            return False
        await conn.execute(
            "UPDATE users SET coins = coins - $1 WHERE discord_id = $2",
            amount, discord_id
        )
        return True


async def get_balance(db, discord_id: int) -> int:
    async with db.pool.acquire() as conn:
        val = await conn.fetchval("SELECT coins FROM users WHERE discord_id = $1", discord_id)
        return val or 0
