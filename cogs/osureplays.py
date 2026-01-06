# type: ignore
import discord
from discord import app_commands
from discord.ext import commands
import os
import re
from osrparse import Replay

def calculate_mods(mods: list):
    return sum(MOD_VALUES.get(mod, 0) for mod in mods)

MOD_VALUES = {
    "NF": 1,
    "EZ": 2,
    "HD": 8,
    "HR": 16,
    "SD": 32,
    "DT": 64,
    "RX": 128,
    "HT": 256,
    "NC": 576,
    "FL": 1024,
    "SO": 4096,
    "PF": 16416
}

def decode_mods(mods_int):
    """Decode the mods integer into a readable mod string."""
    if mods_int == 0:
        return "+NM"
    mods_list = []
    for mod, value in sorted(MOD_VALUES.items(), key=lambda x: -x[1]): # Sorts by value descending
        if mods_int & value: # Checks if the mod is active
            mods_list.append(mod)
            mods_int -= value
    return "+" + "".join(mods_list)

class OsuReplayData(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.replay_folder = "FOLDER TO SAVE REPLAYS TO" # CHANGE THIS!!!!

    @commands.hybrid_command(
        name="replayinfo",
        description="Analyzes your Replay and returns fancy values"
    )
    @app_commands.describe(replay_file="The osu! replay file to analyze")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def replayinfo(self, ctx: commands.Context, replay_file: discord.Attachment):
        await ctx.defer()
        try:
            if not os.path.exists(self.replay_folder):
                os.makedirs(self.replay_folder)
            
            replay_path = os.path.join(self.replay_folder, replay_file.filename)
            with open(replay_path, "wb") as f:
                f.write(await replay_file.read())
            
            replay = Replay.from_path(replay_path)
            mods_int = replay.mods
            mods_display = decode_mods(mods_int)
            
            embed = discord.Embed(title="Replay Info", description=f"Uploader: {replay.username}", color=0xff00ff)

            embed.add_field(name="Gamemode", value=replay.mode.name, inline=True)
            embed.add_field(name="Score", value=replay.score, inline=True)
            
            accuracy = (300 * replay.count_300 + 100 * replay.count_100 + 50 * replay.count_50) / (300 * (replay.count_300 + replay.count_100 + replay.count_50 + replay.count_miss))
            embed.add_field(name="Accuracy", value=f"{accuracy * 100:.2f}%", inline=True)
            
            embed.add_field(name="300s", value=replay.count_300, inline=True)
            embed.add_field(name="100s", value=replay.count_100, inline=True)
            embed.add_field(name="50s", value=replay.count_50, inline=True)
            embed.add_field(name="Misses", value=replay.count_miss, inline=True)
            embed.add_field(name="Mods", value=mods_display, inline=True)
            
            await ctx.send(embed=embed)
            return
            
        except Exception as e:
            await ctx.send("An error occured, check the logs for more info.")
            print(e)

async def setup(bot):
    """Required setup function for cog loading"""
    await bot.add_cog(OsuReplayData(bot))
