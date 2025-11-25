import nextcord
from nextcord import IntegrationType, InteractionContextType
from nextcord.ext import tasks, commands
import aiohttp
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger("osu_tracking")


class OsuTracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.track_file = "data/tracking.json"
        self.client_id = os.getenv("OSU_CLIENT_ID")
        self.client_secret = os.getenv("OSU_CLIENT_SECRET")
        self.token = None
        self.tracked_users = self.load_tracked()

    def load_tracked(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.track_file):
            with open(self.track_file, "r") as f:
                return json.load(f)
        return {}

    def save_tracked(self):
        with open(self.track_file, "w") as f:
            json.dump(self.tracked_users, f, indent=2)

    async def get_token(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://osu.ppy.sh/oauth/token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                    "scope": "public",
                },
            ) as resp:
                data = await resp.json()
                return data["access_token"]

    async def get_user_info(self, username):
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://osu.ppy.sh/api/v2/users/{username}/osu", headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

    async def get_recent_scores(self, user_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://osu.ppy.sh/api/v2/users/{user_id}/scores/recent",
                headers=headers,
                params={"include_fails": 0, "limit": 1},
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []

    @nextcord.slash_command(
        name="osutrackstatus",
        description="Is the tracking even working?",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        ],
    )
    async def osutrackstatus(self, ctx):
        await ctx.send(f"```json\n{json.dumps(self.tracked_users, indent=2)}\n```")

    @nextcord.slash_command(
        name="osutrack",
        description="Setup for tracking your osu! scores",
        integration_types=[
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
        ],
    )
    async def osutrack(self, ctx, osu_username: str):
        """Track an osu! user's scores in this channel"""
        if not self.token:
            self.token = await self.get_token()

        user_info = await self.get_user_info(osu_username)
        if not user_info:
            await ctx.send(f"❌ User `{osu_username}` not found!")
            return

        user_id = str(user_info["id"])
        channel_id = str(ctx.channel.id)

        if user_id not in self.tracked_users:
            self.tracked_users[user_id] = {
                "username": user_info["username"],
                "channels": [channel_id],
                "last_score_id": None,
            }
        else:
            if channel_id not in self.tracked_users[user_id]["channels"]:
                self.tracked_users[user_id]["channels"].append(channel_id)

        self.save_tracked()
        await ctx.send(f"✅ Now tracking **{user_info['username']}** in this channel!")

    @nextcord.slash_command(
        name="osuuntrack",
        description="Removes your recent score tracking.",
        integration_types=[
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
        ],
    )
    async def osuuntrack(self, ctx, osu_username: str):
        """Stop tracking an osu! user in this channel"""
        user_info = await self.get_user_info(osu_username)
        if not user_info:
            await ctx.send(f"❌ User `{osu_username}` not found!")
            return

        user_id = str(user_info["id"])
        channel_id = str(ctx.channel.id)

        if user_id in self.tracked_users:
            if channel_id in self.tracked_users[user_id]["channels"]:
                self.tracked_users[user_id]["channels"].remove(channel_id)
                if not self.tracked_users[user_id]["channels"]:
                    del self.tracked_users[user_id]
                self.save_tracked()
                await ctx.send(f"✅ Stopped tracking **{user_info['username']}**")
                return

        await ctx.send("❌ Not tracking this user in this channel!")

    @tasks.loop(minutes=1)
    async def check_scores(self):
        print(
            f"\n=========[ {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%H:%M:%S')} ]=========\n=== Score check starting ==="
        )

        if not self.token:
            return

        print(f"Checking {len(self.tracked_users)} tracked user(s)")

        for user_id, data in list(self.tracked_users.items()):
            print(f"  Checking {data['username']} (ID: {user_id})")

            try:
                scores = await self.get_recent_scores(user_id)

                if not scores:
                    continue

                latest_score = scores[0]
                score_id = latest_score["id"]

                if data["last_score_id"] != score_id:
                    if data["last_score_id"] is not None:
                        print("    🎉 NEW SCORE DETECTED! Posting...")
                        embed = self.create_score_embed(latest_score, data["username"])
                        for channel_id in data["channels"]:
                            channel = self.bot.get_channel(int(channel_id))
                            if channel:
                                await channel.send(embed=embed)
                                print(f"    ✓ Posted to channel {channel_id}")
                            else:
                                print(f"    ✗ Channel {channel_id} not found")
                    else:
                        print("    Skipping (first time tracking)")

                    self.tracked_users[user_id]["last_score_id"] = score_id
                    self.save_tracked()
                else:
                    print("    No new scores")

            except Exception as _:
                print("    ERROR: {e}")
                import traceback

                traceback.print_exc()

        print("=== Score check complete ===\n")

    def create_score_embed(self, score, username):
        beatmap = score["beatmap"]
        beatmapset = score["beatmapset"]

        embed = nextcord.Embed(
            title=f"{beatmapset['artist']} - {beatmapset['title']} [{beatmap['version']}]",
            url=f"https://osu.ppy.sh/b/{beatmap['id']}",
            color=0xFF69B4,
        )

        embed.set_author(
            name=f"{username} set a new score!",
            url=f"https://osu.ppy.sh/users/{score['user_id']}",
            icon_url=f"https://a.ppy.sh/{score['user_id']}",
        )

        embed.set_thumbnail(url=beatmapset["covers"]["list"])

        mods = "+" + "".join(score["mods"]) if score["mods"] else "NoMod"
        rank_emojis = {
            "XH": "🥈",
            "X": "🥇",
            "SH": "🥈",
            "S": "🥇",
            "A": "🟢",
            "B": "🔵",
            "C": "🟡",
            "D": "🟠",
            "F": "🔴",
        }

        # Build combo string
        combo_str = f"{score['max_combo']}x"
        if beatmap.get("max_combo"):
            combo_str += f" / {beatmap['max_combo']}x"

        embed.add_field(
            name="Score Info",
            value=f"**Rank:** {rank_emojis.get(score['rank'], score['rank'])} {score['rank']}\n"
            f"**Score:** {score['score']:,}\n"
            f"**Accuracy:** {score['accuracy'] * 100:.2f}%\n"
            f"**Combo:** {combo_str}\n"
            f"**Mods:** {mods}",
            inline=True,
        )

        if score.get("pp"):
            embed.add_field(
                name="Performance",
                value=f"**PP:** {score['pp']:.2f}pp\n"
                f"**Stars:** ⭐ {beatmap['difficulty_rating']:.2f}",
                inline=True,
            )

        stats = score["statistics"]
        embed.add_field(
            name="Hits",
            value=f"300: {stats['count_300']} | 100: {stats['count_100']} | 50: {stats['count_50']} | Miss: {stats['count_miss']}",
            inline=False,
        )

        return embed


def setup(bot):
    bot.add_cog(OsuTracking(bot))
