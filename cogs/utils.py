# type: ignore
import io
from nextcord import IntegrationType, Interaction, InteractionContextType, SlashOption, slash_command, Embed, InteractionMessage
import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import Bot, Cog
import requests
from requests import HTTPError
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Union
import base64
import json
import pytz
import deepl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def get_repo_languages(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"

    try:
        response = requests.get(url)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def analyze_languages(languages_data):
    if not languages_data:
        return None

    total_bytes = sum(languages_data.values())

    analysis = {
        'total_bytes': total_bytes,
        'languages': {}
    }

    for language, bytes_count in languages_data.items():
        percentage = (bytes_count / total_bytes) * 100
        analysis['languages'][language] = {
            'bytes': bytes_count,
            'percentage': round(percentage, 2)
        }

    return analysis

async def fix_pixiv(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("pixiv.net", "phixiv.net")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

async def fix_reddit(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("reddit.com", "rxddit.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

async def fix_twitter(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("x.com", "twitter.com")
    link = link.replace("twitter.com", "fxtwitter.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

async def fix_tiktok(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("tiktok.com", "tt.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

async def fix_insta(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("instagram.com", "i.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

async def fix_bsky(message: nextcord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("bsky.app", "b.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)

encodings = {
    "Base16": "base64.b16encode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base32": "base64.b32encode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base64": "base64.b64encode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base85": "base64.b85encode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "HEX": "bytes.hex(\"{0}\".encode(\"utf-8\"))",
}
decodings = {
    "Base16": "base64.b16decode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base32": "base64.b32decode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base64": "base64.b64decode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "Base85": "base64.b85decode(\"{0}\".encode(\"utf-8\")).decode(\"utf-8\")",
    "HEX": "bytes.fromhex(\"{0}\").decode(\"utf-8\")",
}

class Utils(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.twitter_pattern = re.compile(r"(https://(www.)?(twitter|x)\.com/[a-zA-Z0-9_]+/status/[0-9]+)")
        self.pixiv_pattern = re.compile(r"(https://(www.)?(pixiv)\.net/en/artworks/[0-9]+)")
        self.reddit_pattern = re.compile(r"(https://(www.)?(reddit)\.com/r/[^/]+/(?:comments|s)/[a-zA-Z0-9]+/?)")
        self.insta_pattern = re.compile(r"https?:\/\/(www\.)?instagram\.com\/(p\/[a-zA-Z0-9_-]+|reel\/[a-zA-Z0-9_-]+|[a-zA-Z0-9._-]+)\/?(\?[^\s]*)?")
        self.bsky_pattern = re.compile(r"https?:\/\/bsky\.app\/[^\s]+")
        self.tiktok_pattern = re.compile(r"^.*https:\/\/(?:m|www|vm)?\.?tiktok\.com\/((?:.*\b(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+))|\w+)\/.*")

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
            print('=' * 50)
            print("Synchronizing Slash Commands, Please wait.")
            print('=' * 50)
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
        description="Get languages from a GitHub repo",
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
    async def ghcode(
        self,
        interaction: Interaction[Bot],
        repo: str,
        user: str
    ):
        usre = interaction.user
        userpfp = usre.avatar
        if not interaction.user:
            return
        username = interaction.user.name
        await interaction.response.defer()

        try:
            languages = get_repo_languages(user, repo)
            if languages:
                analysis = analyze_languages(languages)
                sorted_langs = sorted(
                    analysis['languages'].items(),
                    key=lambda x: x[1]['percentage'],
                    reverse=True
                )

                # Build the message content
                message_parts = [f"The repository **{repo}** by **{user}** contains:"]
                message_parts.append("```")

                for language, data in sorted_langs:
                    message_parts.append(f"{language}: {data['bytes']:,} bytes ({data['percentage']}%)")

                message_parts.append("```")

                # Join all parts into a single message
                final_message = "\n".join(message_parts)

                # Send the single message
                await interaction.followup.send(final_message)

            else:
                await interaction.followup.send(f"❌ Could not retrieve language data for **{user}/{repo}**. Please check if the repository exists and is public.")

        except Exception as e:
            await interaction.followup.send(f"❌ Error:\n```bash\n{e}```")

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
    async def encode(self, interaction: Interaction[Bot], message: str, method: str = SlashOption(choices=encodings.keys())):
        await interaction.response.defer()

        try:
            encoded_message = eval(encodings[method].format(message))
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
    async def decode(self, interaction: Interaction[Bot], message: str, method: str = SlashOption(choices=decodings.keys())):
        await interaction.response.defer()

        try:
            decoded_message = eval(decodings[method].format(message))

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
            await interaction.send(f"`{timezone}` is an invalid timezone. It needs to be formatted like this: `Europe/Berlin`")
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
            command_timezone = users.get(str(interaction.user.id), {}).get("timezone")
            diff_str = ""
            if command_timezone and command_timezone != timezone:
                now_utc = datetime.utcnow()
                user_offset = pytz.timezone(timezone).utcoffset(now_utc)
                command_offset = pytz.timezone(command_timezone).utcoffset(now_utc)
                if user_offset is not None and command_offset is not None:
                    time_diff = (user_offset - command_offset).total_seconds() / 3600
                    if abs(time_diff) >= 0.05:
                        diff_str = f" (Difference: {time_diff:+.1f} hours from your timezone)"
            await interaction.send(f"Current local time for <@{user_id}> is {current_time_local.strftime('%Y-%m-%d %H:%M:%S')}.{diff_str}")
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Look for a Term on the Urban Dictionary.",
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
    async def urban(self,
                         interaction: Interaction[Bot],
                         term: str = nextcord.SlashOption(
                            description="Term to look for",
                            required=True
                        )):
        url = f"https://unofficialurbandictionaryapi.com/api/search?term={term}&strict=true&"
        formatted = url.replace(" ", "_")

        try:
            await interaction.response.defer()
            response = requests.get(formatted)

            if response.status_code == 200:
                data = response.json()

                if 'found' in data:
                    result = data["data"][0]

                    word = result["word"]
                    meaning = result["meaning"]
                    example = result["example"]
                    contributor = result["contributor"]
                    date = result["date"]

                    embed = nextcord.Embed(
                        title="Urban Dictionary Lookup",
                        description=f"Showing the top result for {term}",
                        color=0x3498DB
                    )

                    embed.set_author(name=contributor)
                    embed.add_field(name="Meaning", value=meaning[:300], inline=False)
                    embed.add_field(name="Example", value=f"`{example[:500]}`", inline=False)
                    embed.set_footer(text=f"Posted on Urban Dictionary on {date}")

                    await interaction.send(embed=embed)

                else:
                    await interaction.send(f"No Search Result for {term}")
            elif response.status_code == 404:
                data = response.json()
                if 'message' in data:
                    message = data["message"]
                    formatted2 = message.replace("this word", f"{term}")
                    await interaction.send(formatted2 + ".")
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured.\n```bash\n{e}```")

    @slash_command(
        description="HTTP Cat Error Code",
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
    async def httpcat(self,
                         interaction: Interaction[Bot],
                         error_code: int = nextcord.SlashOption(
                            description="Error Code",
                            required=True
                        )):
        await interaction.response.defer()
        try:
            img = f"https://http.cat/{error_code}"
            meow = requests.get(img)

            if meow.status_code == 200:
                if error_code == 0:
                    color = 0xFF00FF
                if error_code >= 100 and error_code < 200:
                    color = 0x0000FF
                elif error_code >= 200 and error_code < 300:
                    color = 0x00FF00
                elif error_code >= 300 and error_code < 400:
                    color = 0xFFFF00
                elif error_code == 420:
                    color = 0x008000
                elif error_code >= 400 and error_code < 500:
                    color = 0xFF0000
                elif error_code >= 500 and error_code < 600:
                    color = 0x400000

                embed = nextcord.Embed(
                    color=color
                )

                embed.set_image(url=img)

                await interaction.send(embed=embed)
            else:
                await interaction.send(f"The Error Code `{error_code}` is not valid.")
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured.\n```bash\n{e}```")

    @slash_command(
        description="Get a Minecraft Skin using the username",
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
    async def mcskin(self,
                         interaction: Interaction[Bot],
                         minecraft_name: str = nextcord.SlashOption(
                            description="Minecraft Name",
                            required=True
                        )):
        await interaction.response.defer()

        try:
            if re.match(r'[a-zA-Z0-9_]', minecraft_name):
                url = f"https://vzge.me/full/384/{minecraft_name}"
            else:
                await interaction.send("Invalid Minecraft Username.")

            embed = nextcord.Embed(
                title=f"{minecraft_name}'s Skin",
                description=f"[Download Skin](https://mineskin.eu/download/{minecraft_name})",
                color=0x008000
            )

            embed.set_image(url)

            await interaction.send(embed=embed)
        except HTTPError:
            await interaction.send("The API is currently unavailable.")
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured:\n```bash\n{e}```")

    @slash_command(
        description="Take a screenshot of a website",
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
    async def screenshot(self,
                         interaction: Interaction[Bot],
                         url: str = nextcord.SlashOption(
                            description="Website URL",
                            required=True
                            )):
        await interaction.response.defer()

        driver = None
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-extensions")

            driver = webdriver.Chrome(options=chrome_options)

            driver.get(url)

            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )

            ss_bytes = driver.get_screenshot_as_png()

            ss_file = nextcord.File(
                io.BytesIO(ss_bytes),
                filename="screenshot.png"
            )

            embed = nextcord.Embed(
                color=0x5865F2,
                timestamp=datetime.now()
            )

            embed.set_image(url="attachment://screenshot.png")
            embed.set_footer(
                text=f"Requested by {interaction.user.name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )

            await interaction.send(embed=embed, file=ss_file)

        except Exception as e:
            print(e)
            await interaction.send(f"An error occured while taking a screenshot:\n```bash\n{e}```")
        finally:
            if driver:
                driver.quit()

    @slash_command(
        description="Translates your text using DeepL",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        ],
    async def translate(self,
                        interaction: Interaction[Bot],
                        text: str = nextcord.SlashOption(
                            description="Text to translate",
                            required=True
                        ),
                        target_lang: str = nextcord.SlashOption(
                            description="Target language (e.g., EN, DE, FR)",
                            required=True
                        )):
        await interaction.response.defer()

        try:
            if target_lang == "EN":
                target_lang = "EN-US"

            deepl_client = deepl.DeepLClient(os.getenv("DEEPL_API_KEY"))
            result = deepl_client.translate_text(text, target_lang=target_lang.upper())

            embed = nextcord.Embed(
                title="Translation",
                color=0x0B82C4,
                timestamp=datetime.now()
            )

            embed.add_field(name="Original Text", value=f"```\n{text}\n```", inline=False)
            embed.add_field(name=f"Translated ({target_lang.upper()})", value=f"```\n{result}\n```", inline=False)
            embed.set_footer(
                text=f"Translated using DeepL • Requested by {interaction.user.name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )

            await interaction.send(embed=embed)

        except Exception as e:
            print(e)
            await interaction.send(f"An error occured while translating:\n```bash\n{e}```")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        try:
            message_content = message.content.strip("<>")
            if twitter_match := self.twitter_pattern.search(message_content):
                link = twitter_match.group(0)
                await fix_twitter(message, link)
            elif pixiv_match := self.pixiv_pattern.search(message_content):
                link = pixiv_match.group(0)
                await fix_pixiv(message, link)
            elif reddit_match := self.reddit_pattern.search(message.content):
                link = reddit_match.group(0)
                await fix_reddit(message, link)
            elif insta_match := self.insta_pattern.search(message.content):
                link = insta_match.group(0)
                await fix_insta(message, link)
            elif bsky_match := self.bsky_pattern.search(message.content):
                link = bsky_match.group(0)
                await fix_bsky(message, link)
            elif tiktok_match := self.tiktok_pattern.search(message.content):
                link = tiktok_match.group(0)
                await fix_tiktok(message, link)
        except Exception as e:
            await message.channel.send(f"An error occured:\n`{e}`")
