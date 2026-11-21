"""
presence_bot.py — Bot Raphael bản tối giản chuyên dụng cho GunLol Discord Sync.
- Giữ kết nối Gateway tới server Discord (đọc Online/Idle/DND/Spotify/Game/Clan Tag).
- Cung cấp slash commands gọn nhẹ (/bio, /syncstatus).
- Mở kèm API nhỏ (/presence/{user_id}, /members, /health) để web đọc trạng thái trực tiếp nếu host tách rời.
"""
import asyncio
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "bot"))

intents = discord.Intents.default()
intents.members = True
intents.presences = True


def serialize_member(member: discord.Member) -> dict:
    avatar_url = ""
    if member.display_avatar:
        avatar_url = member.display_avatar.url

    activity_text = ""
    activity_sub = ""
    is_spotify = False
    album_art = ""

    for act in member.activities or []:
        if isinstance(act, discord.Spotify):
            is_spotify = True
            activity_text = act.title or "Spotify"
            activity_sub = f"by {', '.join(act.artists)}" if act.artists else ""
            album_art = act.album_cover_url or ""
            break

    if not is_spotify:
        custom_act = next((a for a in (member.activities or []) if isinstance(a, discord.CustomActivity)), None)
        game_act = next((a for a in (member.activities or []) if not isinstance(a, discord.CustomActivity)), None)
        if custom_act and custom_act.name:
            activity_text = custom_act.name
            if game_act and getattr(game_act, "name", None):
                activity_sub = f"Playing {game_act.name}"
        elif game_act and getattr(game_act, "name", None):
            activity_text = game_act.name
            activity_sub = getattr(game_act, "details", None) or getattr(game_act, "state", None) or ""

    return {
        "id": str(member.id),
        "username": member.name,
        "globalName": member.global_name or member.name,
        "avatarUrl": avatar_url,
        "badges": [],
        "status": str(member.status),
        "activityText": activity_text,
        "activitySub": activity_sub,
        "isSpotify": is_spotify,
        "albumArt": album_art,
    }


class RaphaelPresenceBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.http_runner = None

    async def setup_hook(self):
        await self.load_extension("cogs.gunlol_sync")
        guild_id = os.getenv("DEV_GUILD_ID", "").strip()
        if guild_id.isdigit():
            guild_obj = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)

        await self.start_http_bridge()

    async def start_http_bridge(self):
        port_raw = os.getenv("PORT") or os.getenv("PRESENCE_BRIDGE_PORT") or "4001"
        try:
            port = int(port_raw)
        except ValueError:
            port = 4001

        app = web.Application()

        async def handle_health(_request):
            return web.json_response({
                "ok": True,
                "botReady": self.is_ready(),
                "guilds": len(self.guilds),
            })

        async def handle_presence(request):
            uid = request.match_info.get("user_id", "").strip()
            if not uid.isdigit():
                return web.json_response({"botActive": self.is_ready(), "data": None}, status=400)
            target_id = int(uid)
            for guild in self.guilds:
                member = guild.get_member(target_id)
                if member:
                    return web.json_response({"botActive": True, "health": "ready", "data": serialize_member(member)})
            return web.json_response({"botActive": self.is_ready(), "health": "ready", "data": None})

        async def handle_members(request):
            q = (request.query.get("q") or "").strip().lower()
            items = []
            guild_name = ""
            for guild in self.guilds:
                guild_name = guild.name
                for m in guild.members:
                    if m.bot:
                        continue
                    if q and q not in m.name.lower() and q not in (m.global_name or "").lower() and q not in str(m.id):
                        continue
                    items.append(serialize_member(m))
                break
            return web.json_response({"botActive": self.is_ready(), "guildName": guild_name, "members": items[:30]})

        app.router.add_get("/health", handle_health)
        app.router.add_get("/presence/{user_id}", handle_presence)
        app.router.add_get("/members", handle_members)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        self.http_runner = runner
        print(f"[Raphael Bridge] HTTP Presence API listening on port {port}", flush=True)

    async def close(self):
        if self.http_runner:
            await self.http_runner.cleanup()
        await super().close()

    async def on_ready(self):
        print(f"[Raphael Bio Sync] Online: {self.user} ({len(self.guilds)} server)", flush=True)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Bio Presence Sync",
            )
        )


async def main():
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        print("[Raphael] Thieu DISCORD_TOKEN trong .env")
        return
    bot = RaphaelPresenceBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
