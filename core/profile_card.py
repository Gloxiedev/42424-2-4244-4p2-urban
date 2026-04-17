import io
import asyncio
from PIL import Image, ImageDraw, ImageFont
import aiohttp


async def fetch_avatar(url: str) -> Image.Image:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                data = await r.read()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result


def try_font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/nix/store/q4xaf00v5dl2j0bcfqhk3dybxqvs9vxl-noto-fonts-2024-01-01/share/fonts/noto/NotoSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


async def generate_profile_card(
    username: str,
    coins: int,
    reputation: int,
    chat_count: int,
    friends: int,
    rank: int,
    badges: list,
    title: str,
    premium: bool,
    avatar_url: str = None,
    daily_streak: int = 0,
) -> io.BytesIO:
    W, H = 520, 300
    bg = Image.new("RGB", (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(bg)

    for i in range(H):
        alpha = int(20 + (i / H) * 15)
        draw.line([(0, i), (W, i)], fill=(alpha, alpha, alpha))

    draw.rectangle([0, 0, W - 1, H - 1], outline=(60, 60, 60), width=2)
    draw.rectangle([0, 0, W - 1, 3], fill=(255, 255, 255))

    font_xl = try_font(26)
    font_lg = try_font(18)
    font_md = try_font(14)
    font_sm = try_font(12)

    AV = 88
    ax, ay = 24, 24

    if avatar_url:
        avatar_img = await fetch_avatar(avatar_url)
        if avatar_img:
            circ = circle_avatar(avatar_img, AV)
            bg.paste(circ, (ax, ay), circ)
            ring = Image.new("RGBA", (AV + 6, AV + 6), (0, 0, 0, 0))
            ring_d = ImageDraw.Draw(ring)
            ring_d.ellipse((0, 0, AV + 5, AV + 5), outline=(255, 255, 255, 180), width=2)
            bg.paste(ring, (ax - 3, ay - 3), ring)

    tx = ax + AV + 16
    ty = ay

    name_color = (255, 215, 0) if premium else (255, 255, 255)
    display = ("💎 " if premium else "") + username
    draw.text((tx, ty), display, font=font_xl, fill=name_color)
    ty += 32

    if title:
        draw.text((tx, ty), f'"{title}"', font=font_sm, fill=(180, 180, 180))
        ty += 20

    ty += 4
    draw.line([(tx, ty), (W - 20, ty)], fill=(50, 50, 50), width=1)
    ty += 10

    draw.text((tx, ty), f"🏅 Rank #{rank}", font=font_md, fill=(200, 200, 200))

    row1_y = ay + AV + 20
    stats = [
        ("💰", f"{coins:,} coins", 24),
        ("⭐", f"{reputation} rep", 160),
        ("💬", f"{chat_count} chats", 296),
        ("👥", f"{friends} friends", 24),
        ("🔥", f"{daily_streak} streak", 160),
    ]
    for icon, val, x in stats:
        draw.rectangle([x, row1_y, x + 130, row1_y + 40], fill=(20, 20, 20), outline=(50, 50, 50), width=1)
        draw.text((x + 8, row1_y + 5), icon, font=font_md, fill=(255, 255, 255))
        draw.text((x + 30, row1_y + 4), val, font=font_sm, fill=(200, 200, 200))

    badge_y = row1_y + 56
    draw.text((24, badge_y), "Badges:", font=font_sm, fill=(120, 120, 120))
    bx = 90
    for b in badges[:8]:
        draw.text((bx, badge_y), b, font=font_sm, fill=(255, 255, 255))
        bx += len(b) * 8 + 6

    draw.text((W - 120, H - 20), "🌍 Domegle", font=font_sm, fill=(60, 60, 60))

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf
