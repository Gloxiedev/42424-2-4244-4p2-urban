from typing import List, Tuple

ACHIEVEMENTS = [
    ("first_chat",      "🌱 First Steps",       "Complete your first chat",               1),
    ("chat_10",         "💬 Chatterbox",         "Complete 10 chats",                      10),
    ("chat_50",         "⭐ Regular",            "Complete 50 chats",                      50),
    ("chat_100",        "🏆 Veteran",            "Complete 100 chats",                     100),
    ("chat_500",        "👑 Legend",             "Complete 500 chats",                     500),
    ("rep_10",          "✨ Reputable",          "Earn 10 reputation points",              10),
    ("rep_50",          "🌟 Beloved",            "Earn 50 reputation points",              50),
    ("friends_5",       "👥 Social",             "Make 5 friends",                         5),
    ("friends_20",      "🤝 Connector",          "Make 20 friends",                        20),
    ("daily_7",         "📅 Week Streak",        "Claim daily reward 7 days in a row",     7),
    ("daily_30",        "🔥 Monthly Grind",      "Claim daily reward 30 days in a row",   30),
    ("coins_1000",      "💰 Saver",              "Accumulate 1,000 coins",                1000),
    ("coins_10000",     "🏦 Rich",               "Accumulate 10,000 coins",              10000),
    ("icebreaker_use",  "🎯 Icebreaker",         "Use an icebreaker command",              1),
    ("topic_use",       "📚 Topic Starter",      "Start a topic discussion",               1),
    ("reveal_mutual",   "🎭 Revealed",           "Complete a mutual reveal",               1),
]

ACHIEVEMENT_MAP = {a[0]: a for a in ACHIEVEMENTS}


async def check_and_award(db, discord_id: int) -> List[Tuple]:
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", discord_id)
        if not user:
            return []

        existing = await conn.fetch(
            "SELECT achievement_id FROM achievements WHERE discord_id = $1",
            discord_id
        )
        earned_ids = {r["achievement_id"] for r in existing}

        friend_count = await conn.fetchval(
            "SELECT COUNT(*) FROM friends WHERE user_id = $1 AND status = 'accepted'", discord_id
        )
        streak = user.get("daily_streak", 0) or 0

        new_achievements = []

        checks = {
            "first_chat":     user["chat_count"] >= 1,
            "chat_10":        user["chat_count"] >= 10,
            "chat_50":        user["chat_count"] >= 50,
            "chat_100":       user["chat_count"] >= 100,
            "chat_500":       user["chat_count"] >= 500,
            "rep_10":         user["reputation"] >= 10,
            "rep_50":         user["reputation"] >= 50,
            "friends_5":      friend_count >= 5,
            "friends_20":     friend_count >= 20,
            "daily_7":        streak >= 7,
            "daily_30":       streak >= 30,
            "coins_1000":     (user.get("coins") or 0) >= 1000,
            "coins_10000":    (user.get("coins") or 0) >= 10000,
        }

        for ach_id, met in checks.items():
            if met and ach_id not in earned_ids:
                await conn.execute(
                    "INSERT INTO achievements (discord_id, achievement_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    discord_id, ach_id
                )
                new_achievements.append(ACHIEVEMENT_MAP[ach_id])

        return new_achievements


async def award_specific(db, discord_id: int, ach_id: str) -> bool:
    if ach_id not in ACHIEVEMENT_MAP:
        return False
    async with db.pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT 1 FROM achievements WHERE discord_id = $1 AND achievement_id = $2",
            discord_id, ach_id
        )
        if existing:
            return False
        await conn.execute(
            "INSERT INTO achievements (discord_id, achievement_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            discord_id, ach_id
        )
    return True


async def get_user_achievements(db, discord_id: int) -> List[str]:
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT achievement_id FROM achievements WHERE discord_id = $1",
            discord_id
        )
        return [r["achievement_id"] for r in rows]
