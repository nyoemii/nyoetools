from nextcord import File, IntegrationType, Interaction, InteractionContextType, \
    SlashOption, slash_command
from nextcord.exit.commands import Bot, Cog

class Fun(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        description=":trol:",
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
    async def osu(
        self,
        interaction: Interaction[Bot],
        clip: str = SlashOption(
            choices={} # your choices go here, written like this: {"option_name": "file_name", "option_name2": "file_name2"}
        )
    ):
        try:
            file = f"{clip}"
            await interaction.response.defer()
            await interaction.send(file=File(file))
        except Exception:
            await interaction.send("Error: File not found")

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
        choices={"Australian Dollar": "AUD", "Bulgarian Lev": "BGN", "Brazilian Real": "BRL", "Canadian Dollar": "CAD", "Swiss Franc": "CHF", "Chinese Renminbi Yuan": "CNY", "Czech Koruna": "CZK", "Danish Krone": "DKK", "Euro": "EUR", "British Pound": "GBP", "Hong Kong Dollar": "HKD", "Hungarian Forint": "HUF", "Indonesian Rupiah": "IDR", "Japanese Yen": "JPY", "South Korean Won": "KRW", "Norwegian Krone": "NOK", "Polish Zloty": "PLN", "Swedish Krona": "SEK", "Turkish Lira": "TRY", "United States Dollar": "USD"}), currencyto: str = SlashOption(
        choices={"Australian Dollar": "AUD", "Bulgarian Lev": "BGN", "Brazilian Real": "BRL", "Canadian Dollar": "CAD", "Swiss Franc": "CHF", "Chinese Renminbi Yuan": "CNY", "Czech Koruna": "CZK", "Danish Krone": "DKK", "Euro": "EUR", "British Pound": "GBP", "Hong Kong Dollar": "HKD", "Hungarian Forint": "HUF", "Indonesian Rupiah": "IDR", "Japanese Yen": "JPY", "South Korean Won": "KRW", "Norwegian Krone": "NOK", "Polish Zloty": "PLN", "Swedish Krona": "SEK", "Turkish Lira": "TRY", "United States Dollar": "USD"})):
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

        try:
            await interaction.response.defer()
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
                    description=f"You rolled: {','.join(rolls)}",
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
