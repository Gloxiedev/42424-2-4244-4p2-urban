import discord
from discord.ext import commands
import os
import logging

log = logging.getLogger("domegle.admin")

HARDCODED_DEV = 1074288861716422707


async def get_all_devs(bot) -> set:
    db_devs = await bot.db.get_developers()
    return db_devs | {HARDCODED_DEV}


def is_developer():
    async def predicate(ctx: commands.Context) -> bool:
        devs = await get_all_devs(ctx.bot)
        if ctx.author.id in devs:
            return True
        await ctx.reply("❌ Not authorized.")
        return False
    return commands.check(predicate)


class NetworkAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="domegleban")
    @is_developer()
    async def ban(self, ctx, username: str, *, reason: str = "No reason provided"):
        user = await self.bot.db.get_user_by_username(username)
        if not user:
            await ctx.reply(f"❌ No user: `{username}`")
            return
        if user["banned"]:
            await ctx.reply(f"⚠️ `{username}` is already banned.")
            return
        await self.bot.db.ban_user(user["discord_id"], reason)
        mm = self.bot.matchmaking
        if mm:
            session = await mm.get_session(user["discord_id"])
            if session:
                partner_id = mm.get_partner_id(user["discord_id"])
                ended = await mm.end_session(user["discord_id"])
                if partner_id and ended:
                    ch_id = ended.channel_b if ended.user_a == user["discord_id"] else ended.channel_a
                    ch = self.bot.get_channel(ch_id)
                    if ch:
                        await ch.send(embed=discord.Embed(title="👋 Stranger Left", description="Removed from Domegle.", color=0xE74C3C))
                if ended and ended.voice_channel_id:
                    await mm.cleanup_voice_session(ended)
            await mm.dequeue(user["discord_id"])
        target = self.bot.get_user(user["discord_id"])
        if target:
            try:
                await target.send(embed=discord.Embed(title="🔨 Banned from Domegle", description=f"**Reason:** {reason}", color=0xE74C3C))
            except discord.Forbidden:
                pass
        await ctx.reply(embed=discord.Embed(title="🔨 Banned", description=f"**{username}** (`{user['discord_id']}`)\n**Reason:** {reason}", color=0xE74C3C))
        log.warning(f"[ADMIN] {ctx.author} banned {username}: {reason}")

    @commands.command(name="domegleunban")
    @is_developer()
    async def unban(self, ctx, username: str):
        user = await self.bot.db.get_user_by_username(username)
        if not user:
            await ctx.reply(f"❌ No user: `{username}`")
            return
        if not user["banned"]:
            await ctx.reply(f"⚠️ `{username}` is not banned.")
            return
        await self.bot.db.unban_user(user["discord_id"])
        target = self.bot.get_user(user["discord_id"])
        if target:
            try:
                await target.send(embed=discord.Embed(title="✅ Ban Lifted", description="Your ban has been removed.", color=0x2ECC71))
            except discord.Forbidden:
                pass
        await ctx.reply(embed=discord.Embed(title="✅ Unbanned", description=f"**{username}** unbanned.", color=0x2ECC71))

    @commands.command(name="reports")
    @is_developer()
    async def reports(self, ctx, limit: int = 10):
        rows = await self.bot.db.get_all_reports(min(limit, 25))
        if not rows:
            await ctx.reply("📭 No reports.")
            return
        e = discord.Embed(title=f"🚨 Reports ({len(rows)})", color=0xE74C3C)
        for r in rows:
            e.add_field(
                name=f"#{r['id']} — {r['reported_name']}",
                value=f"**By:** {r['reporter_name']}\n**Reason:** {r['reason']}\n**Session:** {r['session_id']}\n**Time:** <t:{int(r['created_at'].timestamp())}:R>",
                inline=False
            )
        await ctx.reply(embed=e)

    @commands.command(name="globalstats")
    @is_developer()
    async def globalstats(self, ctx):
        s = await self.bot.db.get_global_stats()
        mm = self.bot.matchmaking
        qs = mm.get_queue_sizes() if mm else {}
        async with self.bot.db.pool.acquire() as conn:
            banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE banned = TRUE")
            premium = await conn.fetchval("SELECT COUNT(*) FROM users WHERE premium = TRUE")
        e = discord.Embed(title="🌍 Global Stats [ADMIN]", color=0x5865F2)
        e.add_field(name="Users", value=str(s["total_users"]), inline=True)
        e.add_field(name="Servers", value=str(s["total_servers"]), inline=True)
        e.add_field(name="Premium", value=str(premium), inline=True)
        e.add_field(name="Banned", value=str(banned), inline=True)
        e.add_field(name="Matches Today", value=str(s["matches_today"]), inline=True)
        e.add_field(name="Total Matches", value=str(s["total_matches"]), inline=True)
        e.add_field(name="Text Queue", value=str(qs.get("text", 0)), inline=True)
        e.add_field(name="Voice Queue", value=str(qs.get("voice", 0)), inline=True)
        e.add_field(name="Active Sessions", value=str(qs.get("active_sessions", 0)), inline=True)
        await ctx.reply(embed=e)

    @commands.command(name="lookup")
    @is_developer()
    async def lookup(self, ctx, username: str):
        user = await self.bot.db.get_user_by_username(username)
        if not user:
            await ctx.reply(f"❌ No user: `{username}`")
            return
        reports = await self.bot.db.get_report_count(user["discord_id"])
        e = discord.Embed(title=f"🔍 {user['username']}", color=0x3498DB)
        e.add_field(name="Discord ID", value=str(user["discord_id"]), inline=True)
        e.add_field(name="Premium", value="✅" if user["premium"] else "❌", inline=True)
        e.add_field(name="Banned", value="🔨" if user["banned"] else "✅", inline=True)
        e.add_field(name="Ban Reason", value=user["ban_reason"] or "—", inline=True)
        e.add_field(name="Chats", value=str(user["chat_count"]), inline=True)
        e.add_field(name="Reports Against", value=str(reports), inline=True)
        e.add_field(name="Interests", value=", ".join(user["interests"]) or "None", inline=False)
        e.add_field(name="Joined", value=f"<t:{int(user['created_at'].timestamp())}:R>", inline=True)
        await ctx.reply(embed=e)

    @commands.command(name="setpremium")
    @is_developer()
    async def setpremium(self, ctx, username: str, value: str = "true"):
        user = await self.bot.db.get_user_by_username(username)
        if not user:
            await ctx.reply(f"❌ No user: `{username}`")
            return
        is_p = value.lower() in ("true", "1", "yes", "on")
        await self.bot.db.update_user(user["discord_id"], premium=is_p)
        await ctx.reply(f"💎 Premium {'granted ✅' if is_p else 'revoked ❌'} for **{username}**.")

    @commands.command(name="devadd")
    @is_developer()
    async def devadd(self, ctx, user_id: int):
        await self.bot.db.add_developer(user_id)
        user = self.bot.get_user(user_id)
        name = str(user) if user else str(user_id)
        await ctx.reply(embed=discord.Embed(title="✅ Developer Added", description=f"**{name}** (`{user_id}`) now has developer access.", color=0x2ECC71))
        log.info(f"[ADMIN] {ctx.author} added developer {user_id}")

    @commands.command(name="devremove")
    @is_developer()
    async def devremove(self, ctx, user_id: int):
        if user_id == HARDCODED_DEV:
            await ctx.reply("❌ Cannot remove the root developer.")
            return
        await self.bot.db.remove_developer(user_id)
        await ctx.reply(embed=discord.Embed(title="✅ Removed", description=f"`{user_id}` removed from developers.", color=0xE74C3C))

    @commands.command(name="devlist")
    @is_developer()
    async def devlist(self, ctx):
        devs = await get_all_devs(self.bot)
        lines = "\n".join(f"• `{d}`" + (" *(root)*" if d == HARDCODED_DEV else "") for d in sorted(devs))
        await ctx.reply(embed=discord.Embed(title="👑 Developers", description=lines or "None", color=0x5865F2))


async def setup(bot):
    await bot.add_cog(NetworkAdmin(bot))
