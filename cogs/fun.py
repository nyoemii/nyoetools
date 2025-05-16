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