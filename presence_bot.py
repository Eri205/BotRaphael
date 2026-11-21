"""
presence_bot.py — Bot Raphael chuyên dụng cho Cú Profile (cuprofile.id.vn):
- Giữ kết nối Gateway tới server Discord (đọc Online/Idle/DND/Spotify/Game/Clan Tag).
- Cung cấp slash commands gọn nhẹ (/bio, /syncstatus).
- Tích hợp sẵn Web Dashboard Quản lý Bot tại `/` (xem trạng thái, đổi status bot,
  gửi DM thử, sync slash commands, xem thành viên Live) và API tại /health, /presence/{id}, /members.
"""
import asyncio
import html
import hmac
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

DASHBOARD_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Raphael Bot Manager — Cú Profile</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; font-family: Inter, system-ui, -apple-system, sans-serif; }
    body { margin: 0; background: #07070c; color: #f4f4f5; min-height: 100vh; padding: 24px; }
    .wrap { max-width: 1040px; margin: 0 auto; display: grid; gap: 18px; }
    .card { background: #0e0e17; border: 1px solid rgba(255,255,255,.1); border-radius: 20px; padding: 20px; }
    .row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
    .grid4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 14px; }
    .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .stat { background: rgba(0,0,0,.4); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 12px 14px; }
    .stat small { color: #a1a1aa; font-size: 11px; display: block; }
    .stat strong { font-size: 22px; margin-top: 4px; display: block; }
    .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .ok { background: rgba(16,185,129,.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,.35); }
    .warn { background: rgba(245,158,11,.15); color: #fcd34d; border: 1px solid rgba(245,158,11,.35); }
    input, select, textarea { width: 100%; background: rgba(0,0,0,.5); color: #fff; border: 1px solid rgba(255,255,255,.12); border-radius: 12px; padding: 10px 12px; font-size: 13px; }
    label { display: block; font-size: 11px; color: #a1a1aa; margin: 10px 0 5px; }
    button { background: #5865F2; color: #fff; border: 0; border-radius: 12px; padding: 10px 16px; font-size: 13px; font-weight: 700; cursor: pointer; }
    button:hover { background: #4752C4; }
    button.sec { background: rgba(255,255,255,.08); }
    button.sec:hover { background: rgba(255,255,255,.14); }
    .list { max-height: 290px; overflow-y: auto; display: grid; gap: 8px; margin-top: 10px; }
    .member { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 10px; border-radius: 12px; background: rgba(0,0,0,.35); border: 1px solid rgba(255,255,255,.06); font-size: 12px; }
    .member img { width: 32px; height: 32px; border-radius: 999px; object-fit: cover; }
    .dot { width: 8px; height: 8px; border-radius: 999px; display: inline-block; }
    .online { background: #34d399; } .idle { background: #fbbf24; } .dnd { background: #f43f5e; } .offline { background: #71717a; }
    .toast { padding: 10px 14px; border-radius: 12px; font-size: 12px; display: none; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div id="authBox" class="card" style="max-width:420px;margin:60px auto;display:none">
      <h2 style="margin:0 0 6px">🦉 Raphael Bot Manager</h2>
      <p style="margin:0 0 14px;font-size:12px;color:#a1a1aa">Nhập mật khẩu quản trị Bot để truy cập bảng điều khiển.</p>
      <input id="pwInput" type="password" placeholder="Mật khẩu quản trị..." />
      <button style="width:100%;margin-top:12px" onclick="login()">Đăng nhập</button>
      <div id="authErr" class="toast warn"></div>
    </div>

    <div id="dashBox" style="display:none;gap:18px" class="wrap">
      <div class="card">
        <div class="row">
          <div style="display:flex;align-items:center;gap:12px">
            <img id="botAvatar" src="" alt="" style="width:48px;height:48px;border-radius:14px;background:#18181b;object-fit:cover" />
            <div>
              <div style="display:flex;align-items:center;gap:8px">
                <strong id="botName" style="font-size:17px">Bot Raphael</strong>
                <span id="botBadge" class="badge ok">Ready</span>
              </div>
              <div id="botMeta" style="font-size:12px;color:#a1a1aa;margin-top:3px">Đang tải...</div>
            </div>
          </div>
          <div class="row">
            <button class="sec" onclick="loadState()">Làm mới</button>
            <button onclick="syncCommands()">Sync Slash Commands</button>
          </div>
        </div>
        <div class="grid4">
          <div class="stat"><small>Tổng thành viên</small><strong id="cTotal">0</strong></div>
          <div class="stat"><small>Online</small><strong id="cOnline" style="color:#34d399">0</strong></div>
          <div class="stat"><small>Idle / Chờ</small><strong id="cIdle" style="color:#fbbf24">0</strong></div>
          <div class="stat"><small>Ping Gateway</small><strong id="cPing">0 ms</strong></div>
        </div>
        <div id="toast" class="toast ok"></div>
      </div>

      <div class="grid2">
        <div class="card">
          <h3 style="margin:0 0 8px;font-size:15px">Trạng thái & Test gửi DM</h3>
          <label>Trạng thái hiển thị Bot</label>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <select id="stType">
              <option value="watching">Watching</option>
              <option value="playing">Playing</option>
              <option value="listening">Listening</option>
            </select>
            <select id="stOnline">
              <option value="online">Online</option>
              <option value="idle">Idle</option>
              <option value="dnd">DND</option>
            </select>
          </div>
          <label>Nội dung Activity của Bot</label>
          <div style="display:flex;gap:8px">
            <input id="stText" value="Bio Presence Sync" />
            <button onclick="updateStatus()">Lưu</button>
          </div>

          <hr style="border:0;border-top:1px solid rgba(255,255,255,.08);margin:16px 0" />
          <label>Gửi DM thử tới Discord User ID</label>
          <input id="dmId" placeholder="1155773960215072768" />
          <label>Nội dung tin nhắn</label>
          <textarea id="dmMsg" rows="2">🦉 Tin nhắn kiểm tra từ Bot Raphael!</textarea>
          <button style="width:100%;margin-top:10px" onclick="sendDm()">Gửi DM qua Bot</button>
        </div>

        <div class="card">
          <div class="row">
            <h3 style="margin:0;font-size:15px">Thành viên Server Live</h3>
            <input id="qInput" placeholder="Tìm tên hoặc ID..." style="width:180px;padding:7px 10px" oninput="renderMembers()" />
          </div>
          <div id="memberList" class="list"></div>
        </div>
      </div>
    </div>
  </div>
<script>
let members = [];
let token = localStorage.getItem("bot_admin_pw") || "";
function showToast(msg, ok=true){
  const t = document.getElementById("toast");
  t.className = "toast " + (ok ? "ok" : "warn");
  t.textContent = msg;
  t.style.display = "block";
}
async function api(path, opts={}){
  opts.headers = Object.assign({"Content-Type":"application/json","x-bot-admin":token}, opts.headers||{});
  const r = await fetch(path, opts);
  return { ok: r.ok, status: r.status, data: await r.json().catch(()=>({})) };
}
async function login(){
  token = document.getElementById("pwInput").value;
  localStorage.setItem("bot_admin_pw", token);
  await loadState();
}
async function loadState(){
  const r = await api("/api/bot/status");
  if(r.status === 401){
    document.getElementById("authBox").style.display = "block";
    document.getElementById("dashBox").style.display = "none";
    if(token){ const e = document.getElementById("authErr"); e.textContent="Sai mật khẩu"; e.style.display="block"; }
    return;
  }
  document.getElementById("authBox").style.display = "none";
  document.getElementById("dashBox").style.display = "grid";
  const d = r.data;
  document.getElementById("botName").textContent = d.botName || "Bot Raphael";
  if(d.botAvatar) document.getElementById("botAvatar").src = d.botAvatar;
  document.getElementById("botBadge").textContent = d.ready ? "Online (Ready)" : "Connecting";
  document.getElementById("botMeta").textContent = `Server: ${d.guildName || "Chưa có"} • Bot ID: ${d.botId || "-"}`;
  document.getElementById("cTotal").textContent = d.counts?.total ?? 0;
  document.getElementById("cOnline").textContent = d.counts?.online ?? 0;
  document.getElementById("cIdle").textContent = d.counts?.idle ?? 0;
  document.getElementById("cPing").textContent = `${d.latencyMs ?? 0} ms`;
  members = d.members || [];
  renderMembers();
}
function renderMembers(){
  const q = (document.getElementById("qInput").value || "").toLowerCase();
  const box = document.getElementById("memberList");
  const filtered = members.filter(m => !q || m.globalName.toLowerCase().includes(q) || m.username.toLowerCase().includes(q) || m.id.includes(q));
  box.innerHTML = filtered.map(m => `
    <div class="member">
      <div style="display:flex;align-items:center;gap:8px;min-width:0">
        <img src="${m.avatarUrl || ''}" alt="" />
        <div style="min-width:0">
          <div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            <span class="dot ${m.status}"></span> ${m.globalName} <span style="color:#71717a;font-weight:400">@${m.username}</span>
          </div>
          <div style="color:#a1a1aa;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${m.activityText || m.id}</div>
        </div>
      </div>
      <button class="sec" style="padding:5px 9px;font-size:11px" onclick="document.getElementById('dmId').value='${m.id}'">Chọn DM</button>
    </div>`).join("") || "<div style='color:#71717a;font-size:12px'>Chưa có thành viên.</div>";
}
async function updateStatus(){
  const r = await api("/api/bot/status", { method:"POST", body: JSON.stringify({
    type: document.getElementById("stType").value,
    status: document.getElementById("stOnline").value,
    text: document.getElementById("stText").value
  })});
  showToast(r.ok ? "Đã cập nhật trạng thái Bot!" : (r.data.error || "Lỗi"), r.ok);
}
async function sendDm(){
  const r = await api("/api/bot/dm", { method:"POST", body: JSON.stringify({
    userId: document.getElementById("dmId").value,
    message: document.getElementById("dmMsg").value
  })});
  showToast(r.ok ? "Đã gửi DM thành công!" : (r.data.error || "Không gửi được DM"), r.ok);
}
async function syncCommands(){
  const r = await api("/api/bot/sync", { method:"POST" });
  showToast(r.ok ? "Đã đồng bộ Slash Commands!" : (r.data.error || "Lỗi sync"), r.ok);
}
loadState();
</script>
</body>
</html>"""


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
        guild_id = (os.getenv("DEV_GUILD_ID") or os.getenv("DISCORD_GUILD_ID") or "").strip()
        if guild_id.isdigit():
            guild_obj = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)

        await self.start_http_bridge()

    def _is_admin(self, request: web.Request) -> bool:
        expected = (os.getenv("BOT_ADMIN_PASSWORD") or "Matkhau37@").strip()
        provided = (request.headers.get("x-bot-admin") or "").strip()
        return bool(expected) and hmac.compare_digest(provided, expected)

    async def start_http_bridge(self):
        port_raw = os.getenv("PORT") or os.getenv("PRESENCE_BRIDGE_PORT") or "4001"
        try:
            port = int(port_raw)
        except ValueError:
            port = 4001

        app = web.Application()

        async def handle_dashboard(_request):
            return web.Response(text=DASHBOARD_HTML, content_type="text/html")

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

        async def handle_bot_status(request):
            if not self._is_admin(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            all_members = []
            guild_name = ""
            for guild in self.guilds:
                guild_name = guild.name
                for m in guild.members:
                    if not m.bot:
                        all_members.append(serialize_member(m))
                break
            return web.json_response({
                "ready": self.is_ready(),
                "botId": str(self.user.id) if self.user else "",
                "botName": str(self.user.display_name) if self.user else "Bot Raphael",
                "botAvatar": self.user.display_avatar.url if self.user and self.user.display_avatar else "",
                "guildName": guild_name,
                "latencyMs": round(self.latency * 1000) if self.latency else 0,
                "counts": {
                    "total": len(all_members),
                    "online": sum(1 for m in all_members if m["status"] == "online"),
                    "idle": sum(1 for m in all_members if m["status"] == "idle"),
                },
                "members": all_members[:50],
            })

        async def handle_update_status(request):
            if not self._is_admin(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            body = await request.json()
            act_type_str = str(body.get("type") or "watching")
            status_str = str(body.get("status") or "online")
            text = str(body.get("text") or "Bio Presence Sync").strip()[:100]

            act_type = {
                "playing": discord.ActivityType.playing,
                "listening": discord.ActivityType.listening,
                "watching": discord.ActivityType.watching,
            }.get(act_type_str, discord.ActivityType.watching)

            dc_status = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
            }.get(status_str, discord.Status.online)

            await self.change_presence(
                status=dc_status,
                activity=discord.Activity(type=act_type, name=text),
            )
            return web.json_response({"ok": True})

        async def handle_send_dm(request):
            if not self._is_admin(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            body = await request.json()
            uid = str(body.get("userId") or "").strip()
            msg = str(body.get("message") or "").strip()[:1000]
            if not uid.isdigit() or not msg:
                return web.json_response({"error": "Thiếu Discord User ID hoặc nội dung"}, status=400)
            try:
                user = self.get_user(int(uid)) or await self.fetch_user(int(uid))
                await user.send(msg)
                return web.json_response({"ok": True})
            except Exception as exc:
                return web.json_response({"error": html.escape(str(exc))}, status=400)

        async def handle_sync_cmds(request):
            if not self._is_admin(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            guild_id = (os.getenv("DEV_GUILD_ID") or os.getenv("DISCORD_GUILD_ID") or "").strip()
            if guild_id.isdigit():
                await self.tree.sync(guild=discord.Object(id=int(guild_id)))
            else:
                await self.tree.sync()
            return web.json_response({"ok": True})

        app.router.add_get("/", handle_dashboard)
        app.router.add_get("/health", handle_health)
        app.router.add_get("/presence/{user_id}", handle_presence)
        app.router.add_get("/members", handle_members)
        app.router.add_get("/api/bot/status", handle_bot_status)
        app.router.add_post("/api/bot/status", handle_update_status)
        app.router.add_post("/api/bot/dm", handle_send_dm)
        app.router.add_post("/api/bot/sync", handle_sync_cmds)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        self.http_runner = runner
        print(f"[Raphael Bridge] Web Manager & Presence API listening on port {port}", flush=True)

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
    token = (os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    if not token:
        print("[Raphael] Thieu DISCORD_TOKEN trong .env")
        return
    bot = RaphaelPresenceBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
