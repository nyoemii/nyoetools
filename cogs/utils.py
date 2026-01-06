# type: ignore
import base64
import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Union

import deepl
import discord
from discord import app_commands
from discord.ext import commands
import pytz
import requests
import pytesseract
import io
import dns.resolver
import whois
from openai import OpenAI
from requests import HTTPError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image

tld_cache = {}

def is_valid_tld(tld):
    """Check if a TLD exists by querying DNS for its nameservers"""
    # Check cache first
    if tld in tld_cache:
        return tld_cache[tld]
    
    try:
        # Try to get the NS (nameserver) records for the TLD
        # If it exists, it will have nameservers
        dns.resolver.resolve(tld + '.', 'NS')
        tld_cache[tld] = True
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        # TLD doesn't exist
        tld_cache[tld] = False
        return False
    except Exception:
        # If there's any other error, assume it might exist (be cautious)
        return True

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

    analysis = {"total_bytes": total_bytes, "languages": {}}

    for language, bytes_count in languages_data.items():
        percentage = (bytes_count / total_bytes) * 100
        analysis["languages"][language] = {
            "bytes": bytes_count,
            "percentage": round(percentage, 2),
        }

    return analysis


async def fix_pixiv(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("pixiv.net", "phixiv.net")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


async def fix_reddit(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("reddit.com", "rxddit.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


async def fix_twitter(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("x.com", "twitter.com")
    link = link.replace("twitter.com", "fxtwitter.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


async def fix_tiktok(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("tiktok.com", "tt.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


async def fix_insta(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("instagram.com", "i.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


async def fix_bsky(message: discord.Message, link: str):
    link = link.replace("www.", "")
    link = link.replace("bsky.app", "b.embewd.com")

    await message.reply(f"{link}", mention_author=False)
    await message.edit(suppress=True)


encodings = {
    "Base16": 'base64.b16encode("{0}".encode("utf-8")).decode("utf-8")',
    "Base32": 'base64.b32encode("{0}".encode("utf-8")).decode("utf-8")',
    "Base64": 'base64.b64encode("{0}".encode("utf-8")).decode("utf-8")',
    "Base85": 'base64.b85encode("{0}".encode("utf-8")).decode("utf-8")',
    "HEX": 'bytes.hex("{0}".encode("utf-8"))',
}
decodings = {
    "Base16": 'base64.b16decode("{0}".encode("utf-8")).decode("utf-8")',
    "Base32": 'base64.b32decode("{0}".encode("utf-8")).decode("utf-8")',
    "Base64": 'base64.b64decode("{0}".encode("utf-8")).decode("utf-8")',
    "Base85": 'base64.b85decode("{0}".encode("utf-8")).decode("utf-8")',
    "HEX": 'bytes.fromhex("{0}").decode("utf-8")',
}


class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.twitter_pattern = re.compile(
            r"(https://(www.)?(twitter|x)\.com/[a-zA-Z0-9_]+/status/[0-9]+)"
        )
        self.pixiv_pattern = re.compile(
            r"(https://(www.)?(pixiv)\.net/en/artworks/[0-9]+)"
        )
        self.reddit_pattern = re.compile(
            r"(https://(www.)?(reddit)\.com/r/[^/]+/(?:comments|s)/[a-zA-Z0-9]+/?)"
        )
        self.insta_pattern = re.compile(
            r"https?:\/\/(www\.)?instagram\.com\/(p\/[a-zA-Z0-9_-]+|reel\/[a-zA-Z0-9_-]+|[a-zA-Z0-9._-]+)\/?(\?[^\s]*)?"
        )
        self.bsky_pattern = re.compile(r"https?:\/\/bsky\.app\/[^\s]+")
        self.tiktok_pattern = re.compile(
            r"^.*https:\/\/(?:m|www|vm)?\.?tiktok\.com\/((?:.*\b(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+))|\w+)\/.*"
        )

    @commands.hybrid_command(
        name="sync",
        description="Sync Command (Owner Only)"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def sync(self, ctx: commands.Context):
        if not ctx.author or ctx.author.id == 277830029399031818:
            print("=" * 50)
            print("Synchronizing Slash Commands, Please wait.")
            print("=" * 50)
            await ctx.defer()
            await self.bot.tree.sync()
            await ctx.send("Successfully synchronized Slash Commands.")
        else:
            await ctx.send("Missing permissions.", ephemeral=True)

    @commands.hybrid_command(
        name="github",
        description="Get latest Commit of a specified GitHub Repo"
    )
    @app_commands.describe(
        repo="Repository name",
        user="GitHub username",
        commitname="Commit SHA or branch name"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def github(
        self, ctx: commands.Context, repo: str, user: str, commitname: str
    ):
        usre = ctx.author
        userpfp = usre.avatar

        if not ctx.author:
            return
        base_url = "https://api.github.com/repos/"
        query = ""
        username = ctx.author.name

        query += f"{user}/{repo}/commits/{commitname}"

        await ctx.defer()

        response = None
        try:
            response = requests.get(base_url + query, timeout=10)

            if response.status_code == 200:
                data = response.json()

                commit = data["commit"]
                author = data["author"]

                git_commit_hash = data.get("sha", {})
                git_message = commit.get("message", "No message attached.")
                git_avatar = author.get("avatar_url", {})
                git_profile = author.get("html_url", {})

            else:
                await ctx.send("GitHub Repo not found.")
                return

            embed = (
                discord.Embed(
                    title=f"Information about {repo} by {user}",
                    color=discord.Color.green(),
                )
                .add_field(
                    name="Commit Hash",
                    value=f"[{git_commit_hash}](https://github.com/{user}/{repo}/commits/{git_commit_hash})",
                    inline=False,
                )
                .add_field(name="Message: ", value=f"{git_message}", inline=False)
                .set_author(
                    name=f"{user}", url=f"{git_profile}", icon_url=f"{git_avatar}"
                )
                .set_footer(icon_url=userpfp.url if userpfp else None, text=f"Command ran by {username}")
            )

            await ctx.send(embed=embed)
            return
        except HTTPError:
            await ctx.send(
                f"Error accessing GitHub: {response.status_code if response is not None else 'Unknown Error'}"
            )
            return
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            return

    @commands.hybrid_command(
        name="ghcode",
        description="Get languages from a GitHub repo"
    )
    @app_commands.describe(
        repo="Repository name",
        user="GitHub username"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ghcode(self, ctx: commands.Context, repo: str, user: str):
        usre = ctx.author
        userpfp = usre.avatar
        if not ctx.author:
            return
        username = ctx.author.name
        await ctx.defer()

        try:
            languages = get_repo_languages(user, repo)
            if languages:
                analysis = analyze_languages(languages)
                sorted_langs = sorted(
                    analysis["languages"].items(),
                    key=lambda x: x[1]["percentage"],
                    reverse=True,
                )

                # Build the message content
                message_parts = [f"The repository **{repo}** by **{user}** contains:"]
                message_parts.append("```")

                for language, data in sorted_langs:
                    message_parts.append(
                        f"{language}: {data['bytes']:,} bytes ({data['percentage']}%)"
                    )

                message_parts.append("```")

                # Join all parts into a single message
                final_message = "\n".join(message_parts)

                # Send the single message
                await ctx.send(final_message)

            else:
                await ctx.send(
                    f"❌ Could not retrieve language data for **{user}/{repo}**. Please check if the repository exists and is public."
                )

        except Exception as e:
            await ctx.send(f"❌ Error:\n```bash\n{e}```")

    @commands.hybrid_command(
        name="mcname",
        description="Checks if a Minecraft Name is available"
    )
    @app_commands.describe(username="The Minecraft username to check")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def mcname(self, ctx: commands.Context, username: str):
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"

        try:
            await ctx.defer()
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                if "name" in data:
                    await ctx.send(
                        f"The username `{data['name']}` is already taken."
                    )
                else:
                    await ctx.send("Unexpected response from Mojang's API.")
            elif len(username) < 3 or len(username) > 16:
                await ctx.send(
                    f"The username `{username}` is not available because it is too {'long' if len(username) > 16 else 'short'}."
                )
            else:
                data = response.json()
                if (
                    "errorMessage" in data
                    and "Couldn't find any profile" in data["errorMessage"]
                ):
                    await ctx.send(f"The username `{username}` is available!")
                else:
                    await ctx.send(
                        f"Error checking username: {data.get('errorMessage', 'Unknown error')}"
                    )
        except Exception as e:
            await ctx.send("Error: Logs")
            print(e)

    @commands.hybrid_command(
        name="avatar",
        description="Grabs a Users Avatar if possible."
    )
    @app_commands.describe(user="The user whose avatar to get")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(
        self,
        ctx: commands.Context,
        user: Optional[Union[discord.User, discord.Member]] = None,
    ):
        await ctx.defer()

        try:
            if user is None:
                user = ctx.author
            if user is None:
                await ctx.send("Failed to get user!")
                return

            userpfp = user.avatar
            if userpfp is None:
                await ctx.send("user.avatar was None!")

            embed = discord.Embed(
                title=f"{user.name}'s Avatar", color=0x0000FF, timestamp=datetime.now()
            )

            embed.set_image(url=userpfp.url)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @commands.hybrid_command(
        name="encode",
        description="Encodes your message into various types."
    )
    @app_commands.describe(
        message="Message to encode",
        method="Encoding method"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.choices(method=[
        app_commands.Choice(name=k, value=k) for k in encodings.keys()
    ])
    async def encode(
        self,
        ctx: commands.Context,
        message: str,
        method: str,
    ):
        await ctx.defer()

        try:
            encoded_message = eval(encodings[method].format(message))
            await ctx.send(f"```\n{encoded_message}\n```")
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @commands.hybrid_command(
        name="decode",
        description="Decodes your message into various types."
    )
    @app_commands.describe(
        message="Message to decode",
        method="Decoding method"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.choices(method=[
        app_commands.Choice(name=k, value=k) for k in decodings.keys()
    ])
    async def decode(
        self,
        ctx: commands.Context,
        message: str,
        method: str,
    ):
        await ctx.defer()

        try:
            decoded_message = eval(decodings[method].format(message))

            await ctx.send(f"```\n{decoded_message}\n```")
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @commands.hybrid_command(
        name="settimezone",
        description="Sets your timezone."
    )
    @app_commands.describe(timezone="Your timezone (e.g., Europe/Berlin)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def settimezone(self, ctx: commands.Context, timezone: str):
        await ctx.defer()

        if timezone not in pytz.all_timezones:
            await ctx.send(
                f"`{timezone}` is an invalid timezone. It needs to be formatted like this: `Europe/Berlin`"
            )
            return

        try:
            user_id = ctx.author.id
            username = ctx.author.name
            users_file = "/root/noemi/nyoetools.py/users.json"
            
            # Create file if it doesn't exist
            if not os.path.exists(users_file):
                with open(users_file, "w") as f:
                    json.dump({}, f)
            
            with open(users_file, "r") as f:
                users = json.load(f)
            users[str(user_id)] = {"timezone": timezone}
            with open(users_file, "w") as f:
                json.dump(users, f, indent=4)
            await ctx.send(f"Set timezone to {timezone} for user {username}.")
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @commands.hybrid_command(
        name="time",
        description="Gets the current time based on your set timezone."
    )
    @app_commands.describe(user="User to check time for (defaults to yourself)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def time(
        self,
        ctx: commands.Context,
        user: Optional[Union[discord.User, discord.Member]] = None,
    ):
        await ctx.defer()

        try:
            if user is None:
                user_id = ctx.author.id
            else:
                user_id = user.id
            
            users_file = "/root/noemi/nyoetools.py/users.json"
            if not os.path.exists(users_file):
                with open(users_file, "w") as f:
                    json.dump({}, f)
            
            with open(users_file, "r") as f:
                users = json.load(f)
            if str(user_id) not in users:
                await ctx.send(
                    f"Please set your timezone using `/settimezone <timezone>`{f', {user.mention}' if user else ''}."
                )
                return
            timezone = users[str(user_id)]["timezone"]
            current_time = datetime.now(pytz.timezone(timezone))
            current_time_local = current_time.astimezone(pytz.timezone(timezone))
            command_timezone = users.get(str(ctx.author.id), {}).get("timezone")
            diff_str = ""
            if command_timezone and command_timezone != timezone:
                now_utc = datetime.utcnow()
                user_offset = pytz.timezone(timezone).utcoffset(now_utc)
                command_offset = pytz.timezone(command_timezone).utcoffset(now_utc)
                if user_offset is not None and command_offset is not None:
                    time_diff = (user_offset - command_offset).total_seconds() / 3600
                    if abs(time_diff) >= 0.05:
                        diff_str = (
                            f" (Difference: {time_diff:+.1f} hours from your timezone)"
                        )
            await ctx.send(
                f"Current local time for <@{user_id}> is {current_time_local.strftime('%Y-%m-%d %H:%M:%S')}.{diff_str}"
            )
        except Exception as e:
            await ctx.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @commands.hybrid_command(
        name="urban",
        description="Look for a Term on the Urban Dictionary."
    )
    @app_commands.describe(term="Term to look for")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def urban(
        self,
        ctx: commands.Context,
        term: str,
    ):
        url = f"https://unofficialurbandictionaryapi.com/api/search?term={term}&strict=true&"
        formatted = url.replace(" ", "_")

        try:
            await ctx.defer()
            response = requests.get(formatted)

            if response.status_code == 200:
                data = response.json()

                if "found" in data:
                    result = data["data"][0]

                    word = result["word"]
                    meaning = result["meaning"]
                    example = result["example"]
                    contributor = result["contributor"]
                    date = result["date"]

                    embed = discord.Embed(
                        title="Urban Dictionary Lookup",
                        description=f"Showing the top result for {term}",
                        color=0x3498DB,
                    )

                    embed.set_author(name=contributor)
                    embed.add_field(name="Meaning", value=meaning[:300], inline=False)
                    embed.add_field(
                        name="Example", value=f"`{example[:500]}`", inline=False
                    )
                    embed.set_footer(text=f"Posted on Urban Dictionary on {date}")

                    await ctx.send(embed=embed)

                else:
                    await ctx.send(f"No Search Result for {term}")
            elif response.status_code == 404:
                data = response.json()
                if "message" in data:
                    message = data["message"]
                    formatted2 = message.replace("this word", f"{term}")
                    await ctx.send(formatted2 + ".")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured.\n```bash\n{e}```")

    @commands.hybrid_command(
        name="httpcat",
        description="HTTP Cat Error Code"
    )
    @app_commands.describe(error_code="HTTP error code")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def httpcat(
        self,
        ctx: commands.Context,
        error_code: int,
    ):
        await ctx.defer()
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

                embed = discord.Embed(color=color)

                embed.set_image(url=img)

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"The Error Code `{error_code}` is not valid.")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured.\n```bash\n{e}```")

    @commands.hybrid_command(
        name="mcskin",
        description="Get a Minecraft Skin using the username"
    )
    @app_commands.describe(minecraft_name="Minecraft username")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def mcskin(
        self,
        ctx: commands.Context,
        minecraft_name: str,
    ):
        await ctx.defer()

        try:
            if re.match(r"[a-zA-Z0-9_]", minecraft_name):
                url = f"https://vzge.me/full/384/{minecraft_name}"
            else:
                await ctx.send("Invalid Minecraft Username.")

            embed = discord.Embed(
                title=f"{minecraft_name}'s Skin",
                description=f"[Download Skin](https://mineskin.eu/download/{minecraft_name})",
                color=0x008000,
            )

            embed.set_image(url=url)

            await ctx.send(embed=embed)
        except HTTPError:
            await ctx.send("The API is currently unavailable.")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured:\n```bash\n{e}```")

    @commands.hybrid_command(
        name="screenshot",
        description="Take a screenshot of a website"
    )
    @app_commands.describe(url="Website URL to screenshot")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def screenshot(
        self,
        ctx: commands.Context,
        url: str,
    ):
        # Send initial loading message
        loading_embed = discord.Embed(
            title="📸 Taking Screenshot...",
            description=f"🔄 Loading `{url}`\n\n⏳ Please wait, this may take a few seconds...",
            color=0x5865F2
        )
        loading_msg = await ctx.send(embed=loading_embed)

        driver = None
        try:
            # Validate and format URL
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Configure Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-extensions")

            # Initialize the driver
            driver = webdriver.Chrome(options=chrome_options)

            driver.get(url)

            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Take screenshot
            screenshot_bytes = driver.get_screenshot_as_png()

            screenshot_file = discord.File(
                io.BytesIO(screenshot_bytes), filename="screenshot.png"
            )

            embed = discord.Embed(color=0x5865F2, timestamp=datetime.now())

            embed.set_image(url="attachment://screenshot.png")
            embed.set_footer(
                text=f"Requested by {ctx.author.name}",
                icon_url=ctx.author.avatar.url
                if ctx.author.avatar
                else None,
            )

            await loading_msg.edit(embed=embed, attachments=[screenshot_file])

        except Exception as e:
            print(e)
            error_embed = discord.Embed(
                title="❌ Screenshot Failed",
                description=f"An error occurred while taking the screenshot.",
                color=0xFF0000
            )
            await loading_msg.edit(embed=error_embed)
        finally:
            if driver:
                driver.quit()


    @commands.hybrid_command(
        name="translate",
        description="Translates your text using DeepL."
    )
    @app_commands.describe(
        target_lang="Target language code (EN, DE, FR, ES, IT, PT, RU, JA, ZH)",
        text="Text to translate"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def translate(
        self,
        ctx: commands.Context,
        target_lang: str,
        *,
        text: str,
    ):
        await ctx.defer()

        try:
            # Normalize language code
            target_lang = target_lang.upper()
            if target_lang == "EN":
                target_lang = "EN-US"
            
            deepl_client = deepl.Translator(os.getenv("DEEPL_API_KEY"))
            result = deepl_client.translate_text(text, target_lang=target_lang)

            # Create pretty embed
            embed = discord.Embed(
                title=":DeepL Emoji here: Translation",
                color=0x0B82C4,
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="📝 Original Text", value=f"```\n{text}\n```", inline=False
            )

            embed.add_field(
                name=f"🎯 Translated ({target_lang})",
                value=f"```\n{result.text}\n```",
                inline=False,
            )

            embed.set_footer(
                text=f"Translated using DeepL • Requested by {ctx.author.name}",
                icon_url=ctx.author.avatar.url
                if ctx.author.avatar
                else None,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            print(e)
            error_msg = str(e)
            if "not supported" in error_msg.lower():
                await ctx.send(
                    f"❌ Language code `{target_lang}` is not supported.\n"
                    f"Supported languages: EN, DE, FR, ES, IT, PT, RU, JA, ZH, and more.\n"
                    f"Usage: `{ctx.prefix}translate <lang_code> <text>`"
                )
            else:
                await ctx.send(f"❌ An error occurred during translation.")

    @commands.hybrid_command(
        name="ask",
        description="Ask AI!"
    )
    @app_commands.describe(query="Your question for the AI")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ask(self, ctx: commands.Context, *, query: str):
        await ctx.defer()

        try:
            client = OpenAI(
                api_key=os.environ["GROQ_API_KEY"],
                base_url="https://api.groq.com/openai/v1",
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=1,
                messages=[
                    {
                        "role": "system",
                        "content": "YOUR SYSTEM PROMPT",
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
            )

            responsetext = response.choices[0].message.content

            max_length = 2000

            if len(responsetext) <= max_length:
                await ctx.send(responsetext)
            else:
                chunks = []
                while responsetext:
                    if len(responsetext) <= max_length:
                        chunks.append(responsetext)
                        break
                    
                    split_pos = max_length

                    last_nl = responsetext[:max_length].rfind('\n')
                    if last_nl > max_length - 200:
                        split_pos = last_nl + 1
                    else:
                        last_space = responsetext[:max_length].rfind(' ')
                        if last_space > max_length - 100:
                            split_pos = last_space + 1

                    chunks.append(responsetext[:split_pos])
                    responsetext = responsetext[split_pos:]

                await ctx.send(chunks[0])

                for chunk in chunks[1:]:
                    await ctx.send(chunk)
        
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured:\n```bash\n{e}```")

    @commands.hybrid_command(
        name="ocr",
        description="Use OCR to extract text from an image."
    )
    @app_commands.describe(image="Image to extract text from")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ocr(self, ctx: commands.Context, image: discord.Attachment):
        await ctx.defer()

        try:
            bytes_data = await image.read()

            img = Image.open(io.BytesIO(bytes_data))

            text = pytesseract.image_to_string(img)

            await ctx.send(f"```{text}```")
        except Exception as e:
            print(e)
            await ctx.send(f"An error occured:\n```bash\n{e}```")

    @commands.hybrid_command(
    name="domain",
    description="Check the availability for a Domain"
    )
    @app_commands.describe(domain="Domain to check")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def domain(self, ctx: commands.Context, domain: str):
        await ctx.defer()
        
        # Clean up the domain (remove http://, https://, www.)
        domain = domain.lower().strip()
        domain = re.sub(r'^(https?://)?(www\.)?', '', domain)
        domain = domain.split('/')[0]  # Remove any path
        
        # Validate domain format
        if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$', domain):
            await ctx.send("❌ That doesn't look like a valid domain name format!")
            return
        
        # Extract TLD (everything after the last dot)
        parts = domain.split('.')
        if len(parts) < 2:
            await ctx.send("❌ Please provide a domain with an extension (like .com, .net, etc.)")
            return
        
        # Check for multi-part TLDs like .co.uk
        tld = parts[-1]
        
        # First try single TLD
        if not is_valid_tld(tld):
            # If single TLD doesn't exist, try multi-part (like .co.uk)
            if len(parts) >= 3:
                multi_tld = f"{parts[-2]}.{parts[-1]}"
                if is_valid_tld(multi_tld):
                    tld = multi_tld
                else:
                    await ctx.send(f"❌ `.{parts[-1]}` is not a recognized domain extension!\n"
                                f"Here is a full list of valid TLDs: https://data.iana.org/TLD/tlds-alpha-by-domain.txt")
                    return
            else:
                await ctx.send(f"❌ `.{tld}` is not a recognized domain extension!\n"
                            f"Here is a full list of valid TLDs: https://data.iana.org/TLD/tlds-alpha-by-domain.txt")
                return
        
        # Now check if domain is available
        try:
            dns.resolver.resolve(domain, 'A')
            await ctx.send(f"❌ The domain `{domain}` is already taken.")
        except dns.resolver.NXDOMAIN:
            await ctx.send(f"✅ The domain `{domain}` appears to be available!")
        except dns.resolver.NoAnswer:
            await ctx.send(f"❌ The domain `{domain}` is already taken.")
        except dns.resolver.Timeout:
            await ctx.send(f"⚠️ The request timed out. Try again in a moment!")
        except Exception as e:
            await ctx.send(f"⚠️ Couldn't check the domain. Error:\n```bash\n{e}```")
        

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

async def setup(bot):
    """Required setup function for cog loading"""
    await bot.add_cog(Utils(bot))
