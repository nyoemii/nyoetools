import os
import nextcord
from nextcord.ext.commands import Bot
from cogs import Eval, Fun, Misc, Poll, Utils

bot_token = os.environ["BOT_TOKEN"]

with open("/app/ff.json", 'w', encoding="ascii") as ffconfig:
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
bot.run(bot_token)