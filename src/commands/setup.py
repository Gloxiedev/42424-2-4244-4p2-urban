import discord
from discord import app_commands
from discord.ext import commands
from src.core.utils import ok, err, embed, db_check


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message(embed=err("Server Only", "Use this in a server."), ephemeral=True)
            return False
        p = interaction.user.guild_permissions
        if not (p.manage_guild or p.administrator):
            await interaction.response.send_message(embed=err("No Permission", "Requires **Manage Server**."), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setdomeglechat", description="[Admin] Set the Domegle text channel")
    @app_commands.describe(channel="Text channel for Domegle")
    @is_admin()
    async def set_chat(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await db_check(interaction):
            return
        p = channel.permissions_for(interaction.guild.me)
        if not p.send_messages or not p.embed_links:
            await interaction.response.send_message(embed=err("Missing Perms", f"I need Send Messages + Embed Links in {channel.mention}."), ephemeral=True)
            return
        await self.bot.db.upsert_server(interaction.guild_id, text_channel_id=channel.id, setup_by=interaction.user.id)
        await interaction.response.send_message(embed=ok("✅ Channel Set", f"Domegle will operate in {channel.mention}."), ephemeral=True)
        welcome = discord.Embed(
            title="🌍 Domegle is ready!",
            description="**Getting started:**\n1. `/start` — Register\n2. `/username <n>` — Create your identity\n3. `/omegleconnect` — Find a stranger!\n\nUse `/help` for all commands.",
            color=0x5865F2
        )
        welcome.set_footer(text="🌍 Domegle — Your identity stays anonymous")
        await channel.send(embed=welcome)

    @app_commands.command(name="setdomeglevoice", description="[Admin] Set the voice waiting channel")
    @app_commands.describe(channel="Voice channel users join before matching")
    @is_admin()
    async def set_voice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        if not await db_check(interaction):
            return
        p = channel.permissions_for(interaction.guild.me)
        if not p.move_members or not p.manage_channels:
            await interaction.response.send_message(embed=err("Missing Perms", f"I need Move Members + Manage Channels in {channel.mention}."), ephemeral=True)
            return
        await self.bot.db.upsert_server(interaction.guild_id, voice_channel_id=channel.id)
        await interaction.response.send_message(embed=ok("✅ Voice Set", f"Users join {channel.mention} before voice matching."), ephemeral=True)

    @app_commands.command(name="domeglesetup", description="[Admin] View current configuration")
    @is_admin()
    async def view_setup(self, interaction: discord.Interaction):
        if not await db_check(interaction):
            return
        server = await self.bot.db.get_server(interaction.guild_id)
        if not server:
            await interaction.response.send_message(embed=embed("⚙️ Not Configured", "Run `/setdomeglechat #channel` to start."), ephemeral=True)
            return
        tc = f"<#{server['text_channel_id']}>" if server["text_channel_id"] else "Not set"
        vc = f"<#{server['voice_channel_id']}>" if server["voice_channel_id"] else "Not set"
        await interaction.response.send_message(embed=embed("⚙️ Config", f"**Text:** {tc}\n**Voice:** {vc}"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Setup(bot))
