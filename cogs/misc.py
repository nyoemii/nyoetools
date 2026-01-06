# type: ignore
import sys
import requests 
import os
from subprocess import run
from typing import List, Union
import datetime
import re

import discord
from discord import app_commands
from discord.ext import commands
import psutil

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

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.proc = psutil.Process()

    @commands.hybrid_command(
        name="ping",
        description="Replies with Pong!"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ping(self, ctx: commands.Context):
        embed = discord.Embed(
            color=discord.Color.green(),
            title="Pong!",
            description=f"-# **Latency**: {self.bot.latency * 1000:.1f} ms • **Memory usage**: {size(self.proc.memory_info().rss)}"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="info",
        description="Current System Info"
    )
    @app_commands.describe(ephemeral="Make the response visible only to you")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def info(self, ctx: commands.Context, ephemeral: bool = False):
        await ctx.defer(ephemeral=ephemeral)
        embed = discord.Embed(title="System Info", color=discord.Color.blue(), timestamp=datetime.datetime.now())
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        vmem = psutil.virtual_memory()
        embed.add_field(name="Memory Usage", value=f"{vmem.percent:.1f}% ({size(vmem.total-vmem.available)}/{size(vmem.total)})")
        dusage = psutil.disk_usage('/')
        embed.add_field(name="Disk Usage", value=f"{dusage.percent:.1f}% ({size(dusage.used)}/{size(dusage.total)})")
        nctrs = psutil.net_io_counters()
        embed.add_field(name="Network Stats", value=f"Sent: {size(nctrs.bytes_sent)}\nReceived: {size(nctrs.bytes_recv)}")
        embed.add_field(name="Uptime", value=f"<t:{psutil.boot_time():.0f}:R>")
        embed.add_field(name="Python Version", value=f"`{sys.version}`")
        embed.add_field(name="Discord.py Version", value=f"`{discord.__version__}`")
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_command(
        name="credits",
        description="Gives credits to the people helping and developing"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def credits(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Credits",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Developers",
            value="[nyoemii](https://nyoemii.dev), [plx](https://x.com/plzdonthaxme), [secp192k1](https://github.com/secp192k1)",
            inline=True
        )
        embed.add_field(
            name="Testers",
            value="[Mineek](https://github.com/mineek), [omardotdev](https://omardotdev.github.io), impliedgg, [ie11/positron](https://cdstx4.xyz), mugman",
            inline=True
        )

        await ctx.send(embed=embed)

async def setup(bot):
    """Required setup function for cog loading"""
    await bot.add_cog(Misc(bot))
