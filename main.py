"""
Main file for the Shiritori Bot
Handles bot startup and Cog loading
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ShiritoriBot(commands.Bot):
    """Shiritori Bot class"""
    
    def __init__(self):
        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True  # Enable message content access
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix='!',  # Prefix (low usage frequency as slash commands are main)
            intents=intents,
            help_command=None  # Disable default help command
        )
    
    async def setup_hook(self):
        """Initial setup during bot startup"""
        # Load Cogs
        try:
            await self.load_extension('cogs.shiritori_cog')
            print("✅ Loaded Shiritori Cog")
        except Exception as e:
            print(f"❌ Failed to load Cog: {e}")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f"🤖 Logged in as {self.user}")
        print(f"📝 Bot ID: {self.user.id}")
        print(f"🔗 Invite URL: https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=274877908992&scope=bot%20applications.commands")
        print("🎯 Shiritori bot has started!")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.playing, 
            name="しりとり | /help for details"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore non-existent commands
        
        print(f"❌ Command error: {error}")
        
        if ctx.channel:
            await ctx.send(f"An error occurred: {error}")


async def main():
    """Main function"""
    # Check environment variables
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ DISCORD_BOT_TOKEN is not set.")
        print("📝 Please set the token in the .env file.")
        return
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY is not set.")
        print("📝 Please set the Gemini API key in the .env file.")
        return
    
    # Start the bot
    bot = ShiritoriBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ Discord login failed. Please check your token.")
    except Exception as e:
        print(f"❌ An error occurred during bot startup: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    # Avoid event loop issues on Windows
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
