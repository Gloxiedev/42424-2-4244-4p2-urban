import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, embed, ok, err, info
import asyncio

_pending_reveals: dict = {}


class Reveal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reveal", description="Request to reveal your Discord profile to your chat partner")
    async def reveal(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm = self.bot.matchmaking
        if mm is None:
            await interaction.response.send_message(embed=err("Error", "Matchmaking unavailable."), ephemeral=True)
            return

        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to use `/reveal`."),
                ephemeral=True
            )
            return

        partner_id = mm.get_partner_id(interaction.user.id)
        if not partner_id:
            await interaction.response.send_message(embed=err("Error", "Could not find your chat partner."), ephemeral=True)
            return

        sid = session.session_id
        if sid not in _pending_reveals:
            _pending_reveals[sid] = set()

        if interaction.user.id in _pending_reveals[sid]:
            await interaction.response.send_message(
                embed=info("Already Requested", "You already requested a reveal. Waiting for your partner to type `/reveal` too."),
                ephemeral=True
            )
            return

        _pending_reveals[sid].add(interaction.user.id)

        user = await self.bot.db.get_user(interaction.user.id)
        partner_user = await self.bot.db.get_user(partner_id)
        my_name = ("💎 " if user["premium"] else "") + user["username"]
        partner_name = ("💎 " if partner_user["premium"] else "") + partner_user["username"]

        partner_ch_id = session.channel_b if session.user_a == interaction.user.id else session.channel_a
        partner_ch = self.bot.get_channel(partner_ch_id)
        if partner_ch is None:
            try:
                partner_ch = await self.bot.fetch_channel(partner_ch_id)
            except Exception:
                partner_ch = None

        both_agreed = partner_id in _pending_reveals[sid]

        if both_agreed:
            _pending_reveals.pop(sid, None)

            discord_user = interaction.user
            partner_discord = self.bot.get_user(partner_id)
            if partner_discord is None:
                try:
                    partner_discord = await self.bot.fetch_user(partner_id)
                except Exception:
                    partner_discord = None

            partner_tag = str(partner_discord) if partner_discord else f"Unknown#{partner_id}"
            partner_mention = partner_discord.mention if partner_discord else f"<@{partner_id}>"
            partner_avatar = partner_discord.display_avatar.url if partner_discord else None

            user_reveal = discord.Embed(
                title="🎭 Reveal Accepted!",
                description=(
                    f"**Both of you agreed to reveal.**\n\n"
                    f"Your partner is:\n"
                    f"**{partner_tag}**\n"
                    f"{partner_mention}\n"
                    f"ID: `{partner_id}`\n\n"
                    f"You can now add each other on Discord directly!"
                ),
                color=0x2ECC71
            )
            if partner_avatar:
                user_reveal.set_thumbnail(url=partner_avatar)
            user_reveal.set_footer(text=f"Session #{sid} • Revealed")

            partner_reveal = discord.Embed(
                title="🎭 Reveal Accepted!",
                description=(
                    f"**Both of you agreed to reveal.**\n\n"
                    f"Your partner is:\n"
                    f"**{str(discord_user)}**\n"
                    f"{discord_user.mention}\n"
                    f"ID: `{discord_user.id}`\n\n"
                    f"You can now add each other on Discord directly!"
                ),
                color=0x2ECC71
            )
            partner_reveal.set_thumbnail(url=discord_user.display_avatar.url)
            partner_reveal.set_footer(text=f"Session #{sid} • Revealed")

            await interaction.response.send_message(embed=user_reveal)
            if partner_ch:
                try:
                    await partner_ch.send(embed=partner_reveal)
                except Exception:
                    pass

            public = discord.Embed(
                title="🎭 Mutual Reveal",
                description=f"**{my_name}** and **{partner_name}** revealed their Discord profiles to each other.",
                color=0x9B59B6
            )
            public.set_footer(text="Use /reveal to do the same with your partner")

            try:
                if isinstance(interaction.channel, discord.DMChannel):
                    await interaction.channel.send(embed=public)
                else:
                    await interaction.channel.send(embed=public)
            except Exception:
                pass

            if partner_ch and partner_ch.id != interaction.channel_id:
                try:
                    await partner_ch.send(embed=public)
                except Exception:
                    pass

        else:
            await interaction.response.send_message(
                embed=ok(
                    "📤 Reveal Requested",
                    "Request sent to your partner.\n\n"
                    "If they also type `/reveal`, both profiles will be shown.\n\n"
                    "**This is optional** — they can ignore it.\n"
                    "Expires in 2 minutes."
                ),
                ephemeral=True
            )

            notify = discord.Embed(
                title="🎭 Reveal Request",
                description=(
                    f"**{my_name}** wants to reveal their Discord profile to you.\n\n"
                    f"Type `/reveal` to accept and see who they are.\n"
                    f"You can ignore this to stay anonymous.\n\n"
                    f"*Expires in 2 minutes.*"
                ),
                color=0x9B59B6
            )
            notify.set_footer(text="Both must type /reveal for profiles to be shown")

            if partner_ch:
                partner_discord = self.bot.get_user(partner_id)
                try:
                    await partner_ch.send(
                        content=partner_discord.mention if partner_discord else f"<@{partner_id}>",
                        embed=notify
                    )
                except Exception:
                    pass

            asyncio.create_task(self._expire_reveal(sid, interaction.user.id, interaction.channel_id, partner_ch_id, my_name))

    async def _expire_reveal(self, sid: str, requester_id: int, req_ch_id: int, partner_ch_id: int, requester_name: str):
        await asyncio.sleep(120)
        if sid not in _pending_reveals:
            return
        if requester_id not in _pending_reveals.get(sid, set()):
            return

        _pending_reveals[sid].discard(requester_id)
        if not _pending_reveals[sid]:
            _pending_reveals.pop(sid, None)

        for ch_id, msg in [(req_ch_id, "Your reveal request expired."), (partner_ch_id, f"**{requester_name}**'s reveal request expired.")]:
            if not ch_id or ch_id == partner_ch_id and ch_id == req_ch_id:
                continue
            ch = self.bot.get_channel(ch_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(ch_id)
                except Exception:
                    continue
            try:
                await ch.send(embed=embed("⏰ Reveal Expired", msg), delete_after=10)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Reveal(bot))
