# type: ignore
import os
import nextcord
from nextcord.ext.commands import Bot
from cogs import Eval, Fun, Misc, Utils, OsuReplayData, DeutscheBahn, OsuTracking
from time import gmtime, strftime

from cogs.osu import OsuBeatmapConverter

bot_token = os.environ["BOT_TOKEN"]

with open("/app/config.jsonc", 'w', encoding="ascii") as ffconfig:
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

losers = [1088593923661893703, 574669003755356162, 1079578703295696917, 820294242659205120, 335468199497695232, 510651129328304138, 171024905536536576]

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = Bot(intents=intents)

print('=' * 50)
print('🚀 Bot starting...')
print('=' * 50)

@bot.event
async def on_connect():
    print('✓ Connected to Discord')

@bot.event
async def on_ready():
    await bot.sync_all_application_commands()

    print('\n' + '=' * 50)
    print(f'✨ {bot.user.name} is online! ✨')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} server(s)')
    print('=' * 50)

    osu_cog = bot.get_cog('OsuTracking')
    if osu_cog:
        print('✓ OsuTracking cog found')
        if not osu_cog.token:
            print('  Getting token...')
            osu_cog.token = await osu_cog.get_token()
            print(f'  Token obtained: {osu_cog.token[:20]}...')
        
        if not osu_cog.check_scores.is_running():
            print('  Starting loop...')
            osu_cog.check_scores.start()
            print(f'  Loop started: {osu_cog.check_scores.is_running()}')
        else:
            print('  Loop already running')
    else:
        print('✗ OsuTracking cog NOT found!')
    
    print('\n📦 Loaded Cogs:')
    for cog_name in bot.cogs:
        print(f'  ✓ {cog_name}')
    print('=' * 50)
    print()

print('\n🔄 Loading cogs...')
bot.add_cog(Eval(bot))
bot.add_cog(Fun(bot))
bot.add_cog(Misc(bot))
bot.add_cog(Utils(bot))
bot.add_cog(OsuBeatmapConverter(bot))
bot.add_cog(DeutscheBahn(bot))
bot.add_cog(OsuReplayData(bot))
bot.add_cog(OsuTracking(bot))
print()
print('=' * 50)
bot.run(bot_token)
