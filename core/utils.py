import discord


def embed(title: str, description: str = None, color: int = 0x5865F2) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.set_footer(text="🌍 Domegle — Global Anonymous Chat")
    return e


def ok(title: str, description: str = None) -> discord.Embed:
    return embed(title, description, 0x2ECC71)


def err(title: str, description: str = None) -> discord.Embed:
    return embed(title, description, 0xE74C3C)


def info(title: str, description: str = None) -> discord.Embed:
    return embed(title, description, 0x3498DB)


def is_dm(interaction: discord.Interaction) -> bool:
    return interaction.guild_id is None


async def require_user(interaction: discord.Interaction) -> bool:
    db = getattr(interaction.client, "db", None)
    if db is None:
        await interaction.response.send_message(
            embed=err("Unavailable", "Bot is still starting up. Try again in a moment."),
            ephemeral=True
        )
        return False
    user = await db.get_user(interaction.user.id)
    if not user:
        await interaction.response.send_message(
            embed=err("Not Registered", "Run `/start` first to use Domegle!"),
            ephemeral=True
        )
        return False
    if user["banned"]:
        await interaction.response.send_message(
            embed=err("Banned", f"You are banned from Domegle.\nReason: {user['ban_reason'] or 'No reason provided.'}"),
            ephemeral=True
        )
        return False
    return True


async def require_chat_context(interaction: discord.Interaction) -> bool:
    """
    Passes if:
    - User is in a DM (DMs are always a valid Domegle context)
    - OR user is in the configured server Domegle channel
    """
    if is_dm(interaction):
        return True

    db = getattr(interaction.client, "db", None)
    if db is None:
        await interaction.response.send_message(
            embed=err("Unavailable", "Bot is still starting up."),
            ephemeral=True
        )
        return False

    server = await db.get_server(interaction.guild_id)
    if not server or not server["text_channel_id"]:
        await interaction.response.send_message(
            embed=err("Not Set Up", "An admin needs to run `/setdomeglechat` first."),
            ephemeral=True
        )
        return False
    if interaction.channel_id != server["text_channel_id"]:
        ch = interaction.guild.get_channel(server["text_channel_id"]) if interaction.guild else None
        await interaction.response.send_message(
            embed=err("Wrong Channel", f"Use Domegle commands in {ch.mention if ch else '#domegle'}"),
            ephemeral=True
        )
        return False
    return True


async def get_session_channel_id(interaction: discord.Interaction) -> int:
    """Returns the channel ID to use for this user's session."""
    if is_dm(interaction):
        dm = await interaction.user.create_dm()
        return dm.id
    return interaction.channel_id


async def get_session_guild_id(interaction: discord.Interaction) -> int:
    """Returns 0 for DM sessions (no guild)."""
    return interaction.guild_id or 0


async def db_check(interaction: discord.Interaction) -> bool:
    if getattr(interaction.client, "db", None) is None:
        await interaction.response.send_message(
            embed=err("Startup Error", "Run `./start.sh` instead of `python3 bot.py`\nThe wrong discord.py version is loaded."),
            ephemeral=True
        )
        return False
    return True
