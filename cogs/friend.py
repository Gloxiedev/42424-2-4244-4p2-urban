import discord
from discord import app_commands
from discord.ext import commands
from core.utils import require_user, embed, ok, err, info
from core.matchmaking import QueueEntry, ChatType


async def _fetch_user(bot, user_id: int) -> discord.User | None:
    user = bot.get_user(user_id)
    if user:
        return user
    try:
        return await bot.fetch_user(user_id)
    except Exception:
        return None


class FriendRequestView(discord.ui.View):
    def __init__(self, bot, requester_id: int, target_id: int, requester_name: str):
        super().__init__(timeout=86400)
        self.bot = bot
        self.requester_id = requester_id
        self.target_id = target_id
        self.requester_name = requester_name

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.stop()
        await self.bot.db.accept_friend_request(self.target_id, self.requester_id)
        me = await self.bot.db.get_user(self.target_id)
        requester_discord = await _fetch_user(self.bot, self.requester_id)
        if requester_discord:
            try:
                await requester_discord.send(embed=ok("✅ Friend Accepted", f"**{me['username']}** accepted your friend request!"))
            except discord.Forbidden:
                pass
        await interaction.response.edit_message(
            embed=ok("✅ Friends!", f"You and **{self.requester_name}** are now friends!\nUse `/friend_list` to see all your friends."),
            view=None
        )

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(embed=embed("❌ Declined", "Friend request declined."), view=None)

    async def on_timeout(self):
        self.stop()


class Friend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="friend_add", description="Send a friend request to someone you chatted with")
    @app_commands.describe(username="Their Domegle username")
    async def friend_add(self, interaction: discord.Interaction, username: str):
        if not await require_user(interaction):
            return

        me = await self.bot.db.get_user(interaction.user.id)
        target = await self.bot.db.get_user_by_username(username)

        if not target:
            await interaction.response.send_message(embed=err("Not Found", f"No user named **{username}** exists."), ephemeral=True)
            return
        if target["discord_id"] == interaction.user.id:
            await interaction.response.send_message(embed=err("Nice Try", "You can't add yourself."), ephemeral=True)
            return
        if await self.bot.db.are_friends(interaction.user.id, target["discord_id"]):
            await interaction.response.send_message(embed=err("Already Friends", f"You're already friends with **{username}**."), ephemeral=True)
            return

        result = await self.bot.db.send_friend_request(interaction.user.id, target["discord_id"])
        if result == "exists":
            await interaction.response.send_message(embed=info("Already Sent", f"You already have a pending request to **{username}**."), ephemeral=True)
            return

        display = ("💎 " if me["premium"] else "") + me["username"]
        view = FriendRequestView(self.bot, interaction.user.id, target["discord_id"], me["username"])
        req_embed = discord.Embed(
            title="📨 Friend Request",
            description=(
                f"**{display}** wants to add you as a friend on Domegle!\n\n"
                f"Accept or decline below.\nYou can also use `/friend_accept {me['username']}`."
            ),
            color=0x5865F2
        )
        req_embed.set_footer(text="🌍 Domegle")

        target_discord = await _fetch_user(self.bot, target["discord_id"])
        dm_sent = False
        if target_discord:
            try:
                await target_discord.send(embed=req_embed, view=view)
                dm_sent = True
            except discord.Forbidden:
                pass

        if dm_sent:
            await interaction.response.send_message(
                embed=ok("📨 Request Sent", f"Friend request sent to **{username}**!\nThey'll receive a DM to accept or decline."),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=info("📨 Request Sent", f"Friend request sent to **{username}**.\nThey have DMs closed — they can accept with `/friend_accept {me['username']}`."),
                ephemeral=True
            )

    @app_commands.command(name="friend_accept", description="Accept a pending friend request")
    @app_commands.describe(username="The username who sent you a request")
    async def friend_accept(self, interaction: discord.Interaction, username: str):
        if not await require_user(interaction):
            return

        requester = await self.bot.db.get_user_by_username(username)
        if not requester:
            await interaction.response.send_message(embed=err("Not Found", f"No user named **{username}**."), ephemeral=True)
            return

        pending = await self.bot.db.get_pending_requests(interaction.user.id)
        pending_ids = [p["discord_id"] for p in pending]

        if requester["discord_id"] not in pending_ids:
            await interaction.response.send_message(
                embed=err("No Request", f"No pending friend request from **{username}**.\nCheck `/friend_list` for pending requests."),
                ephemeral=True
            )
            return

        await self.bot.db.accept_friend_request(interaction.user.id, requester["discord_id"])
        me = await self.bot.db.get_user(interaction.user.id)

        requester_discord = await _fetch_user(self.bot, requester["discord_id"])
        if requester_discord:
            try:
                await requester_discord.send(embed=ok("✅ Friend Accepted", f"**{me['username']}** accepted your friend request! You're now friends."))
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            embed=ok("✅ Friends!", f"You and **{username}** are now friends!\nUse `/friend_list` to see all your friends."),
            ephemeral=True
        )

    @app_commands.command(name="friend_remove", description="Remove someone from your friends list")
    @app_commands.describe(username="Their Domegle username")
    async def friend_remove(self, interaction: discord.Interaction, username: str):
        if not await require_user(interaction):
            return

        target = await self.bot.db.get_user_by_username(username)
        if not target:
            await interaction.response.send_message(embed=err("Not Found", f"No user named **{username}**."), ephemeral=True)
            return
        if not await self.bot.db.are_friends(interaction.user.id, target["discord_id"]):
            await interaction.response.send_message(embed=err("Not Friends", f"You're not friends with **{username}**."), ephemeral=True)
            return

        await self.bot.db.remove_friend(interaction.user.id, target["discord_id"])
        await interaction.response.send_message(embed=ok("✅ Removed", f"**{username}** has been removed from your friends."), ephemeral=True)

    @app_commands.command(name="friend_list", description="View your friends list and pending requests")
    async def friend_list(self, interaction: discord.Interaction):
        if not await require_user(interaction):
            return

        friends = await self.bot.db.get_friends(interaction.user.id)
        pending_sent = await self.bot.db.get_pending_sent(interaction.user.id)
        pending_received = await self.bot.db.get_pending_requests(interaction.user.id)

        if not friends and not pending_sent and not pending_received:
            await interaction.response.send_message(
                embed=info("👥 Friends", "You have no friends yet!\nChat with someone and use `/friend_add <username>` to add them."),
                ephemeral=True
            )
            return

        desc = ""
        if friends:
            desc += f"**Friends ({len(friends)})**\n"
            desc += "\n".join(f"• {'💎 ' if f['premium'] else ''}{f['username']}" for f in friends)
            desc += "\n\n"

        if pending_received:
            desc += f"**Incoming Requests ({len(pending_received)})**\n"
            desc += "\n".join(f"• {p['username']} — `/friend_accept {p['username']}`" for p in pending_received)
            desc += "\n\n"

        if pending_sent:
            desc += f"**Sent Requests ({len(pending_sent)})**\n"
            desc += "\n".join(f"• {p['username']} — waiting..." for p in pending_sent)

        await interaction.response.send_message(embed=embed("👥 Your Friends", desc.strip()), ephemeral=True)

    @app_commands.command(name="friend_chat", description="Start a private chat with a friend")
    @app_commands.describe(username="Their Domegle username")
    async def friend_chat(self, interaction: discord.Interaction, username: str):
        if not await require_user(interaction):
            return

        target = await self.bot.db.get_user_by_username(username)
        if not target:
            await interaction.response.send_message(embed=err("Not Found", f"No user named **{username}**."), ephemeral=True)
            return
        if not await self.bot.db.are_friends(interaction.user.id, target["discord_id"]):
            await interaction.response.send_message(embed=err("Not Friends", f"You need to be friends with **{username}** first."), ephemeral=True)
            return

        mm = self.bot.matchmaking
        if await mm.get_session(interaction.user.id):
            await interaction.response.send_message(embed=err("Already in Chat", "Use `/stop` to leave your current chat first."), ephemeral=True)
            return

        me = await self.bot.db.get_user(interaction.user.id)
        target_discord = await _fetch_user(self.bot, target["discord_id"])

        if not target_discord:
            await interaction.response.send_message(embed=err("Unavailable", "Could not find that user. They may have left Discord."), ephemeral=True)
            return

        bot_ref = self.bot
        me_ref = me
        target_ref = target
        req_channel = interaction.channel_id
        req_guild = interaction.guild_id

        class AcceptView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
            async def accept_btn(self, i: discord.Interaction, btn: discord.ui.Button):
                self.stop()
                await i.response.defer()
                server = await bot_ref.db.get_server(i.guild_id) if i.guild_id else None
                ch_id = server["text_channel_id"] if server and server["text_channel_id"] else req_channel
                ea = QueueEntry(
                    discord_id=me_ref["discord_id"], guild_id=req_guild,
                    channel_id=req_channel, chat_type=ChatType.FRIEND,
                    premium=me_ref["premium"], interests=[]
                )
                eb = QueueEntry(
                    discord_id=i.user.id, guild_id=i.guild_id or req_guild,
                    channel_id=ch_id, chat_type=ChatType.FRIEND,
                    premium=target_ref["premium"], interests=[]
                )
                await bot_ref.matchmaking.create_session(ea, eb)
                await i.followup.send(
                    embed=ok("💬 Chat Started!", f"You're now chatting with **{me_ref['username']}**!\nType messages in your Domegle channel."),
                    ephemeral=True
                )

            @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
            async def decline_btn(self, i: discord.Interaction, btn: discord.ui.Button):
                self.stop()
                await i.response.send_message("Chat request declined.", ephemeral=True)

            async def on_timeout(self):
                self.stop()

        try:
            await target_discord.send(
                embed=embed("💬 Chat Request", f"Your friend **{me['username']}** wants to start a private Domegle chat with you!"),
                view=AcceptView()
            )
            await interaction.response.send_message(
                embed=info("📨 Request Sent", f"Chat invite sent to **{username}**. Waiting for them to accept."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=err("DMs Closed", f"**{username}** has their DMs closed and can't receive the request."),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Friend(bot))
