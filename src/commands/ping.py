import discord
from discord import app_commands
from discord.ext import commands
import time


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive and view latency")
    async def ping(self, interaction: discord.Interaction):
        ws_latency = round(self.bot.latency * 1000)

        start = time.perf_counter()
        await interaction.response.defer(ephemeral=True)
        end = time.perf_counter()
        api_latency = round((end - start) * 1000)

        if ws_latency < 100:
            color, status = 0x2ECC71, "🟢 Excellent"
        elif ws_latency < 200:
            color, status = 0xF39C12, "🟡 Good"
        else:
            color, status = 0xE74C3C, "🔴 Poor"

        mm = self.bot.matchmaking
        qs = mm.get_queue_sizes() if mm else {"text": 0, "voice": 0, "active_sessions": 0}

        e = discord.Embed(title="🏓 Pong!", color=color)
        e.add_field(name="📡 WebSocket", value=f"`{ws_latency}ms`", inline=True)
        e.add_field(name="⚡ API", value=f"`{api_latency}ms`", inline=True)
        e.add_field(name="📶 Status", value=status, inline=True)
        e.add_field(name="💬 Active Sessions", value=str(qs["active_sessions"]), inline=True)
        e.add_field(name="🔍 In Queue", value=str(qs["text"] + qs["voice"]), inline=True)
        e.set_footer(text="🌍 Domegle is online")
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ping(bot))
