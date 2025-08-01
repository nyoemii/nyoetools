# type: ignore
import os
import nextcord
from nextcord.ext.commands import Bot
from cogs import Eval, Fun, Misc, Poll, Utils
from time import gmtime, strftime

from cogs.osu import OsuBeatmapConverter

path = "/home/nyoemii/userapp/config.jsonc"

# windows development is real
if os.name == "nt":
    import dotenv
    dotenv.load_dotenv()

    path = "tests/config.jsonc"

bot_token = os.environ["BOT_TOKEN"]

with open(path, 'w', encoding="ascii") as ffconfig:
    ffconfig.write("""
{
  "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "modules": [
    "break",
    "break",
    "title",
    "separator",
    "os",
    "host",
    "kernel",
    "uptime",
    "packages",
    "shell",
    "terminal",
    "terminalfont",
    "cpu",
    "memory",
    "swap",
    "disk",
    "separator"
  ]
}
""")

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = Bot(intents=intents)

print("Bot starting.")

@bot.event
async def on_connect():
    print("Connected.")

@bot.event
async def on_ready():
    await bot.sync_all_application_commands()
    print("We ball")

bot.add_cog(Eval(bot))
bot.add_cog(Fun(bot))
bot.add_cog(Misc(bot))
bot.add_cog(Poll(bot))
bot.add_cog(Utils(bot))
bot.add_cog(OsuBeatmapConverter(bot))
bot.run(bot_token)
