import io
import asyncio
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import aiohttp

# Cache for downloaded avatars
_avatar_cache = {}
# Cache for fonts
_font_cache = {}


@lru_cache(maxsize=128)
def get_cached_avatar(url: str) -> bytes:
    """Cache avatars in memory"""
    return _avatar_cache.get(url)


class ProfileCardGenerator:
    """Optimized profile card generator with caching and modern design"""
    
    # Pre-computed gradients and patterns
    _GRADIENT_CACHE = {}
    
    def __init__(self):
        self.W, self.H = 600, 400  # Larger canvas for more content
        self.avatar_size = 100
        self.corner_radius = 20
        
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Cached font loading"""
        cache_key = (size, bold)
        if cache_key in _font_cache:
            return _font_cache[cache_key]
        
        font_style = "Bold" if bold else "Regular"
        font_paths = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{font_style}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-{font_style}.ttf",
            "/nix/store/q4xaf00v5dl2j0bcfqhk3dybxqvs9vxl-noto-fonts-2024-01-01/share/fonts/noto/NotoSans-Bold.ttf",
        ]
        
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[cache_key] = font
                return font
            except:
                continue
        
        font = ImageFont.load_default()
        _font_cache[cache_key] = font
        return font
    
    def _create_gradient_background(self, width: int, height: int) -> Image.Image:
        """Create a beautiful gradient background with caching"""
        cache_key = (width, height)
        if cache_key in self._GRADIENT_CACHE:
            return self._GRADIENT_CACHE[cache_key].copy()
        
        # Dark gradient from #0a0a0a to #1a1a2e
        bg = Image.new("RGB", (width, height), (10, 10, 10))
        draw = ImageDraw.Draw(bg)
        
        for y in range(height):
            ratio = y / height
            r = int(10 + (20 * ratio))
            g = int(10 + (15 * ratio))
            b = int(10 + (30 * ratio))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        self._GRADIENT_CACHE[cache_key] = bg.copy()
        return bg
    
    def _round_corners(self, image: Image.Image, radius: int) -> Image.Image:
        """Apply rounded corners to an image"""
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, image.size[0], image.size[1]), radius, fill=255)
        result = Image.new("RGBA", image.size, (0, 0, 0, 0))
        result.paste(image, mask=mask)
        return result
    
    def _add_glow_effect(self, image: Image.Image, radius: int = 5) -> Image.Image:
        """Add a subtle glow effect"""
        glow = image.filter(ImageFilter.GaussianBlur(radius))
        return Image.blend(image, glow, 0.3)
    
    async def _fetch_avatar_async(self, url: str) -> Image.Image:
        """Async avatar fetching with caching"""
        if url in _avatar_cache:
            return _avatar_cache[url]
        
        try:
            timeout = aiohttp.ClientTimeout(total=3)  # Reduced timeout
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.read()
                        img = Image.open(io.BytesIO(data)).convert("RGBA")
                        _avatar_cache[url] = img
                        return img
        except:
            pass
        return None
    
    async def generate(
        self,
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
        level: int = 1,
        exp: int = 0,
        next_level_exp: int = 1000,
        join_date: str = None,
        bio: str = None,
    ) -> io.BytesIO:
        """Generate an enhanced profile card"""
        
        # Create base canvas
        bg = self._create_gradient_background(self.W, self.H)
        draw = ImageDraw.Draw(bg)
        
        # Add decorative elements
        # Top accent bar
        draw.rectangle([0, 0, self.W, 4], fill=(100, 150, 255))
        
        # Subtle grid pattern
        for x in range(0, self.W, 40):
            draw.line([(x, 0), (x, self.H)], fill=(30, 30, 40), width=1)
        for y in range(0, self.H, 40):
            draw.line([(0, y), (self.W, y)], fill=(30, 30, 40), width=1)
        
        # Main content area with rounded corners
        content_padding = 20
        content_rect = [
            content_padding, 
            content_padding, 
            self.W - content_padding, 
            self.H - content_padding
        ]
        draw.rounded_rectangle(
            content_rect, 
            radius=self.corner_radius, 
            outline=(60, 65, 80), 
            width=2,
            fill=(15, 15, 20, 200)
        )
        
        # Avatar section
        avatar_x, avatar_y = 40, 40
        
        if avatar_url:
            avatar_img = await self._fetch_avatar_async(avatar_url)
            if avatar_img:
                # Resize and create circular avatar
                avatar_img = avatar_img.resize((self.avatar_size, self.avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (self.avatar_size, self.avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=255)
                
                circular_avatar = Image.new("RGBA", (self.avatar_size, self.avatar_size), (0, 0, 0, 0))
                circular_avatar.paste(avatar_img, (0, 0), mask)
                
                # Add glow for premium users
                if premium:
                    circular_avatar = self._add_glow_effect(circular_avatar, 8)
                
                bg.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
                
                # Add ring around avatar
                ring_size = self.avatar_size + 8
                ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
                ring_draw = ImageDraw.Draw(ring)
                ring_color = (255, 215, 0) if premium else (100, 150, 255)
                ring_draw.ellipse((0, 0, ring_size, ring_size), outline=ring_color, width=3)
                bg.paste(ring, (avatar_x - 4, avatar_y - 4), ring)
        
        # User info section
        text_x = avatar_x + self.avatar_size + 25
        text_y = avatar_y + 10
        
        # Username with premium badge
        username_color = (255, 215, 0) if premium else (255, 255, 255)
        font_title = self._get_font(28, bold=True)
        display_name = f"{'👑 ' if premium else ''}{username}"
        draw.text((text_x, text_y), display_name, font=font_title, fill=username_color)
        
        # Level and rank
        font_info = self._get_font(14)
        level_text = f"Level {level}  •  Rank #{rank}"
        draw.text((text_x, text_y + 35), level_text, font=font_info, fill=(150, 155, 170))
        
        # Title/bio
        if title:
            font_title_small = self._get_font(13)
            draw.text((text_x, text_y + 55), f'"{title}"', font=font_title_small, fill=(180, 185, 200))
        
        # Experience bar
        exp_y = avatar_y + self.avatar_size + 15
        exp_width = self.W - 80
        exp_percentage = exp / next_level_exp
        
        # Experience bar background
        draw.rounded_rectangle(
            [40, exp_y, exp_width, exp_y + 12],
            radius=6,
            fill=(30, 35, 45)
        )
        # Experience bar fill
        draw.rounded_rectangle(
            [40, exp_y, 40 + (exp_width - 40) * exp_percentage, exp_y + 12],
            radius=6,
            fill=(100, 150, 255)
        )
        # Experience text
        exp_text = f"EXP: {exp:,} / {next_level_exp:,}"
        draw.text((40, exp_y + 16), exp_text, font=self._get_font(11), fill=(120, 125, 140))
        
        # Stats grid
        stats_y = exp_y + 45
        stats = [
            ("🪙", f"{coins:,}", "Coins", (40, stats_y)),
            ("⭐", f"{reputation:,}", "Reputation", (160, stats_y)),
            ("💬", f"{chat_count:,}", "Messages", (280, stats_y)),
            ("👥", f"{friends:,}", "Friends", (400, stats_y)),
            ("🔥", f"{daily_streak}", "Day Streak", (40, stats_y + 45)),
            ("🎯", f"{rank}", "Global Rank", (160, stats_y + 45)),
            ("📅", join_date or "N/A", "Joined", (280, stats_y + 45)),
        ]
        
        for icon, value, label, (x, y) in stats:
            # Stat card
            card_width = 100
            card_height = 50
            draw.rounded_rectangle(
                [x, y, x + card_width, y + card_height],
                radius=8,
                fill=(20, 22, 30),
                outline=(40, 45, 55),
                width=1
            )
            # Icon and value
            draw.text((x + 8, y + 8), icon, font=self._get_font(20), fill=(255, 255, 255))
            draw.text((x + 35, y + 8), str(value), font=self._get_font(16, bold=True), fill=(255, 255, 255))
            # Label
            draw.text((x + 35, y + 30), label, font=self._get_font(10), fill=(120, 125, 140))
        
        # Badges section
        badges_y = stats_y + 100
        if badges:
            draw.text((40, badges_y), "🏆 ACHIEVEMENTS", font=self._get_font(12, bold=True), fill=(150, 155, 170))
            
            badge_x = 40
            badge_y_offset = badges_y + 20
            
            for i, badge in enumerate(badges[:10]):  # Show up to 10 badges
                # Badge pill
                badge_text = f"🏅 {badge}"
                bbox = draw.textbbox((0, 0), badge_text, font=self._get_font(11))
                badge_width = bbox[2] - bbox[0] + 16
                
                if badge_x + badge_width > self.W - 40:
                    badge_x = 40
                    badge_y_offset += 25
                
                draw.rounded_rectangle(
                    [badge_x, badge_y_offset, badge_x + badge_width, badge_y_offset + 20],
                    radius=10,
                    fill=(30, 35, 50),
                    outline=(60, 65, 80),
                    width=1
                )
                draw.text((badge_x + 8, badge_y_offset + 4), badge_text, font=self._get_font(11), fill=(200, 205, 220))
                badge_x += badge_width + 8
        
        # Footer
        footer_y = self.H - 25
        draw.text((40, footer_y), "✨ Profile Card • Domegle", font=self._get_font(10), fill=(80, 85, 100))
        
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d")
        draw.text((self.W - 120, footer_y), f"Updated: {timestamp}", font=self._get_font(10), fill=(80, 85, 100))
        
        # Save to buffer
        buffer = io.BytesIO()
        bg.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        return buffer


# Optimized wrapper function for backward compatibility
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
    """Wrapper for the improved generator"""
    generator = ProfileCardGenerator()
    return await generator.generate(
        username=username,
        coins=coins,
        reputation=reputation,
        chat_count=chat_count,
        friends=friends,
        rank=rank,
        badges=badges,
        title=title,
        premium=premium,
        avatar_url=avatar_url,
        daily_streak=daily_streak,
        level=1,  # Default values for new params
        exp=0,
        next_level_exp=1000,
        join_date=None,
        bio=None
    )