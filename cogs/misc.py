# type: ignore
import sys
import requests 
import os
from subprocess import run
from typing import List, Union
import datetime
import re
from dotenv import load_dotenv

from nextcord import Colour, Embed, \
    IntegrationType, Interaction, InteractionContextType, slash_command, SlashOption
import nextcord
from nextcord.ext.commands import Bot, Cog
import psutil

from . import discord_ansi_adapter

if os.name == "nt":
    import dotenv
    dotenv.load_dotenv()

newsapikey = os.environ["NEWS_API_KEY"]

class HumanBytes:
    METRIC_LABELS: List[str] = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    BINARY_LABELS: List[str] = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    PRECISION_OFFSETS: List[float] = [0.5, 0.05, 0.005, 0.0005] # PREDEFINED FOR SPEED.
    PRECISION_FORMATS: List[str] = ["{}{:.0f} {}", "{}{:.1f} {}", "{}{:.2f} {}", "{}{:.3f} {}"] # PREDEFINED FOR SPEED.

    @staticmethod
    def format(num: Union[int, float], metric: bool=False, precision: int=1) -> str:
        """
        Human-readable formatting of bytes, using binary (powers of 1024)
        or metric (powers of 1000) representation.
        """

        assert isinstance(num, (int, float)), "num must be an int or float"
        assert isinstance(metric, bool), "metric must be a bool"
        assert isinstance(precision, int) and precision >= 0 and precision <= 3, "precision must be an int (range 0-3)"

        unit_labels = HumanBytes.METRIC_LABELS if metric else HumanBytes.BINARY_LABELS
        last_label = unit_labels[-1]
        unit_step = 1000 if metric else 1024
        unit_step_thresh = unit_step - HumanBytes.PRECISION_OFFSETS[precision]

        is_negative = num < 0
        if is_negative: # Faster than ternary assignment or always running abs().
            num = abs(num)

        for unit in unit_labels:
            if num < unit_step_thresh:
                # VERY IMPORTANT:
                # Only accepts the CURRENT unit if we're BELOW the threshold where
                # float rounding behavior would place us into the NEXT unit: F.ex.
                # when rounding a float to 1 decimal, any number ">= 1023.95" will
                # be rounded to "1024.0". Obviously we don't want ugly output such
                # as "1024.0 KiB", since the proper term for that is "1.0 MiB".
                break
            if unit != last_label:
                # We only shrink the number if we HAVEN'T reached the last unit.
                # NOTE: These looped divisions accumulate floating point rounding
                # errors, but each new division pushes the rounding errors further
                # and further down in the decimals, so it doesn't matter at all.
                num /= unit_step

        return HumanBytes.PRECISION_FORMATS[precision].format("-" if is_negative else "", num, unit) # pyright: ignore[reportPossiblyUnboundVariable]

size = HumanBytes.format

class Misc(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.proc = psutil.Process()

    @slash_command(
        description="Fastfetch :3",
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
    async def fastfetch(self, interaction: Interaction[Bot]):
        await interaction.response.defer()
        with open("skulley.txt", "w", encoding="ascii") as f:
            f.write("$ fastfetch\n")
            f.flush()
            p = run(
                ["fastfetch",
                 "--title-format", "{#bold_title}nyoemi{#reset_default}@{#bold_title}nyoetools",
                 "--config","config.jsonc",
                 "--pipe", "false"],
                stdout=f,
                check=False
            )
        if p.returncode != 0:
            embed = Embed(
                color=Colour.red(),
                title="Error",
                description=f"```\n{p.stderr}\n```"
            )
            await interaction.send(embed=embed)
            return


        with open("skulley.txt", "r", encoding="ascii") as f:
            await interaction.send(
                "```ansi\n" + \
                discord_ansi_adapter \
                    .do_match(
                        re.sub(r"\[[\d]*[ABCDHJKlhsu]", "", f.read())
                        .replace(r"[0;39m", "[0;37m")
                    ).replace("\x1B[0m8;;file:///\x1B[0m/\x1B[0m8;;\x1B[0m", "/") + \
                "\n```"
            )
            return

    @slash_command(
        description="Replies with Pong!",
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
    async def ping(self, interaction: Interaction[Bot]):
        embed: Embed = Embed(
            color=Colour.green(),
            title="Pong!",
            description=f"-# **Latency**: {self.bot.latency * 1000:.1f} ms • **Memory usage**: {size(self.proc.memory_info().rss)}"
        )
        await interaction.response.send_message(embed=embed)

    @slash_command(description="Current system Info")
    async def info(self, iact: Interaction[Bot], ephemeral: bool = False):
        await iact.response.defer(ephemeral=ephemeral)
        embed: Embed = Embed(title="System Info", color=Colour.blue(), timestamp=datetime.datetime.now())
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        vmem = psutil.virtual_memory()
        embed.add_field(name="Memory Usage", value=f"{vmem.percent:.1f}% ({size(vmem.total-vmem.available)}/{size(vmem.total)})")
        dusage = psutil.disk_usage('/')
        embed.add_field(name="Disk Usage", value=f"{dusage.percent:.1f}% ({size(dusage.used)}/{size(dusage.total)})")
        nctrs = psutil.net_io_counters()
        embed.add_field(name="Network Stats", value=f"Sent: {size(nctrs.bytes_sent)}\nReceived: {size(nctrs.bytes_recv)}")
        embed.add_field(name="Uptime", value=f"<t:{psutil.boot_time():.0f}:R>")
        embed.add_field(name="Python Version", value=f"`{sys.version}`")
        await iact.send(embed=embed, ephemeral=ephemeral)

    @slash_command(
        name="credits",
        description="Gives credits to the people helping and developing",
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
    async def credits(self, interaction: Interaction[Bot]):
        embed = nextcord.Embed(
            title="Credits",
            color=nextcord.Color.blue()
        )

        embed.add_field(
            name="Developers",
            value="[nyoemii](https://nyoemii.dev),\n[plx](https://x.com/plzdonthaxme)",
            inline=True
        )
        embed.add_field(
            name="Testers",
            value="[Mineek](https://github.com/mineek)\n[omardotdev](https://omardotdev.github.io),\nimpliedgg, [ie11/positron](https://cdstx4.xyz),\nmugman",
            inline=True
        )

        await interaction.send(embed=embed)