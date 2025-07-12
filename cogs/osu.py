import nextcord
from nextcord.ext import commands
import re
import aiohttp
import json
import os
from datetime import datetime

class OsuBeatmapView(nextcord.ui.View):
    def __init__(self, beatmap_data, beatmap_id):
        super().__init__(timeout=300)
        self.beatmap_data = beatmap_data
        self.beatmap_id = beatmap_id

    @nextcord.ui.button(label="🌐 Open in Browser", style=nextcord.ButtonStyle.primary)
    async def open_browser(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(f"https://osu.ppy.sh/s/{self.beatmap_id}", ephemeral=True)

    @nextcord.ui.button(label="📥 osu! Direct", style=nextcord.ButtonStyle.success)
    async def download_beatmap(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(f"osu://dl/{self.beatmap_id}", ephemeral=True)

    @nextcord.ui.button(label="❌ Dismiss", style=nextcord.ButtonStyle.danger)
    async def dismiss(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(view=None)
        self.stop()

class OsuBeatmapConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client_id = os.environ["CLIENT_ID"]
        self.client_secret = os.environ["CLIENT_SECRET"]
        self.access_token = None
        self.token_expires = None

    async def get_access_token(self):
        """Get OAuth2 access token for osu! API v2"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token

        if not self.client_id or not self.client_secret:
            return None

        async with aiohttp.ClientSession() as session:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
                'scope': 'public'
            }

            async with session.post('https://osu.ppy.sh/oauth/token', data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self.access_token = token_data['access_token']
                    from datetime import timedelta
                    self.token_expires = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
                    return self.access_token
                return None

    async def get_beatmapset_info(self, beatmapset_id):
        """Fetch beatmapset information from osu! API v2"""
        token = await self.get_access_token()
        if not token:
            return None

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://osu.ppy.sh/api/v2/beatmapsets/{beatmapset_id}', headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

    def create_beatmap_embed(self, beatmap_data, beatmap_id):
        """Create a rich embed with beatmap information"""
        embed = nextcord.Embed(
            title=f"{beatmap_data['artist']} - {beatmap_data['title']}",
            url=f"https://osu.ppy.sh/s/{beatmap_id}",
            color=0xff69b4
        )

        if beatmap_data.get('covers', {}).get('cover'):
            embed.set_thumbnail(url=beatmap_data['covers']['cover'])

        embed.add_field(name="🎵 Artist", value=beatmap_data['artist'], inline=True)
        embed.add_field(name="🎼 Title", value=beatmap_data['title'], inline=True)
        embed.add_field(name="👤 Creator", value=beatmap_data['creator'], inline=True)

        embed.add_field(name="⭐ Status", value=beatmap_data['status'].replace('_', ' ').title(), inline=True)
        embed.add_field(name="🎯 BPM", value=str(beatmap_data.get('bpm', 'N/A')), inline=True)

        length_seconds = 0
        if beatmap_data.get('beatmaps') and len(beatmap_data['beatmaps']) > 0:
            first_beatmap = beatmap_data['beatmaps'][0]
            length_seconds = first_beatmap.get('total_length', 0) or first_beatmap.get('hit_length', 0) or first_beatmap.get('length', 0)

        length_display = f"{length_seconds // 60}:{length_seconds % 60:02d}" if length_seconds > 0 else "N/A"
        embed.add_field(name="🕐 Length", value=length_display, inline=True)

        difficulty_count = len(beatmap_data.get('beatmaps', []))
        embed.add_field(name="🎮 Difficulties", value=str(difficulty_count), inline=True)

        if beatmap_data.get('tags'):
            tags = beatmap_data['tags'][:100] + "..." if len(beatmap_data['tags']) > 100 else beatmap_data['tags']
            embed.add_field(name="🏷️ Tags", value=tags, inline=False)

        if beatmap_data.get('ranked_date'):
            ranked_date = datetime.fromisoformat(beatmap_data['ranked_date'].replace('Z', '+00:00'))
            embed.add_field(name="📅 Ranked", value=ranked_date.strftime('%Y-%m-%d'), inline=True)

        embed.set_footer(text=f"Beatmapset ID: {beatmap_id}")
        return embed

    def create_fallback_embed(self, beatmap_id):
        """Create a simple embed when API data is not available"""
        embed = nextcord.Embed(
            title="🎵 Beatmap Found!",
            description=f"Found a beatmap with ID: {beatmap_id}",
            url=f"https://osu.ppy.sh/s/{beatmap_id}",
            color=0x00ff00
        )
        embed.add_field(name="🌐 View Online", value=f"[Click here](https://osu.ppy.sh/s/{beatmap_id})", inline=False)
        embed.set_footer(text=f"Beatmapset ID: {beatmap_id}")
        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        pattern = r'(?:beatmapsets|b)/(\d+)'
        matches = re.findall(pattern, message.content)

        if matches:
            for beatmap_id in matches:
                try:
                    beatmap_data = await self.get_beatmapset_info(beatmap_id)

                    if beatmap_data:
                        embed = self.create_beatmap_embed(beatmap_data, beatmap_id)
                        view = OsuBeatmapView(beatmap_data, beatmap_id)
                        await message.channel.send(embed=embed, view=view)
                    else:
                        embed = self.create_fallback_embed(beatmap_id)
                        view = OsuBeatmapView(None, beatmap_id)
                        await message.channel.send(embed=embed, view=view)

                except Exception as e:
                    embed = self.create_fallback_embed(beatmap_id)
                    view = OsuBeatmapView(None, beatmap_id)
                    await message.channel.send(embed=embed, view=view)
                    print(f"Error fetching beatmap {beatmap_id}: {e}")

def setup(bot):
    bot.add_cog(OsuBeatmapConverter(bot))
