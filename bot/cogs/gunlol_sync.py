import os
import discord
from discord import app_commands
from discord.ext import commands


class GunLolSyncCog(commands.Cog):
    """Minimal cog keeping Raphael online in the server for guns.lol presence sync."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bio", description="Lấy đường dẫn trang Cú Profile cá nhân")
    @app_commands.describe(username="Tên người dùng trên Cú Profile (mặc định dùng tên Discord)")
    async def bio(self, interaction: discord.Interaction, username: str | None = None):
        handle = (username or interaction.user.name).strip().lower()
        base_url = os.getenv("GUNLOL_BASE_URL", "http://localhost:4000").rstrip("/")
        embed = discord.Embed(
            title=f"Cú Profile — {interaction.user.display_name}",
            description=f"🦉 Truy cập Bio tại: **{base_url}/{handle}**",
            color=0xA855F7,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="syncstatus", description="Kiểm tra trạng thái đồng bộ Discord sang Bio")
    async def sync_status(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        status_str = str(member.status) if member else "unknown"
        act_text = "Không có hoạt động"
        if member and member.activities:
            first = member.activities[0]
            act_text = getattr(first, "state", None) or getattr(first, "name", None) or str(first)

        embed = discord.Embed(
            title="Trạng thái Đồng bộ Live",
            color=0x22C55E if status_str == "online" else 0xF0B232 if status_str == "idle" else 0xA855F7,
        )
        embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="Trạng thái", value=f"`{status_str}`", inline=True)
        embed.add_field(name="Hoạt động hiện tại", value=act_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GunLolSyncCog(bot))
