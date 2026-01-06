# type: ignore
import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import requests
import time
from openai import OpenAI
from typing import Optional, Union

currencies = {
    "Australian Dollar": "AUD",
    "Brazilian Real": "BRL",
    "Canadian Dollar": "CAD",
    "Swiss Franc": "CHF",
    "Chinese Renminbi Yuan": "CNY",
    "Czech Koruna": "CZK",
    "Euro": "EUR",
    "British Pound": "GBP",
    "Croatian Kuna": "HRK",
    "Indonesian Rupiah": "IDR",
    "Indian Rupee": "INR",
    "Japanese Yen": "JPY",
    "South Korean Won": "KRW",
    "Mexican Peso": "MXN",
    "Norwegian Krone": "NOK",
    "New Zealand Dollar": "NZD",
    "Polish Zloty": "PLN",
    "Romanian Leu": "RON",
    "Russian Ruble": "RUB",
    "Swedish Krona": "SEK",
    "Singapore Dollar": "SGD",
    "Thai Baht": "THB",
    "Turkish Lira": "TRY",
    "United States Dollar": "USD",
    "South African Rand": "ZAR"
}

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="currency",
        description="Convert a specified Amount from a Currency to another Currency"
    )
    @app_commands.describe(
        amount="Amount to convert",
        currencyfrom="Currency to convert from",
        currencyto="Currency to convert to"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.choices(currencyfrom=[
        app_commands.Choice(name="Australian Dollar", value="AUD"),
        app_commands.Choice(name="Bulgarian Lev", value="BGN"),
        app_commands.Choice(name="Brazilian Real", value="BRL"),
        app_commands.Choice(name="Canadian Dollar", value="CAD"),
        app_commands.Choice(name="Swiss Franc", value="CHF"),
        app_commands.Choice(name="Chinese Renminbi Yuan", value="CNY"),
        app_commands.Choice(name="Czech Koruna", value="CZK"),
        app_commands.Choice(name="Danish Krone", value="DKK"),
        app_commands.Choice(name="Euro", value="EUR"),
        app_commands.Choice(name="British Pound", value="GBP"),
        app_commands.Choice(name="Hong Kong Dollar", value="HKD"),
        app_commands.Choice(name="Hungarian Forint", value="HUF"),
        app_commands.Choice(name="Indonesian Rupiah", value="IDR"),
        app_commands.Choice(name="Japanese Yen", value="JPY"),
        app_commands.Choice(name="South Korean Won", value="KRW"),
        app_commands.Choice(name="Norwegian Krone", value="NOK"),
        app_commands.Choice(name="Polish Zloty", value="PLN"),
        app_commands.Choice(name="Swedish Krona", value="SEK"),
        app_commands.Choice(name="Turkish Lira", value="TRY"),
        app_commands.Choice(name="United States Dollar", value="USD")
    ])
    @app_commands.choices(currencyto=[
        app_commands.Choice(name="Australian Dollar", value="AUD"),
        app_commands.Choice(name="Bulgarian Lev", value="BGN"),
        app_commands.Choice(name="Brazilian Real", value="BRL"),
        app_commands.Choice(name="Canadian Dollar", value="CAD"),
        app_commands.Choice(name="Swiss Franc", value="CHF"),
        app_commands.Choice(name="Chinese Renminbi Yuan", value="CNY"),
        app_commands.Choice(name="Czech Koruna", value="CZK"),
        app_commands.Choice(name="Danish Krone", value="DKK"),
        app_commands.Choice(name="Euro", value="EUR"),
        app_commands.Choice(name="British Pound", value="GBP"),
        app_commands.Choice(name="Hong Kong Dollar", value="HKD"),
        app_commands.Choice(name="Hungarian Forint", value="HUF"),
        app_commands.Choice(name="Indonesian Rupiah", value="IDR"),
        app_commands.Choice(name="Japanese Yen", value="JPY"),
        app_commands.Choice(name="South Korean Won", value="KRW"),
        app_commands.Choice(name="Norwegian Krone", value="NOK"),
        app_commands.Choice(name="Polish Zloty", value="PLN"),
        app_commands.Choice(name="Swedish Krona", value="SEK"),
        app_commands.Choice(name="Turkish Lira", value="TRY"),
        app_commands.Choice(name="United States Dollar", value="USD")
    ])
    async def currency(self, ctx: commands.Context, amount: int, currencyfrom: str, currencyto: str):
        url = f"https://api.frankfurter.dev/v1/latest?base={currencyfrom}&symbols={currencyto}"

        try:
            await ctx.defer()
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                rate = data['rates'][f'{currencyto}']
                raw_result = amount * rate
                result = str(round(raw_result, 2))

                embed = discord.Embed(
                    title=f"Conversion from {currencyfrom} to {currencyto}",
                    description=f"```{amount} * {rate} = {result} {currencyto}```",
                    color=0x00ff00
                ).set_footer(
                    text=f"Executed by {ctx.author.name}"
                )

                await ctx.send(embed=embed)
                return
        except Exception as e:
            await ctx.send("Conversion has failed. Check logs.")
            print(e)


    @commands.hybrid_command(
        name="roll",
        description="Roll a Dice"
    )
    @app_commands.describe(
        sides="Number of sides on the dice",
        amount="Number of dice to roll"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def roll(self, ctx: commands.Context, sides: int, amount: int):
        try:
            await ctx.defer()

            if amount <= 25:
                rolls = [str(random.randint(1, sides)) for _ in range(amount)]
                print(rolls)

                embed = discord.Embed(
                    title=f"{sides}-sided dice roll for {amount} times",
                    description=f"You rolled: {', '.join(rolls)}",
                    color=0x00ff00
                )

                await ctx.send(embed=embed)
                return
            else:
                await ctx.send("Amount too high, please lower it.")
                return
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured:\n```{e}```")

async def setup(bot):
    """Required setup function for cog loading"""
    await bot.add_cog(Fun(bot))
