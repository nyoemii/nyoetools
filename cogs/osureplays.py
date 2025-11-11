# type: ignore
import nextcord
from nextcord import Attachment, Interaction, IntegrationType, InteractionContextType, slash_command
import os
import re
from nextcord.ext.commands import Bot, Cog
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

class OsuReplayData(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.replay_folder = "" # replay folder

    @slash_command(
        name="replayinfo",
        description="Analyzes your Replay and returns fancy values",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        ]
    )
    async def replayinfo(self, interaction: Interaction[Bot], replay_file: Attachment):
        await interaction.response.defer()
        try:
            if not os.path.exists(self.replay_folder):
                os.makedirs(self.replay_folder)
            
            replay_path = os.path.join(self.replay_folder, replay_file.filename)
            with open(replay_path, "wb") as f:
                f.write(await replay_file.read())
            
            replay = Replay.from_path(replay_path)
            mods_int = replay.mods
            mods_display = decode_mods(mods_int)
            
            embed = nextcord.Embed(title="Replay Info", description=f"Uploader: {replay.username}", color=0xff00ff)

            embed.add_field(name="Gamemode", value=replay.mode.name, inline=True)
            embed.add_field(name="Score", value=replay.score, inline=True)
            
            accuracy = (300 * replay.count_300 + 100 * replay.count_100 + 50 * replay.count_50) / (300 * (replay.count_300 + replay.count_100 + replay.count_50 + replay.count_miss))
            embed.add_field(name="Accuracy", value=f"{accuracy * 100:.2f}%", inline=True)
            
            embed.add_field(name="300s", value=replay.count_300, inline=True)
            embed.add_field(name="100s", value=replay.count_100, inline=True)
            embed.add_field(name="50s", value=replay.count_50, inline=True)
            embed.add_field(name="Misses", value=replay.count_miss, inline=True)
            embed.add_field(name="Mods", value=mods_display, inline=True)
            
            await interaction.send(embed=embed)
            return
            
        except Exception as e:
            await interaction.send("An error occured, check the logs for more info.")
            print(e)