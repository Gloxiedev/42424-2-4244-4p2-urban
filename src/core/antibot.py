import discord
import random
import string
import time
from typing import Dict

_captcha_store: Dict[int, dict] = {}


def _gen_code() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=6))


def issue_captcha(discord_id: int) -> str:
    code = _gen_code()
    _captcha_store[discord_id] = {"code": code, "expires": time.time() + 300}
    return code


def verify_captcha(discord_id: int, submitted: str) -> bool:
    entry = _captcha_store.get(discord_id)
    if not entry:
        return False
    if time.time() > entry["expires"]:
        del _captcha_store[discord_id]
        return False
    if entry["code"].upper() == submitted.strip().upper():
        del _captcha_store[discord_id]
        return True
    return False


async def run_captcha(interaction: discord.Interaction) -> bool:
    code = issue_captcha(interaction.user.id)

    class CaptchaModal(discord.ui.Modal, title="🛡 Anti-Bot Verification"):
        answer = discord.ui.TextInput(label=f"Enter code: {code}", placeholder="Type the code exactly", min_length=4, max_length=8)

        def __init__(self):
            super().__init__()
            self.passed = False

        async def on_submit(self, i: discord.Interaction):
            if verify_captcha(i.user.id, self.answer.value):
                self.passed = True
                await i.response.send_message("✅ Verified! Run `/omegleconnect` again to connect.", ephemeral=True)
            else:
                await i.response.send_message("❌ Wrong code. Try `/omegleconnect` again.", ephemeral=True)

    modal = CaptchaModal()
    await interaction.response.send_modal(modal)
    await modal.wait()
    return modal.passed


def account_old_enough(user: discord.User, days: int = 7) -> bool:
    return (discord.utils.utcnow() - user.created_at).days >= days
