# type: ignore
import io
from nextcord import IntegrationType, Interaction, InteractionContextType, SlashOption, slash_command, Embed
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
import asyncio
import socket

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

def sync_is_tcp_port_open(ip_address: str, port: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        if sock.connect_ex((ip_address, port)) == 0:
            return "Open"
        else:
            return "Closed"
    except socket.gaierror:
        return "Hostname could not be resolved"
    except socket.error:
        return "Connection Error"
    finally:
        sock.close()

def sync_is_udp_port_open(ip_address: str, port: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    try:
        sock.sendto(b'', (ip_address, port))
        sock.recvfrom(1024)
        return "Open (Responded)"
    except socket.timeout:
        return "Open or Filtered"
    except ConnectionRefusedError:
        return "Closed (Connection Refused)"
    except socket.gaierror:
        return "Hostname could not be resolved"
    except socket.error:
        return "Connection Error"
    finally:
        sock.close()

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
            await interaction.send(
                f"Current local time for <@{user_id}> is {current_time_local.strftime('%Y-%m-%d %H:%M:%S')}.{diff_str}"
            )
        except Exception as e:
            await interaction.send(f"An error occured.\n```bash\n{e}```")
            print(e)

    @slash_command(
        description="Check the status of a network port.",
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
    async def portstatus(self,
                         interaction: Interaction[Bot],
                         ip_address: str = nextcord.SlashOption(
                            description="IP address or hostname to scan.",
                            required=True
                        ),
                        port: int = nextcord.SlashOption(
                            description="Port number to check.",
                            required=True
                        )):
        await interaction.response.defer()

        loop = asyncio.get_event_loop()

        tcp_task = loop.run_in_executor(None, sync_is_tcp_port_open, ip_address, port)
        udp_task = loop.run_in_executor(None, sync_is_udp_port_open, ip_address, port)

        tcp_result_str = await tcp_task
        udp_result_str = await udp_task

        embed = nextcord.Embed(
            title="Port Scan Results",
            description=f"Showing status for `{ip_address}:{port}`",
            color=0x3498DB
        )

        if "Open" in tcp_result_str:
            tcp_status = f"✅ {tcp_result_str}"
        elif "Closed" in tcp_result_str:
            tcp_status = f"❌ {tcp_result_str}"
        else:
            tcp_status = f"⚠️ {tcp_result_str}"

        if "Open" in udp_result_str:
            udp_status = f"✅ {udp_result_str}"
        elif "Closed" in udp_result_str:
            udp_status = f"❌ {udp_result_str}"
        else:
            udp_status = f"⚠️ {udp_result_str}"

        embed.add_field(name="TCP Status", value=tcp_status, inline=True)
        embed.add_field(name="UDP Status", value=udp_status, inline=True)
        embed.set_footer(text=f"Scan requested by {interaction.user.name}")

        await interaction.followup.send(embed=embed)

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
                print(formatted)
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

            if meow.status_code == 200:
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
