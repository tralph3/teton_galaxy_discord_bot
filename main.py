from mcstatus import JavaServer
from dataclasses import dataclass
from io import BytesIO
import base64
import os
import json
import time
import asyncio
import discord
import logging

@dataclass
class ServerStats():
    description: str
    player_count: int
    max_player_count: int
    player_list: list[str]
    mc_version: str
    favicon_file: discord.File | None

SERVER_STATS = None

SERVER_IP = os.environ.get("TETON_SERVER_IP", "")
TOKEN = os.environ.get("TETON_DISCORD_TOKEN", "")
CHANNEL_ID = os.environ.get("TETON_CHANNEL_ID", "")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger("teton")

def get_server_stats():
    try:
        server = JavaServer.lookup(SERVER_IP)
        status = server.status()
        query = server.query()

        favicon_file = None
        if "favicon" in status.raw:
            raw = base64.b64decode(status.raw["favicon"].split("base64,")[1])

            favicon_file = discord.File(
                BytesIO(raw),
                filename="favicon.png",
            )
    except Exception as e:
        logger.error(f"Getting server stats failed: {e}")
        return None

    return ServerStats(
        description=status.description,
        player_count=query.players.online,
        max_player_count=query.players.max,
        player_list=query.players.list,
        favicon_file=favicon_file,
        mc_version=query.software.version,
    )

def build_embed():
    retry_count = 0
    while retry_count < 5:
        stats = get_server_stats()
        if stats is None:
            logger.error("Failed getting server info... retrying")
            time.sleep(2)
            retry_count += 1
        else:
            break

    green = 0x00AA00
    red = 0x992D22

    embed = discord.Embed(
        color=green if stats is not None else red,
        timestamp=discord.utils.utcnow(),
    )

    if stats is None:
        embed.set_author(name="⚠️ SE CAYO TETON GALAXY")
        return (embed, stats)
    else:
        embed.set_author(name="🟢 Online")

    embed.title="Teton Galaxy"
    embed.description=stats.description

    players = "\n".join(
        f"- {p}" for p in stats.player_list
    )

    if not players:
        players = "*No hay tetones juguetones 😒*"

    if stats.mc_version:
        embed.add_field(name="Version", value=stats.mc_version)

    embed.add_field(name=f"Tetones   •   {stats.player_count}/{stats.max_player_count}", value=players, inline=False)

    embed.set_footer(text="Que miras gordo teton?")
    if stats.favicon_file is not None:
        embed.set_thumbnail(url="attachment://favicon.png")

    return (embed, stats)


async def get_or_create_message(channel):
    async for message in channel.history(limit=20):
        if message.author.id == client.user.id:
            return message

    embed, stats = build_embed()

    return await channel.send(
        embed=embed,
        file=stats.favicon_file if stats and stats.favicon_file else None,
    )

async def updater():
    await client.wait_until_ready()

    channel = client.get_channel(int(CHANNEL_ID))

    if channel is None:
        logger.warning("Channel not found")
        return

    message = await get_or_create_message(channel)

    while True:
        try:
            embed, stats = build_embed()
            await message.edit(
                embed=embed,
                attachments=[stats.favicon_file] if stats and stats.favicon_file else [],
            )

            logger.info("Stats updated")

        except discord.errors.NotFound:
            logger.warning("Message got deleted, recreating...")
            message = await get_or_create_message(channel)

        except Exception as e:
            logger.error(e)

        await asyncio.sleep(60)


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")

@client.event
async def setup_hook():
    asyncio.create_task(updater())

if __name__ == "__main__":
    if TOKEN == "" or CHANNEL_ID == "" or SERVER_IP == "":
        logger.error("Missing required env vars. Aborting")
        exit()

    client.run(TOKEN)
