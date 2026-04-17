import discord
from discord.ext import commands
from core.spam_detection import is_spam, is_phishing, is_in_cooldown, set_cooldown, clear_history
from core.economy import award_coins, CHAT_REWARD

BLOCKED_WORDS = ["nigger", "nigga", "faggot", "retard"]

_session_start_times: dict = {}


class Relay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if getattr(self.bot, "db", None) is None:
            return
        mm = self.bot.matchmaking
        if mm is None:
            return

        in_dm = isinstance(message.channel, discord.DMChannel)
        in_guild = message.guild is not None

        if not in_dm and not in_guild:
            return

        if in_guild:
            server = await self.bot.db.get_server(message.guild.id)
            if not server or server["text_channel_id"] != message.channel.id:
                return

        session = await mm.get_session(message.author.id)

        if in_guild and not session:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            return

        if in_dm and not session:
            return

        if message.content.startswith("/") or message.content.startswith(">"):
            return

        user = await self.bot.db.get_user(message.author.id)
        if not user:
            return

        if message.content and any(w in message.content.lower() for w in BLOCKED_WORDS):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            try:
                await message.channel.send(
                    f"⚠️ {message.author.mention} Message blocked for rule violation.",
                    delete_after=5
                )
            except Exception:
                pass
            return

        if message.content and is_phishing(message.content):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            try:
                await message.channel.send(
                    f"🚫 {message.author.mention} Suspicious link blocked. Use `/report` if someone is scamming you.",
                    delete_after=8
                )
            except Exception:
                pass
            return

        if message.content and is_spam(message.author.id, message.content):
            if not is_in_cooldown(message.author.id):
                set_cooldown(message.author.id)
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention} You're sending messages too fast. Slow down!",
                        delete_after=5
                    )
                except Exception:
                    pass
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
            return

        partner_id = mm.get_partner_id(message.author.id)
        if not partner_id:
            return

        partner_ch_id = session.channel_b if session.user_a == message.author.id else session.channel_a
        partner_ch = self.bot.get_channel(partner_ch_id)

        if partner_ch is None:
            try:
                partner_ch = await self.bot.fetch_channel(partner_ch_id)
            except Exception:
                return

        if in_guild and not isinstance(partner_ch, discord.DMChannel):
            if partner_ch_id == message.channel.id:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass

        display = ("💎 " if user["premium"] else "") + user["username"]
        if user.get("title"):
            display += f" · {user['title']}"

        files = []
        for att in message.attachments:
            try:
                files.append(await att.to_file())
            except Exception:
                pass

        e = discord.Embed(description=message.content or None, color=0x5865F2)
        e.set_author(name=display)

        try:
            await partner_ch.send(embed=e, files=files)
        except (discord.Forbidden, Exception):
            pass


async def setup(bot):
    await bot.add_cog(Relay(bot))
