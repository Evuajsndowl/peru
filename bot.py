import os
import asyncio
from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands

import aiohttp
from aiohttp import web

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
POLL_SECONDS = 30

# ================= BOT SETUP =================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ================= OWNER CHECK =================
def is_owner(user_id: int) -> bool:
    return BOT_OWNER_ID != 0 and user_id == BOT_OWNER_ID

async def deny_if_not_owner(interaction: discord.Interaction) -> bool:
    if is_owner(interaction.user.id):
        return False
    await interaction.response.send_message(
        "❌ Owner-only command.",
        ephemeral=True
    )
    return True

# ================= CHANNEL HELPER =================
async def get_text_channel(channel_id: int) -> discord.TextChannel:
    if not channel_id:
        raise RuntimeError("SOURCE_CHANNEL_ID not set.")
    ch = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    if not isinstance(ch, discord.TextChannel):
        raise RuntimeError("Source channel is not a text channel.")
    return ch

# ================= IMAGE FINDER =================
intents = discord.Intents.default()
intents.message_content = True  # REQUIRED to read message content

bot = commands.Bot(command_prefix="!", intents=intents)

# Get environment variables (host sets these)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "0"))

# Store last checked message ID to avoid re-checking everything
last_checked_id = None


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_channel.start()


@tasks.loop(seconds=45)
async def check_channel():
    global last_checked_id

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None:
        print("Channel not found.")
        return

    try:
        # Fetch recent messages (limit adjustable if needed)
        async for message in channel.history(limit=50, after=discord.Object(id=last_checked_id) if last_checked_id else None):
            
            # Skip bot's own messages
            if message.author.bot:
                continue

            # If message contains image attachments, skip
            has_image = False
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    has_image = True
                    break

            if has_image:
                continue

            # Delete non-image messages
            try:
                await message.delete()
                print(f"Deleted message from {message.author}")
            except discord.Forbidden:
                print("Missing permissions to delete messages.")
            except discord.HTTPException:
                print("Failed to delete message.")

            # Update last checked ID
            last_checked_id = message.id

    except Exception as e:
        print(f"Error while checking channel: {e}")
# ================= KEEP-ALIVE WEB SERVER =================
async def handle(request):
    return web.Response(text="OK")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= MAIN =================
async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set.")
    await start_web()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
