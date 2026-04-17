import sys
import os
import subprocess
import threading


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


found = _fix_path()

import discord
import asyncio
import logging
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("domegle")
log.info(f"discord.py {discord.__version__} from {discord.__file__}")

if "/usr/lib/python3/dist-packages" in discord.__file__:
    log.critical("WRONG discord.py loaded!")
    sys.exit(1)

from core.database import Database

COGS = [
    "cogs.start",
    "cogs.username",
    "cogs.help_cmd",
    "cogs.connect",
    "cogs.next_cmd",
    "cogs.stop_cmd",
    "cogs.friend",
    "cogs.report",
    "cogs.block",
    "cogs.stats",
    "cogs.interests",
    "cogs.recent",
    "cogs.setup",
    "cogs.relay",
    "cogs.profile",
    "cogs.leaderboard",
    "cogs.premium",
    "cogs.rules",
    "cogs.reveal",
    "admin.network_admin",
    "cogs.icebreaker",
    "cogs.reputation",
    "cogs.search",
    "cogs.mood",
    "cogs.topic",
    "cogs.report_status",
    "cogs.ping",
    "cogs.economy",
    "cogs.achievements",
    "cogs.party",
    "cogs.filters",
    "cogs.profile_card_cmd",
    "cogs.matchmaking_hooks",
]


def run_bot():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        log.error("DISCORD_TOKEN not set — update it in the Secrets panel")
        return
    try:
        asyncio.run(bot.start(token))
    except Exception as e:
        log.error(f"Bot crashed: {e}")


class DomegleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        intents.dm_messages = True
        super().__init__(
            command_prefix=">",
            intents=intents,
            help_command=None,
        )
        self.db: Database = None
        self.matchmaking = None

    async def setup_hook(self):
        self.db = Database()
        await self.db.connect()
        await self.db.init_tables()

        from core.matchmaking import MatchmakingEngine

        self.matchmaking = MatchmakingEngine(self)
        self.matchmaking.start()

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

def _free_port(port):
    import signal
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


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    import werkzeug.serving
    from website.server import app
    import time

    port = int(os.environ.get("PORT", 5000))
    _free_port(port)
    time.sleep(0.5)

    werkzeug.serving.BaseWSGIServer.allow_reuse_address = True
    server = werkzeug.serving.make_server("0.0.0.0", port, app)
    log.info(f"Website running on port {port}")
    server.serve_forever()
