import sys
import os
import subprocess
import signal


def _fix_path():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import site; print('\\n'.join(site.getsitepackages() + [site.getusersitepackages()]))",
        ],
        capture_output=True,
        text=True,
    )
    for path in result.stdout.strip().splitlines():
        if path and os.path.isdir(path):
            discord_init = os.path.join(path, "discord", "__init__.py")
            if os.path.exists(discord_init):
                if path not in sys.path:
                    sys.path.insert(0, path)
                sys.path = [
                    p for p in sys.path if "/usr/lib/python3/dist-packages" not in p
                ]
                return path
    return None


_fix_path()

import discord
import asyncio
import logging
from discord.ext import commands
from config import DISCORD_TOKEN

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("domegle")
log.info(f"discord.py {discord.__version__} from {discord.__file__}")

if "/usr/lib/python3/dist-packages" in discord.__file__:
    log.critical("WRONG discord.py loaded!")
    sys.exit(1)

from src.database.db import Database

COGS = [
    "src.commands.start",
    "src.commands.username",
    "src.commands.help_cmd",
    "src.commands.connect",
    "src.commands.next_cmd",
    "src.commands.stop_cmd",
    "src.commands.friend",
    "src.commands.report",
    "src.commands.block",
    "src.commands.stats",
    "src.commands.interests",
    "src.commands.recent",
    "src.commands.setup",
    "src.commands.profile",
    "src.commands.leaderboard",
    "src.commands.premium",
    "src.commands.rules",
    "src.commands.reveal",
    "src.commands.network_admin",
    "src.commands.icebreaker",
    "src.commands.reputation",
    "src.commands.search",
    "src.commands.mood",
    "src.commands.topic",
    "src.commands.report_status",
    "src.commands.ping",
    "src.commands.economy",
    "src.commands.achievements",
    "src.commands.party",
    "src.commands.filters",
    "src.commands.profile_card_cmd",
    "src.events.relay",
    "src.events.matchmaking_hooks",
]


def _free_port(port: int):
    try:
        hex_port = format(port, "04X")
        with open("/proc/net/tcp") as f:
            lines = f.readlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 10:
                continue
            local_port_hex = parts[1].split(":")[1]
            if local_port_hex.upper() != hex_port:
                continue
            inode = parts[9]
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                fd_dir = f"/proc/{pid}/fd"
                try:
                    for fd in os.listdir(fd_dir):
                        try:
                            target = os.readlink(f"{fd_dir}/{fd}")
                            if f"[{inode}]" in target:
                                os.kill(int(pid), signal.SIGKILL)
                                log.info(f"Killed PID {pid} holding port {port}")
                        except (OSError, ProcessLookupError):
                            pass
                except PermissionError:
                    pass
    except Exception as e:
        log.warning(f"_free_port: {e}")


class DomegleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=">",
            intents=intents,
            help_command=None,
        )
        self.db: Database = None
        self.matchmaking = None

    async def setup_hook(self):
        try:
            self.db = Database()
            await self.db.connect()
            await self.db.init_tables()
            log.info("Database connected and initialized")
        except Exception as e:
            log.error(f"Database connection failed: {e}")
            log.warning("Bot will run in offline mode without database features")
            self.db = None

        try:
            from src.core.matchmaking import MatchmakingEngine
            self.matchmaking = MatchmakingEngine(self)
            self.matchmaking.start()
            log.info("Matchmaking engine started")
        except Exception as e:
            log.error(f"Matchmaking engine failed: {e}")
            self.matchmaking = None

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded: {cog}")
            except Exception as e:
                log.error(f"Failed {cog}: {e}")

        await self.tree.sync()
        log.info("Slash commands synced globally.")

    async def on_ready(self):
        log.info(f"Online as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="🌍 /omegleconnect"
            )
        )

    async def close(self):
        if self.matchmaking:
            self.matchmaking.stop()
        if self.db:
            await self.db.close()
        await super().close()


bot = DomegleBot()


async def _status_server(port: int):
    from aiohttp import web

    async def handle(_request):
        qs = bot.matchmaking.get_queue_sizes() if bot.matchmaking else {}
        active = qs.get("active_sessions", 0)
        queued = qs.get("text", 0) + qs.get("voice", 0)
        html = (
            "<!doctype html><html><head><meta charset=utf-8><title>Domegle Bot</title>"
            "<style>body{font-family:sans-serif;background:#000;color:#fff;padding:2rem;max-width:500px;margin:0 auto}"
            "h1{font-size:1.5rem}p{color:#aaa}strong{color:#fff}</style></head><body>"
            "<h1>🌍 Domegle Bot</h1>"
            f"<p>Status: <strong>Online</strong></p>"
            f"<p>Active sessions: <strong>{active}</strong></p>"
            f"<p>Users in queue: <strong>{queued}</strong></p>"
            "</body></html>"
        )
        return web.Response(text=html, content_type="text/html")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"Status page on port {port}")


async def main():
    token = DISCORD_TOKEN
    if not token:
        log.error("DISCORD_TOKEN not configured in config.py")
        return

    port = int(os.environ.get("PORT", 5000))
    await asyncio.sleep(1.0)
    await _status_server(port)

    await bot.start(token)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    _free_port(port)
    import time; time.sleep(0.5)
    asyncio.run(main())
