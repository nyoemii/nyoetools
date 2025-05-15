import nextcord
import requests
import aiohttp
import datetime
import os
import random
import sys
import textwrap
import traceback
import io
import resource
import psutil
import logging
import asyncio
import pytz
import qrcode
import sh
import subprocess

from datetime import datetime, timedelta
from pytz import timezone
from dotenv import load_dotenv
from nextcord.ext import commands, tasks
from nextcord import Embed
from nextcord import IntegrationType, Interaction, InteractionContextType
from collections import defaultdict

load_dotenv()

newsapikey = os.environ["NEWS_API_KEY"]
bot_token = os.environ["BOT_TOKEN"]

TIMEZONE = pytz.timezone('Europe/Berlin') # or your own timezone (still broken)

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(intents=intents)

poll_votes = defaultdict(dict)

class PollButton(nextcord.ui.Button):
    def __init__(self, poll_id: str, option_idx: int, label: str):
        super().__init__(
            label=f"{label} (0)",
            custom_id=f"poll_{poll_id}_{option_idx}",
            style=nextcord.ButtonStyle.blurple
        )
        self.poll_id = poll_id
        self.option_idx = option_idx
        self.original_label = label

    async def callback(self, interaction: nextcord.Interaction):
        poll_votes[self.poll_id][interaction.user.id] = self.option_idx
        
        vote_counts = [0] * 4
        for vote in poll_votes[self.poll_id].values():
            vote_counts[vote] += 1

        new_view = nextcord.ui.View(timeout=None)
        for idx in range(len(vote_counts)):
            if idx >= len(self.view.children):
                continue

            new_button = PollButton(
                poll_id=self.poll_id,
                option_idx=idx,
                label=self.view.children[idx].original_label
            )
            new_button.label = f"{new_button.original_label} ({vote_counts[idx]})"
            if vote_counts[idx] == max(vote_counts):
                new_button.style = nextcord.ButtonStyle.green
            new_view.add_item(new_button)

        total_votes = sum(vote_counts)
        embed = interaction.message.embeds[0]
        embed.description = f"**Total Votes**: {total_votes}\n\n" + "\n".join(
            f"{self.view.children[i].original_label}: {vote_counts[i]} vote{'s' if vote_counts[i] != 1 else ''}"
            for i in range(len(self.view.children))
        )

        await interaction.response.edit_message(embed=embed, view=new_view)

def memory_limit(limit_in_mb: int):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_in_mb * 1024 *1024, hard))

def memory_usage():
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

class EvalFilter(logging.Filter):
    def filter(self, record):
        return "Cleaning up" not in record.getMessage()

class TimeFormat(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, TIMEZONE)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

for handler in logging.root.handlers:
    handler.setFormatter(TimeFormat())

nextcord_logger = logging.getLogger("nextcord")
nextcord_logger.addFilter(EvalFilter())

@bot.slash_command(
    description="Replies with Pong!",
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
async def ping(interaction: Interaction):
    latency: float = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"Pong! {latency} ms • Memory usage: {round(memory_usage(), 2)} MB", ephemeral=False)

@bot.slash_command(
    description="oooo dangerous",
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
async def eval(interaction: nextcord.Interaction, *, code: str) -> None:
    """A dangerous command to run Python Code and return the result"""
    logging.basicConfig(filename="eval_logs.txt", level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
    TRUSTED_USERS = {} # add your own user id(s)
    TRUSTED_TRUSTED_USERS = {}

    if interaction.user.id not in TRUSTED_USERS:
        logging.warning(f"WARNING - User {interaction.user.name} ({interaction.user.id}) tried to execute {code}")
        print(f"WARNING - User {interaction.user.name} ({interaction.user.id}) tried to execute {code}")
        await interaction.send(f"User {interaction.user.name} was hoping to evaluate code :c")
        return

    if interaction.user.id not in TRUSTED_TRUSTED_USERS:
        if any(keyword in code.lower() for keyword in ["for x in", "os.environ", "os.system", "eval(", "exec(", "shutil", "import os;", "builtins", "getattr", ".system", "__import__", "sys", "version_info", "shutdown", "rm -rf"]):
            logging.warning(f"CODE LOG - User {interaction.user.name} tried to execute:\n{code}")
            print(f"CODE LOG - User {interaction.user.name} tried to execute:\n{code}")
            await interaction.send("Dangerous Code found!")
            return
    
    if any(keyword in code.lower() for keyword in ["shutdown", "restart"]):
        logging.warning(f"CODE LOG - User {interaction.user.name} tried to execute:\n{code}")
        print(f"CODE LOG - User {interaction.user.name} tried to execute:\n{code}")
        await interaction.send("Dangerous Code found!")
        return

    memory_limit(1024)

    start_time = datetime.now(TIMEZONE)

    exec_namespace = {**globals(), **locals(), **{mod.__name__: mod for mod in sys.modules.values()}}

    # Indent the code for the async function
    indented_code = textwrap.indent(textwrap.dedent(code), '    ')
    wrapped_code = f"""
async def _execute():
{indented_code}
"""

    try:
        output = io.StringIO()
        sys.stdout = output
        # Execute the wrapped code
        exec(wrapped_code, exec_namespace)
        # Await the result of the async function
        result = await asyncio.wait_for(exec_namespace["_execute"](), timeout=5.0)

        exec_time = (datetime.now(TIMEZONE) - start_time).total_seconds()

        logging.info(f"SUCCESS - User {interaction.user.name} ({interaction.user.id}) executed {code} - Executed in {exec_time:.3f}s")
        # Send the result to the channel
        sys.stdout = sys.__stdout__
        captured_output = output.getvalue().strip()
        await interaction.response.defer()
        await interaction.send(captured_output)
    except Exception:
        # Send the error traceback to the channel
        await interaction.response.defer()
        await interaction.send(f"ˋˋˋbash\nError: {traceback.format_exc()}ˋˋˋ")

@bot.slash_command(
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
async def news(interaction: nextcord.Interaction, category: str):
    try:
        await interaction.response.defer()
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
                target_tz = timezone('Europe/Berlin')
                cest_date = parse_date.replace(tzinfo=timezone('UTC')).astimezone(target_tz)
                publish_date = cest_date.strftime("%B %d, %Y, %I:%M %p %Z")

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

@bot.slash_command(
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
async def createqr(interaction: nextcord.Interaction, input: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(input)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    file = nextcord.File(buf, filename="qrcode.png")
    await interaction.response.defer()
    await interaction.send(file=file)

@bot.slash_command(
    description="Gives Credits to the People helping and developing",
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
async def credits(interaction: nextcord.Interaction):
    embed = nextcord.Embed(
                title="Credits",
                color=nextcord.Color.blue()
            )

    embed.add_field(name="Developer", value="[nyoemii](https://nyoemii.dev)", inline=True)
    embed.add_field(name="Testers", value="[Mineek](https://github.com/mineek)\n[omardotdev](https://omardotdev.github.io)", inline=True)

    await interaction.send(embed=embed)

@bot.slash_command(
    description="Makes a Poll",
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
async def poll(interaction: nextcord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
    options = [opt for opt in [option1, option2, option3, option4] if opt is not None]
    poll_id = str(interaction.id)

    view = nextcord.ui.View(timeout=None)
    for idx, option in enumerate(options):
        view.add_item(PollButton(
            poll_id=poll_id,
            option_idx=idx,
            label=option
        ))

    embed = nextcord.Embed(
        title=f"Poll: {question}",
        description="\n".join(f"• {opt}" for opt in options),
        color=0x5865F2
    )
    embed.set_footer(text="Enter your vote by using the buttons below!")

    await interaction.response.send_message(embed=embed, view=view)

@bot.slash_command(
    description="Fastfetch :3",
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
async def fastfetch(interaction: nextcord.Interaction):
    os.system("/home/linuxbrew/.linuxbrew/bin/termshot --filename /path/to/output -- 'fastfetch --config /home/nyoemi/.config/fastfetch/config.jsonc'")

    file = "" # set where the file is put in

    await interaction.response.defer()
    await interaction.send(file=nextcord.File(file))

@bot.slash_command(
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
async def github(interaction: nextcord.Interaction, repo: str, user: str, commitname: str):
    base_url = f"https://api.github.com/repos/"
    query = ""
    user_id = interaction.user.id
    username = interaction.user.name

    query += f"{user}/{repo}/commits/{commitname}"
    
    try:
        await interaction.response.defer()
        response = requests.get(base_url + query)

        if response.status_code == 200:
            data = response.json()

            commit = data['commit']
            author = data['author']
            files = data['files']

            git_commit_hash = data.get("sha", {})
            git_message = commit.get("message", "No message attached.")
            git_avatar = author.get("avatar_url", {})
            git_profile = author.get("html_url", {})
                        
        else:
            await interaction.send("GitHub Repo not found.")
        
        embed = nextcord.Embed(
            title=f"Information about {repo}",
            description=f"by {user}",
            color=nextcord.Color.green()
        )

        embed.add_field(name="Commit Hash", value=f"[{git_commit_hash}](https://github.com/{user}/{repo}/commits/{git_commit_hash})", inline=False)
        embed.add_field(name="Message: ", value=f"{git_message}", inline=False)
        embed.set_author(name=f"{user}", url=f"{git_profile}", icon_url=f"{git_avatar}")
        embed.set_footer(icon_url="https://github.githubassets.com/assets/GitHub-Mark-ea2971cee799.png", text=f"Command ran by {username}")

        await interaction.send(embed=embed)
    except Exception:
        await interaction.send("An error occured.")
    except requests.HTTPError:
        await interaction.send(f"Error accessing GitHub: {response.status_code}")

@bot.slash_command(
    description=":trol:",
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
async def osu(interaction: nextcord.Interaction, clip: str = SlashOption(
    choices={}, # your choices go here, written like this: {"option_name": "file_name", "option_name2": "file_name2"}
    ),
):
    try:
        file = f"{clip}"
        await interaction.response.defer()
        await interaction.send(file=nextcord.File(file))
    except Exception:
        await interaction.send("Error: File not found")


@bot.event
async def on_ready():
    await bot.sync_application_commands()
    print("We ball")

bot.run(bot_token)
"""
KEEP THIS HERE AT ALL COSTS
@bot.slash_command(
    description="oooo dangerous",
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
"""
