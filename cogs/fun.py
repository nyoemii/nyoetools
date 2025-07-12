# type: ignore
from nextcord import IntegrationType, Interaction, InteractionContextType, SlashOption, slash_command, Embed, User, Member
from nextcord.ext.commands import Bot, Cog
from typing import Optional, Union
import random
import os
import time
import requests
from openai import OpenAI

# Has to only be 25 items... :( thanks discord api
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


class Fun(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        description="Talk to nyoe!",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def nyoeai(self, interaction: Interaction[Bot], query: str):
        await interaction.response.defer()
        try:
            client = OpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url="https://api.groq.com/openai/v1",
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ""},  # your ai prompt
                    {"role": "user", "content": f"{query}"}
                ],
                temperature=1.3,
                stream=False
            )
            await interaction.send(response.choices[0].message.content)
        except Exception as e:
            await interaction.send("An error occured, check Logs")
            print(e)

    @slash_command(
        description="Convert a specified Amount from a Currency to another Currency",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def currency(self, interaction: Interaction[Bot], amount: int, currencyfrom: str = SlashOption(
        choices=currencies), currencyto: str = SlashOption(
        choices=currencies)):
        url = f"https://api.frankfurter.dev/v1/latest?base={currencyfrom}&symbols={currencyto}"

        try:
            await interaction.response.defer()
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                rate = data['rates'][f'{currencyto}']
                raw_result = amount * rate
                result = str(round(raw_result, 2))

                embed = Embed(
                    title=f"Conversion from {currencyfrom} to {currencyto}",
                    description=f"```{amount} * {rate} = {result} {currencyto}```",
                    color=0x00ff00
                ).set_footer(
                    text=f"Executed by {interaction.user.name}"
                )

                await interaction.send(embed=embed)
                return
        except Exception as e:
            await interaction.send("Conversion has failed. Check logs.")
            print(e)

    @slash_command(
        description="uhhhh, smoking is bad mkayyy",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def southpark(self, interaction: Interaction[Bot]):
        url = "https://southparkquotes.onrender.com/v1/quotes"
        await interaction.response.defer()

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                print(data)

                quote = data[0]['quote']
                char = data[0]['character']

                embed = Embed(
                    title="Random South Park Quote :3",
                    description=f'"{quote}" - {char}',
                    color=0xff0000
                )

                await interaction.send(embed=embed)
                return
        except Exception as e:
            print(e)
            await interaction.send("Check logs")

    @slash_command(
        description="Roll a Dice",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def roll(self, interaction: Interaction[Bot], sides: int, amount: int):
        try:
            await interaction.response.defer()

            if amount <= 25:
                rolls = [str(random.randint(1, sides)) for _ in range(amount)]
                print(rolls)

                embed = Embed(
                    title=f"{sides}-sided dice roll for {amount} times",
                    description=f"You rolled: {', '.join(rolls)}",
                    color=0x00ff00
                )

                await interaction.send(embed=embed)
                return
            else:
                await interaction.send("Amount too high, please lower it.")
                return
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured:\n```{e}```")

    @slash_command(
        description="Say something as the Bot",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def meow(self, interaction: Interaction[Bot], treats: str):
        await interaction.response.send_message(f"```ansi\n{treats}```")

    @slash_command(
        description="Rates the cuteness of someone.",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        ],
    )
    async def cuteness(self, interaction: Interaction[Bot], user: Union[User, Member], is_random: str = SlashOption(name="random", choices=["Yes", "No"], required=False, default="No")):
        try:
            _user: int = user.id

            if is_random == "Yes":
                random_number: int = lambda: sum([int(str(time.time_ns())[14:-2]) for _ in range(100)])
                _user += random_number()

            cute_level = _user % 101

            await interaction.response.send_message(f"{user.mention} is **{cute_level}%** cute")
        except TypeError:
            await interaction.send(f"An error occured.\nIs the bot in the guild?", ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured:\n```{e}```")