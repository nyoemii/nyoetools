import discord
import os
import dotenv
import logging
from discord.ext import commands
from discord import app_commands

# Suppress discord.py verbose logging
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='nt!', intents=intents)

dotenv.load_dotenv()
token = os.environ["BOT_TOKEN"]

print('=' * 50)
print('🚀 Bot starting...')
print('=' * 50)

@bot.event
async def on_connect():
    print('✓ Connected to Discord')

@bot.event
async def on_ready():
    # Load all cogs from the cogs directory
    await load_cogs()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'✓ Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'✗ Failed to sync commands: {e}')

    print('\n' + '=' * 50)
    print(f'✨ {bot.user.name} is online! ✨')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} server(s)')
    print('=' * 50)
    print()

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        # Handle missing required arguments
        param_name = error.param.name
        await ctx.send(f"❌ You're missing a required argument: `{param_name}`\n"
                      f"Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.MissingRequiredAttachment):
        # Handle missing required file attachments
        param_name = error.param.name
        command_name = ctx.command.name if ctx.command else "this command"
        
        # Provide specific messages for different commands
        if command_name == "replayinfo":
            await ctx.send(f"❌ You need to attach an osu! replay file (.osr) for this command.\n"
                          f"Usage: `{ctx.prefix}{command_name}` (attach .osr file)")
        elif command_name == "ocr":
            await ctx.send(f"❌ You need to attach an image file for this command.\n"
                          f"Usage: `{ctx.prefix}{command_name}` (attach image)")
        else:
            await ctx.send(f"❌ You need to attach a file for `{command_name}`.\n"
                          f"Missing parameter: `{param_name}`")
    elif isinstance(error, commands.BadArgument):
        # Handle bad arguments (wrong type, etc.)
        await ctx.send(f"❌ Invalid argument provided.\n"
                      f"Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandNotFound):
        # Silently ignore command not found errors
        pass
    elif isinstance(error, commands.CommandInvokeError):
        # Handle errors that occur during command execution
        original = error.original
        print(f"Error in command {ctx.command}: {original}")
        await ctx.send(f"❌ An error occurred while executing the command.")
    else:
        # Log other errors
        print(f"Unhandled error: {error}")
        await ctx.send(f"❌ An unexpected error occurred.")

async def load_cogs():
    """Load all cog files from the cogs directory"""
    import pathlib
    cogs_dir = pathlib.Path(__file__).parent / 'cogs'
    
    for filepath in cogs_dir.glob('*.py'):
        if filepath.name.startswith('_'):
            continue
        
        cog_name = f'cogs.{filepath.stem}'
        try:
            await bot.load_extension(cog_name)
            print(f'✓ Loaded cog: {cog_name}')
        except Exception as e:
            print(f'✗ Failed to load cog {cog_name}: {e}')


bot.run(token)