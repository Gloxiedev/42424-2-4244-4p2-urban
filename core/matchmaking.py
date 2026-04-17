import asyncio
import uuid
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List
from enum import Enum

log = logging.getLogger("domegle.matchmaking")


class ChatType(Enum):
    TEXT = "text"
    VOICE = "voice"
    FRIEND = "friend"


@dataclass
class QueueEntry:
    discord_id: int
    guild_id: int
    channel_id: int
    chat_type: ChatType
    premium: bool
    interests: List[str]
    joined_at: float = field(default_factory=time.time)


@dataclass
class Session:
    session_id: str
    user_a: int
    user_b: int
    guild_a: int
    guild_b: int
    channel_a: int
    channel_b: int
    chat_type: ChatType
    started_at: float = field(default_factory=time.time)
    voice_channel_id: Optional[int] = None


class MatchmakingEngine:
    def __init__(self, bot):
        self.bot = bot
        self._text_queue: List[QueueEntry] = []
        self._voice_queue: List[QueueEntry] = []
        self._sessions: Dict[int, Session] = {}
        self._in_queue: Set[int] = set()
        self._lock = asyncio.Lock()
        self._rate_limits: Dict[int, float] = {}
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._match_loop())
            log.info("Matchmaking loop started.")

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            log.info("Matchmaking loop stopped.")

    async def enqueue(self, entry: QueueEntry) -> str:
        async with self._lock:
            if entry.discord_id in self._in_queue:
                return "already_in_queue"
            if entry.discord_id in self._sessions:
                return "in_session"
            last = self._rate_limits.get(entry.discord_id, 0)
            if time.time() - last < 10:
                return "rate_limited"
            self._get_queue(entry.chat_type).append(entry)
            self._in_queue.add(entry.discord_id)
            log.info(f"User {entry.discord_id} queued ({entry.chat_type.value}). Size: {len(self._get_queue(entry.chat_type))}")
            return "queued"

    async def dequeue(self, discord_id: int):
        async with self._lock:
            self._remove_from_queues(discord_id)
            self._in_queue.discard(discord_id)

    def _remove_from_queues(self, discord_id: int):
        self._text_queue = [e for e in self._text_queue if e.discord_id != discord_id]
        self._voice_queue = [e for e in self._voice_queue if e.discord_id != discord_id]

    def _get_queue(self, chat_type: ChatType) -> List[QueueEntry]:
        return self._voice_queue if chat_type == ChatType.VOICE else self._text_queue

    def is_in_queue(self, discord_id: int) -> bool:
        return discord_id in self._in_queue

    async def get_session(self, discord_id: int) -> Optional[Session]:
        return self._sessions.get(discord_id)

    async def create_session(self, a: QueueEntry, b: QueueEntry) -> Session:
        session_id = str(uuid.uuid4())[:8].upper()
        session = Session(
            session_id=session_id,
            user_a=a.discord_id, user_b=b.discord_id,
            guild_a=a.guild_id, guild_b=b.guild_id,
            channel_a=a.channel_id, channel_b=b.channel_id,
            chat_type=a.chat_type,
        )
        self._sessions[a.discord_id] = session
        self._sessions[b.discord_id] = session
        self._rate_limits[a.discord_id] = time.time()
        self._rate_limits[b.discord_id] = time.time()
        try:
            await self.bot.db.increment_matches()
            await self.bot.db.add_recent_met(a.discord_id, b.discord_id)
            await self.bot.db.add_recent_met(b.discord_id, a.discord_id)
        except Exception as e:
            log.error(f"DB error in create_session: {e}", exc_info=True)
        log.info(f"Session {session_id}: {a.discord_id} <-> {b.discord_id}")
        return session

    async def end_session(self, discord_id: int) -> Optional[Session]:
        session = self._sessions.pop(discord_id, None)
        if session:
            partner_id = session.user_b if session.user_a == discord_id else session.user_a
            self._sessions.pop(partner_id, None)
            log.info(f"Session {session.session_id} ended.")
        return session

    def get_partner_id(self, discord_id: int) -> Optional[int]:
        session = self._sessions.get(discord_id)
        if not session:
            return None
        return session.user_b if session.user_a == discord_id else session.user_a

    def get_queue_sizes(self) -> dict:
        return {
            "text": len(self._text_queue),
            "voice": len(self._voice_queue),
            "active_sessions": len(self._sessions) // 2,
        }

    async def _match_loop(self):
        while True:
            try:
                await self._try_match(self._text_queue)
                await self._try_match(self._voice_queue)
            except Exception as e:
                log.error(f"Match loop error: {e}", exc_info=True)
            await asyncio.sleep(1)

    async def _try_match(self, queue: List[QueueEntry]):
        if len(queue) < 2:
            return
        async with self._lock:
            queue.sort(key=lambda e: (not e.premium, e.joined_at))
            matched, used = [], set()
            for a in queue:
                if a.discord_id in used:
                    continue
                for b in queue:
                    if b.discord_id == a.discord_id or b.discord_id in used:
                        continue
                    try:
                        blocked = await self.bot.db.is_blocked(a.discord_id, b.discord_id)
                    except Exception:
                        blocked = False
                    if blocked:
                        continue
                    matched.append((a, b))
                    used.update([a.discord_id, b.discord_id])
                    break

            for a, b in matched:
                self._remove_from_queues(a.discord_id)
                self._remove_from_queues(b.discord_id)
                self._in_queue.discard(a.discord_id)
                self._in_queue.discard(b.discord_id)
                session = await self.create_session(a, b)
                asyncio.create_task(self._notify_match(a, b, session))

    async def _notify_match(self, a: QueueEntry, b: QueueEntry, session: Session):
        import discord
        try:
            user_a = await self.bot.db.get_user(a.discord_id)
            user_b = await self.bot.db.get_user(b.discord_id)
            name_a = ("💎 " if user_a["premium"] else "") + user_a["username"]
            name_b = ("💎 " if user_b["premium"] else "") + user_b["username"]

            def make_embed(partner_name):
                e = discord.Embed(
                    title="🌍 Stranger Connected!",
                    description=(
                        f"You are now chatting with **{partner_name}**\n\n"
                        "Send a message to start chatting!\n"
                        "`/next` — new stranger • `/stop` — leave • `/report` — report • `/reveal` — reveal identity"
                    ),
                    color=0x2ECC71
                )
                e.set_footer(text=f"Session #{session.session_id} • Messages relay anonymously")
                return e

            ch_a = self.bot.get_channel(a.channel_id)
            if ch_a is None:
                try:
                    ch_a = await self.bot.fetch_channel(a.channel_id)
                except Exception:
                    ch_a = None
            ch_b = self.bot.get_channel(b.channel_id)
            if ch_b is None:
                try:
                    ch_b = await self.bot.fetch_channel(b.channel_id)
                except Exception:
                    ch_b = None

            # Fetch users to get mentions - use cache first, fall back to fetch
            da = self.bot.get_user(a.discord_id)
            db_ = self.bot.get_user(b.discord_id)

            if ch_a:
                mention = da.mention if da else f"<@{a.discord_id}>"
                await ch_a.send(content=mention, embed=make_embed(name_b))
            if ch_b:
                mention = db_.mention if db_ else f"<@{b.discord_id}>"
                await ch_b.send(content=mention, embed=make_embed(name_a))

            if session.chat_type == ChatType.VOICE:
                await self._setup_voice(a, b, session)

        except Exception as e:
            log.error(f"Notify match error: {e}", exc_info=True)

    async def _setup_voice(self, a: QueueEntry, b: QueueEntry, session: Session):
        try:
            guild = self.bot.get_guild(a.guild_id) or self.bot.get_guild(b.guild_id)
            if not guild:
                return
            channel = await guild.create_voice_channel(f"🎙 domegle-{session.session_id}")
            session.voice_channel_id = channel.id
            ma = guild.get_member(a.discord_id)
            mb = guild.get_member(b.discord_id)
            if ma and ma.voice:
                await ma.move_to(channel)
            if mb and mb.voice:
                await mb.move_to(channel)
        except Exception as e:
            log.error(f"Voice setup error: {e}", exc_info=True)

    async def cleanup_voice_session(self, session: Session):
        if not session.voice_channel_id:
            return
        try:
            ch = self.bot.get_channel(session.voice_channel_id)
            if ch:
                await ch.delete()
        except Exception as e:
            log.error(f"Voice cleanup error: {e}")
