import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, require_chat_context, ok, err, info, embed
from core.matchmaking import MatchmakingEngine

_rep_given: dict = {}


class Reputation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rep", description="Give your chat partner a +1 reputation after a good chat")
    async def rep(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return
        if not await require_chat_context(interaction):
            return

        mm: MatchmakingEngine = self.bot.matchmaking
        session = await mm.get_session(interaction.user.id)
        if not session:
            await interaction.response.send_message(
                embed=err("Not in Chat", "You need to be in an active chat to give reputation."),
                ephemeral=True
            )
            return

        partner_id = mm.get_partner_id(interaction.user.id)
        if not partner_id:
            await interaction.response.send_message(embed=err("Error", "Could not find your partner."), ephemeral=True)
            return

        sid = session.session_id
        already_given = _rep_given.get(sid, set())
        if interaction.user.id in already_given:
            await interaction.response.send_message(
                embed=info("Already Given", "You already gave rep in this session. One per chat!"),
                ephemeral=True
            )
            return

        if sid not in _rep_given:
            _rep_given[sid] = set()
        _rep_given[sid].add(interaction.user.id)

        async with self.bot.db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET reputation = reputation + 1 WHERE discord_id = $1",
                partner_id
            )
            new_rep = await conn.fetchval("SELECT reputation FROM users WHERE discord_id = $1", partner_id)

        partner_user = await self.bot.db.get_user(partner_id)
        partner_name = ("💎 " if partner_user["premium"] else "") + partner_user["username"]
        me = await self.bot.db.get_user(interaction.user.id)
        my_name = ("💎 " if me["premium"] else "") + me["username"]

        partner_ch_id = session.channel_b if session.user_a == interaction.user.id else session.channel_a
        partner_ch = self.bot.get_channel(partner_ch_id)
        if partner_ch is None:
            try:
                partner_ch = await self.bot.fetch_channel(partner_ch_id)
            except Exception:
                partner_ch = None

        await interaction.response.send_message(
            embed=ok("⭐ Rep Given!", f"You gave **{partner_name}** +1 reputation!\nTheir rep is now **{new_rep}**."),
            ephemeral=True
        )

        if partner_ch:
            try:
                notify = discord.Embed(
                    title="⭐ You received +1 Reputation!",
                    description=f"**{my_name}** liked chatting with you!\nYour reputation is now **{new_rep}**.",
                    color=0xF1C40F
                )
                notify.set_footer(text="Use /rep to give rep to someone you enjoy chatting with")
                await partner_ch.send(embed=notify)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Reputation(bot))
