# type: ignore
import io
from nextcord import IntegrationType, Interaction, InteractionContextType, \
    SlashOption, slash_command, Embed
import nextcord
from nextcord.ext.commands import Bot, Cog
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_L
import requests
from requests import HTTPError
import os
from datetime import datetime, timedelta
from typing import Optional, Union
import base64
import json
import pytz

class Utils(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.encodings = {
            "Base16": base64.b16encode,
            "Base32": base64.b32encode,
            "Base64": base64.b64encode,
            "Base85": base64.b85encode,
            "HEX": bytes.hex,
        }
        self.decodings = {
            "Base16": base64.b16decode,
            "Base32": base64.b32decode,
            "Base64": base64.b64decode,
            "Base85": base64.b85decode,
            "HEX": bytes.fromhex,
        }

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
        data: str = SlashOption(name="input")
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
        usre = interaction.user
        userpfp = usre.avatar

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
                title=f"Information about {repo} by {user}",
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
                icon_url=userpfp.url,
                text=f"Command ran by {username}"
            )

            await interaction.send(embed=embed)
            return
        except HTTPError:
            await interaction.send(f"Error accessing GitHub: {response.status_code if response is not None else 'Unknown Error'}")
            return
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            return

    @slash_command(
        description="Gives you news about a specified topic",
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
    async def news(self, interaction: Interaction[Bot], category: str):
        try:
            await interaction.response.defer()

            newsapikey = os.environ["NEWS_API_KEY"]

            url = f"https://newsapi.org/v2/everything?q={category}&apiKey={newsapikey}"
            response = requests.get(url)

            if response.status_code == 200:
                articles = response.json().get('articles', [])
                print(url)

                article = articles[0]

                if articles:
                    news_embed = nextcord.Embed(
                        title=f"Latest news about {category.capitalize()}", color=0x00ff00
                    )

                    published_at = article['publishedAt']
                    parse_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                    publish_date = parse_date.strftime("%B %d, %Y, %I:%M %p %Z")

                    if article.get("urlToImage"):
                        news_embed.set_thumbnail(url=article["urlToImage"])

                    if article:
                        news_embed.add_field(name=article['title'], value=f"[Read more]({article['url']})", inline=False)
                        news_embed.set_footer(text=f"Source: {article['source']['name']} | Published: {publish_date}")
                        await interaction.send(embed=news_embed)
                else:
                    await interaction.send("No news found.")
            else:
                await interaction.send("Failed to get news.")

        except Exception as e:
            await interaction.send("An error occured, check Bot Logs")
            print(e)

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
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"

        try:
            await interaction.response.defer()
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                if 'name' in data:
                    await interaction.send(f"The username `{data['name']}` is already taken.")
                else:
                    await interaction.send("Unexpected response from Mojang's API.")
            elif len(username) < 3 or len(username) > 16:
                await interaction.send(f"The username `{username}` is not available because it is too {"long" if len(username) > 16 else "short"}.")
            else:
                data = response.json()
                if 'errorMessage' in data and "Couldn't find any profile" in data['errorMessage']:
                    await interaction.send(f"The username `{username}` is available!")
                else:
                    await interaction.send(f"Error checking username: {data.get('errorMessage', 'Unknown error')}")
        except Exception as e:
            await interaction.send("Error: Logs")
            print(e)

    @slash_command(
        description="Grabs a Users Avatar if possible.",
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
    async def avatar(self, interaction: Interaction[Bot], user: Optional[Union[nextcord.User, nextcord.Member]] = None):
        await interaction.response.defer()

        try:
            if user is None:
                user = interaction.user
            if user is None:
                await interaction.send("Failed to get user!")
                return

            userpfp = user.avatar
            if userpfp is None:
                await interaction.send("user.avatar was None!")

            embed = Embed(
                title=f"{user.name}'s Avatar",
                color=0x0000ff,
                timestamp=datetime.now()
            )

            embed.set_image(userpfp.url)

            await interaction.send(embed=embed)
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Encodes your message into various types.",
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
    async def encode(self, interaction: Interaction[Bot], message: str, method: str = SlashOption(choices=self.encodings)):
        await interaction.response.defer()

        encoded_message = self.encodings[method](message.encode("utf-8"))

        if type(encoded_message) == bytes:
            encoded_message = encoded_message.decode("utf-8")

        try:
            await interaction.send(f"```\n{encoded_message}\n```")
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Decodes your message into various types.",
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
    async def decode(self, interaction: Interaction[Bot], message: str, method: str = SlashOption(choices=self.decodings)):
        await interaction.response.defer()

        msg = message if method == "HEX" else message.encode("utf-8")

        decoded_message = self.decodings[method](msg)

        if type(decoded_message) == bytes:
            decoded_message = decoded_message.decode("utf-8")

        try:
            await interaction.send(f"```\n{decoded_message}\n```")
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Sets your timezone.",
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
    async def settimezone(self, interaction: Interaction[Bot], timezone: str):
        await interaction.response.defer()

        if timezone not in pytz.all_timezones:
            await interaction.send("Invalid timezone. Laugh at this user.")
            return

        try:
            user_id = interaction.user.id
            username = interaction.user.name
            with open("users.json", "r") as f:
                users = json.load(f)
            users[str(user_id)] = {"timezone": timezone}
            with open("users.json", "w") as f:
                json.dump(users, f, indent=4)
            await interaction.send(f"Set timezone to {timezone} for user {username}.")
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Gets the current time based on your set timezone.",
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
    async def time(self, interaction: Interaction[Bot], user: Optional[Union[nextcord.User, nextcord.Member]] = None):
        await interaction.response.defer()

        try:
            if user is None:
                user_id = interaction.user.id
            else:
                user_id = user.id
            with open("users.json", "r") as f:
                users = json.load(f)
            if str(user_id) not in users:
                await interaction.send(f"Please set your timezone using `/settimezone <timezone>`{f', {user.mention}' if user else ''}.")
                return
            timezone = users[str(user_id)]["timezone"]
            current_time = datetime.now(pytz.timezone(timezone))
            current_time_local = current_time.astimezone(pytz.timezone(timezone))
            await interaction.send(f"Current local time for <@{user_id}> is {current_time_local.strftime('%Y-%m-%d %H:%M:%S')}.")
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)
