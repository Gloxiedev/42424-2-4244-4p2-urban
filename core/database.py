import asyncpg
import os
import logging
from typing import Optional

log = logging.getLogger("domegle.db")


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool = None

    async def connect(self):
        dsn = os.getenv("DATABASE_URL")
        self.pool = await asyncpg.create_pool(dsn, min_size=3, max_size=10)
        log.info("Connected to database.")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id      BIGINT PRIMARY KEY,
                    username        TEXT UNIQUE NOT NULL,
                    premium         BOOLEAN DEFAULT FALSE,
                    reputation      INT DEFAULT 0,
                    interests       TEXT[] DEFAULT '{}',
                    banned          BOOLEAN DEFAULT FALSE,
                    ban_reason      TEXT,
                    chat_count      INT DEFAULT 0,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    last_seen       TIMESTAMPTZ DEFAULT NOW(),
                    captcha_passed  BOOLEAN DEFAULT FALSE,
                    last_connect    TIMESTAMPTZ,
                    coins           INT DEFAULT 0,
                    daily_streak    INT DEFAULT 0,
                    last_daily      TIMESTAMPTZ,
                    title           TEXT DEFAULT '',
                    shadow_banned   BOOLEAN DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS servers (
                    guild_id         BIGINT PRIMARY KEY,
                    text_channel_id  BIGINT,
                    voice_channel_id BIGINT,
                    setup_by         BIGINT,
                    created_at       TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS friends (
                    id         SERIAL PRIMARY KEY,
                    user_id    BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    friend_id  BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    status     TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, friend_id)
                );
                CREATE TABLE IF NOT EXISTS blocks (
                    blocker_id BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    blocked_id BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(blocker_id, blocked_id)
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id          SERIAL PRIMARY KEY,
                    reporter_id BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    reported_id BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    reason      TEXT,
                    session_id  TEXT,
                    reviewed    BOOLEAN DEFAULT FALSE,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS recent_met (
                    id          SERIAL PRIMARY KEY,
                    user_id     BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    met_user_id BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    met_at      TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS stats (
                    id            SERIAL PRIMARY KEY,
                    matches_today INT DEFAULT 0,
                    total_matches INT DEFAULT 0,
                    date          DATE DEFAULT CURRENT_DATE UNIQUE
                );
                CREATE TABLE IF NOT EXISTS developers (
                    discord_id BIGINT PRIMARY KEY,
                    added_at   TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS achievements (
                    id             SERIAL PRIMARY KEY,
                    discord_id     BIGINT REFERENCES users(discord_id) ON DELETE CASCADE,
                    achievement_id TEXT NOT NULL,
                    earned_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(discord_id, achievement_id)
                );
                INSERT INTO stats (date) VALUES (CURRENT_DATE) ON CONFLICT DO NOTHING;
            """)
            await conn.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INT DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_streak INT DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily TIMESTAMPTZ;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS title TEXT DEFAULT '';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS shadow_banned BOOLEAN DEFAULT FALSE;
            """)
        log.info("Tables ready.")

    async def get_user(self, discord_id: int) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", discord_id)

    async def get_user_by_username(self, username: str) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE LOWER(username) = LOWER($1)", username)

    async def create_user(self, discord_id: int, username: str) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO users (discord_id, username) VALUES ($1, $2)", discord_id, username)
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def update_user(self, discord_id: int, **kwargs):
        if not kwargs:
            return
        cols = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
        async with self.pool.acquire() as conn:
            await conn.execute(f"UPDATE users SET {cols} WHERE discord_id = $1", discord_id, *list(kwargs.values()))

    async def set_interests(self, discord_id: int, interests: list):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET interests = $1 WHERE discord_id = $2", interests, discord_id)

    async def ban_user(self, discord_id: int, reason: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET banned = TRUE, ban_reason = $1 WHERE discord_id = $2", reason, discord_id)

    async def unban_user(self, discord_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET banned = FALSE, ban_reason = NULL WHERE discord_id = $1", discord_id)

    async def shadow_ban_user(self, discord_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET shadow_banned = TRUE WHERE discord_id = $1", discord_id)

    async def get_server(self, guild_id: int) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM servers WHERE guild_id = $1", guild_id)

    async def upsert_server(self, guild_id: int, **kwargs):
        existing = await self.get_server(guild_id)
        async with self.pool.acquire() as conn:
            if existing:
                cols = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
                await conn.execute(f"UPDATE servers SET {cols} WHERE guild_id = $1", guild_id, *list(kwargs.values()))
            else:
                kwargs["guild_id"] = guild_id
                cols = ", ".join(kwargs.keys())
                placeholders = ", ".join(f"${i+1}" for i in range(len(kwargs)))
                await conn.execute(f"INSERT INTO servers ({cols}) VALUES ({placeholders})", *list(kwargs.values()))

    async def send_friend_request(self, user_id: int, friend_id: int) -> str:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO friends (user_id, friend_id, status) VALUES ($1, $2, 'pending')",
                    user_id, friend_id
                )
            return "sent"
        except asyncpg.UniqueViolationError:
            return "exists"

    async def accept_friend_request(self, accepter_id: int, requester_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE friends SET status = 'accepted' WHERE user_id = $1 AND friend_id = $2",
                requester_id, accepter_id
            )
            await conn.execute(
                """
                INSERT INTO friends (user_id, friend_id, status)
                VALUES ($1, $2, 'accepted')
                ON CONFLICT (user_id, friend_id) DO UPDATE SET status = 'accepted'
                """,
                accepter_id, requester_id
            )

    async def remove_friend(self, user_id: int, friend_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM friends WHERE (user_id=$1 AND friend_id=$2) OR (user_id=$2 AND friend_id=$1)",
                user_id, friend_id
            )

    async def get_friends(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT u.username, u.discord_id, u.premium
                FROM friends f
                JOIN users u ON u.discord_id = f.friend_id
                WHERE f.user_id = $1 AND f.status = 'accepted'
                ORDER BY u.username
            """, user_id)

    async def get_pending_requests(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT u.username, u.discord_id
                FROM friends f
                JOIN users u ON u.discord_id = f.user_id
                WHERE f.friend_id = $1 AND f.status = 'pending'
                ORDER BY f.created_at DESC
            """, user_id)

    async def are_friends(self, user_id: int, friend_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM friends WHERE user_id=$1 AND friend_id=$2 AND status='accepted'",
                user_id, friend_id
            )
            return row is not None

    async def block_user(self, blocker_id: int, blocked_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO blocks (blocker_id, blocked_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                blocker_id, blocked_id
            )

    async def is_blocked(self, user_a: int, user_b: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM blocks WHERE (blocker_id=$1 AND blocked_id=$2) OR (blocker_id=$2 AND blocked_id=$1)",
                user_a, user_b
            )
            return row is not None

    async def file_report(self, reporter_id: int, reported_id: int, reason: str, session_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reports (reporter_id, reported_id, reason, session_id) VALUES ($1,$2,$3,$4)",
                reporter_id, reported_id, reason, session_id
            )

    async def get_report_count(self, reported_id: int) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM reports WHERE reported_id=$1 AND reviewed=FALSE",
                reported_id
            )

    async def get_all_reports(self, limit: int = 20):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT r.*, u1.username as reporter_name, u2.username as reported_name
                FROM reports r
                JOIN users u1 ON u1.discord_id = r.reporter_id
                JOIN users u2 ON u2.discord_id = r.reported_id
                ORDER BY r.created_at DESC LIMIT $1
            """, limit)

    async def add_recent_met(self, user_id: int, met_user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM recent_met WHERE user_id=$1 AND met_user_id=$2",
                user_id, met_user_id
            )
            await conn.execute(
                "INSERT INTO recent_met (user_id, met_user_id) VALUES ($1,$2)",
                user_id, met_user_id
            )
            await conn.execute("""
                DELETE FROM recent_met WHERE id IN (
                    SELECT id FROM recent_met
                    WHERE user_id=$1
                    ORDER BY met_at DESC
                    OFFSET 10
                )
            """, user_id)

    async def get_recent_met(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT u.username, u.discord_id, u.premium, rm.met_at
                FROM recent_met rm
                JOIN users u ON u.discord_id = rm.met_user_id
                WHERE rm.user_id=$1
                ORDER BY rm.met_at DESC
            """, user_id)

    async def increment_matches(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stats (date, matches_today, total_matches)
                VALUES (CURRENT_DATE, 1, 1)
                ON CONFLICT (date) DO UPDATE
                SET matches_today = stats.matches_today + 1,
                    total_matches = stats.total_matches + 1
            """)

    async def get_global_stats(self):
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            total_servers = await conn.fetchval("SELECT COUNT(*) FROM servers")
            today = await conn.fetchrow("SELECT * FROM stats WHERE date = CURRENT_DATE")
            total_matches = await conn.fetchval("SELECT SUM(total_matches) FROM stats") or 0
            return {
                "total_users": total_users or 0,
                "total_servers": total_servers or 0,
                "matches_today": today["matches_today"] if today else 0,
                "total_matches": total_matches,
            }

    async def get_developers(self) -> set:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT discord_id FROM developers")
            return {r["discord_id"] for r in rows}

    async def add_developer(self, discord_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO developers (discord_id) VALUES ($1) ON CONFLICT DO NOTHING",
                discord_id
            )

    async def remove_developer(self, discord_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM developers WHERE discord_id=$1", discord_id)

    async def get_pending_sent(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT u.username, u.discord_id
                FROM friends f JOIN users u ON u.discord_id = f.friend_id
                WHERE f.user_id = $1 AND f.status = 'pending'
                ORDER BY f.created_at DESC
            """, user_id)
