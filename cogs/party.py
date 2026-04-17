import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, ok, err, info, embed
import uuid
import asyncio

_parties: dict = {}
_user_party: dict = {}


class Party(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="party_create", description="Create a group chat party (up to 5 people)")
    async def party_create(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if interaction.user.id in _user_party:
            await interaction.response.send_message(embed=err("Already in Party", "Use `/party_leave` first."), ephemeral=True)
            return

        user = await self.bot.db.get_user(interaction.user.id)
        party_id = str(uuid.uuid4())[:6].upper()
        _parties[party_id] = {
            "host": interaction.user.id,
            "members": {interaction.user.id: {"channel_id": interaction.channel_id, "guild_id": interaction.guild_id, "username": user["username"], "premium": user["premium"]}},
            "max": 5,
            "active": False,
        }
        _user_party[interaction.user.id] = party_id

        e = discord.Embed(
            title="🎉 Party Created!",
            description=f"Party code: **`{party_id}`**\n\nShare this code with friends — they join with `/party_join {party_id}`\n\nMembers: **1/5**\n\nRun `/party_start` when ready!",
            color=0x2ECC71
        )
        e.set_footer(text="Party auto-dissolves after 10 minutes of inactivity")
        await interaction.response.send_message(embed=e, ephemeral=True)
        asyncio.create_task(self._expire_party(party_id))

    @app_commands.command(name="party_join", description="Join a group chat party")
    @app_commands.describe(code="Party code from the host")
    async def party_join(self, interaction: discord.Interaction, code: str):
        if not await require_user(interaction):
            return
        code = code.upper()
        if interaction.user.id in _user_party:
            await interaction.response.send_message(embed=err("Already in Party", "Use `/party_leave` first."), ephemeral=True)
            return
        if code not in _parties:
            await interaction.response.send_message(embed=err("Not Found", f"No party with code `{code}`."), ephemeral=True)
            return

        party = _parties[code]
        if party["active"]:
            await interaction.response.send_message(embed=err("Already Started", "That party chat has already begun."), ephemeral=True)
            return
        if len(party["members"]) >= party["max"]:
            await interaction.response.send_message(embed=err("Full", "This party is full (5/5)."), ephemeral=True)
            return

        user = await self.bot.db.get_user(interaction.user.id)
        party["members"][interaction.user.id] = {
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "username": user["username"],
            "premium": user["premium"],
        }
        _user_party[interaction.user.id] = code

        await interaction.response.send_message(
            embed=ok("✅ Joined Party!", f"You joined party **{code}**!\nMembers: **{len(party['members'])}/{party['max']}**"),
            ephemeral=True
        )
        await self._broadcast_party(code, interaction.user.id, f"**{user['username']}** joined the party! ({len(party['members'])}/{party['max']})")

    @app_commands.command(name="party_start", description="Start the party group chat")
    async def party_start(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        pid = _user_party.get(interaction.user.id)
        if not pid or pid not in _parties:
            await interaction.response.send_message(embed=err("Not in Party", "Create or join a party first."), ephemeral=True)
            return
        party = _parties[pid]
        if party["host"] != interaction.user.id:
            await interaction.response.send_message(embed=err("Not Host", "Only the party host can start the chat."), ephemeral=True)
            return
        if len(party["members"]) < 2:
            await interaction.response.send_message(embed=err("Too Few Members", "You need at least 2 members to start."), ephemeral=True)
            return

        party["active"] = True
        names = " • ".join(m["username"] for m in party["members"].values())
        e = discord.Embed(
            title="🎉 Party Chat Started!",
            description=f"**{len(party['members'])} people** are now in a group chat!\n\n**Members:** {names}\n\nSend messages normally — they'll be relayed to everyone.\nUse `/party_leave` to exit.",
            color=0x9B59B6
        )
        await interaction.response.send_message(embed=ok("✅ Started!", "Party chat is live! Check your channel."), ephemeral=True)
        await self._broadcast_party(pid, None, None, embed=e)

    @app_commands.command(name="party_leave", description="Leave the current party")
    async def party_leave(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        pid = _user_party.pop(interaction.user.id, None)
        if not pid or pid not in _parties:
            await interaction.response.send_message(embed=err("Not in Party", "You're not in a party."), ephemeral=True)
            return

        party = _parties[pid]
        user = await self.bot.db.get_user(interaction.user.id)
        party["members"].pop(interaction.user.id, None)

        if not party["members"] or interaction.user.id == party["host"]:
            for uid in list(party["members"].keys()):
                _user_party.pop(uid, None)
            _parties.pop(pid, None)
            await interaction.response.send_message(embed=ok("👋 Left", "Party disbanded."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=ok("👋 Left", f"You left party **{pid}**."), ephemeral=True)
            await self._broadcast_party(pid, interaction.user.id, f"**{user['username']}** left the party.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.startswith("/") or message.content.startswith(">"):
            return
        pid = _user_party.get(message.author.id)
        if not pid or pid not in _parties:
            return
        party = _parties[pid]
        if not party["active"]:
            return
        sender_info = party["members"].get(message.author.id)
        if not sender_info:
            return
        sender_ch_id = sender_info["channel_id"]
        if message.channel.id != sender_ch_id:
            return

        name = ("💎 " if sender_info["premium"] else "") + sender_info["username"]
        e = discord.Embed(description=message.content, color=0x9B59B6)
        e.set_author(name=f"[Party] {name}")

        for uid, minfo in party["members"].items():
            if uid == message.author.id:
                continue
            ch = self.bot.get_channel(minfo["channel_id"])
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(minfo["channel_id"])
                except Exception:
                    continue
            try:
                await ch.send(embed=e)
            except Exception:
                pass

    async def _broadcast_party(self, pid: str, exclude_id: int, text: str, embed: discord.Embed = None):
        party = _parties.get(pid)
        if not party:
            return
        for uid, minfo in party["members"].items():
            if uid == exclude_id:
                continue
            ch = self.bot.get_channel(minfo["channel_id"])
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(minfo["channel_id"])
                except Exception:
                    continue
            try:
                if embed:
                    await ch.send(embed=embed)
                elif text:
                    from core.utils import embed as mk_embed
                    await ch.send(embed=mk_embed("🎉 Party", text))
            except Exception:
                pass

    async def _expire_party(self, pid: str):
        await asyncio.sleep(600)
        if pid in _parties and not _parties[pid]["active"]:
            party = _parties.pop(pid, None)
            if party:
                for uid in party["members"]:
                    _user_party.pop(uid, None)


async def setup(bot):
    await bot.add_cog(Party(bot))
