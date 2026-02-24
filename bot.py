import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from aiohttp import web

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
POLL_SECONDS = 45

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Channel ID set dynamically
target_channel_id = None
last_checked_id = None

# ================= OWNER CHECK =================
def is_owner(user_id: int) -> bool:
    return BOT_OWNER_ID != 0 and user_id == BOT_OWNER_ID

# ================= READY EVENT =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    if not check_channel.is_running():
        check_channel.start()

# ================= SLASH COMMAND =================
@bot.tree.command(name="setchannel", description="Set the channel to monitor (Owner only)")
@app_commands.describe(channel="The channel the bot should monitor")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global target_channel_id, last_checked_id

    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Owner-only command.",
            ephemeral=True
        )
        return

    target_channel_id = channel.id
    last_checked_id = None  # Reset tracker

    await interaction.response.send_message(
        f"✅ Now monitoring {channel.mention}",
        ephemeral=True
    )

# ================= MESSAGE CLEANER LOOP =================
@tasks.loop(seconds=POLL_SECONDS)
async def check_channel():
    global last_checked_id

    if not target_channel_id:
        return

    channel = bot.get_channel(target_channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(target_channel_id)
        except:
            return

    try:
        async for message in channel.history(
            limit=50,
            after=discord.Object(id=last_checked_id) if last_checked_id else None
        ):

            if message.author.bot:
                continue

            # Allow image attachments
            has_image = any(
                attachment.content_type and attachment.content_type.startswith("image")
                for attachment in message.attachments
            )

            if has_image:
                last_checked_id = message.id
                continue

            try:
                await message.delete()
                print(f"Deleted message from {message.author}")
            except discord.Forbidden:
                print("Missing Manage Messages permission.")
            except discord.HTTPException:
                print("Failed to delete message.")

            last_checked_id = message.id

    except Exception as e:
        print(f"Error checking channel: {e}")

# ================= KEEP-ALIVE WEB SERVER =================
async def handle(request):
    return web.Response(text="Bot is running.")

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
