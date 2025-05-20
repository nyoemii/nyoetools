import io
import random
from nextcord import IntegrationType, Interaction, InteractionContextType, \
    SlashOption, slash_command
import nextcord
from nextcord.ext.commands import Bot, Cog
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_L
import requests
from requests import HTTPError

class Utils(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        description="Creates a QR Code for your defined URL or Text",
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
    async def createqr(
        self,
        interaction: Interaction[Bot],
        data: str = SlashOption(name="Input")
    ):
        await interaction.response.defer()
        qr = QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, kind="PNG")
        buf.seek(0)

        file = nextcord.File(buf, filename="qrcode.png")
        await interaction.send(file=file)

    @slash_command(
        description="Sync Command",
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
    async def sync(self, interaction: Interaction[Bot]):
        if not interaction.user or interaction.user.id == 277830029399031818:
            await interaction.response.defer()
            await self.bot.sync_all_application_commands()
            await interaction.send("Successfully synchronized Slash Commands.")
        else:
            await interaction.send("Missing permissions.")

    @slash_command(
        description="Get latest Commit of a specified GitHub Repo",
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
    async def github(
        self,
        interaction: Interaction[Bot],
        repo: str,
        user: str,
        commitname: str
    ):
        if not interaction.user:
            return
        base_url = "https://api.github.com/repos/"
        query = ""
        username = interaction.user.name

        query += f"{user}/{repo}/commits/{commitname}"

        await interaction.response.defer()

        response = None
        try:
            response = requests.get(base_url + query, timeout=10)

            if response.status_code == 200:
                data = response.json()

                commit = data['commit']
                author = data['author']

                git_commit_hash = data.get("sha", {})
                git_message = commit.get("message", "No message attached.")
                git_avatar = author.get("avatar_url", {})
                git_profile = author.get("html_url", {})

            else:
                await interaction.send("GitHub Repo not found.")
                return

            embed = nextcord.Embed(
                title=f"Information about {repo}",
                description=f"by {user}",
                color=nextcord.Color.green()
            ).add_field(
                name="Commit Hash",
                value=f"[{git_commit_hash}](https://github.com/{user}/{repo}/commits/{git_commit_hash})",
                inline=False
            ).add_field(
                name="Message: ",
                value=f"{git_message}",
                inline=False
            ).set_author(
                name=f"{user}",
                url=f"{git_profile}",
                icon_url=f"{git_avatar}"
            ).set_footer(
                icon_url="https://github.githubassets.com/assets/GitHub-Mark-ea2971cee799.png",
                text=f"Command ran by {username}"
            )

            await interaction.send(embed=embed)
            return
        except HTTPError:
            await interaction.send(f"Error accessing GitHub: {response.status_code if response is not None else 'Unknown Error'}")
            return
        except Exception: 
            await interaction.send("An error occured.")
            return
        
    @slash_command(
        description="Checks if a Minecraft Name is available",
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
    async def mcname(self, interaction: Interaction[Bot], username: str):
        url = f"https://mcprofile.io/api/v1/java/username/{username}"

        try:
            await interaction.response.defer()
            response = requests.get(url)
            
            if username.isalnum() == True:
                if response.json().get('message') is None:
                    await interaction.send(f'Username "{username}" is taken.')
                else:
                    await interaction.send(f'Username "{username}" is available!')
            else:
                await interaction.send(f'Username "{username}" contains invalid characters, therefore it is not available.')
        except Exception as e:
            await interaction.send("Error: Logs")
            print(e)