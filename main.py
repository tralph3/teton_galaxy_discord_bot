from mcstatus import JavaServer
from dataclasses import dataclass
from io import BytesIO
import base64
import os
import json
import time
import asyncio
import discord

@dataclass
class ServerStats():
    description: str
    player_count: int
    max_player_count: int
    player_list: list[str]
    mc_version: str
    favicon_file: discord.File | None

SERVER_STATS = None

SERVER_IP = os.environ.get("TETON_SERVER_IP", None)
TOKEN = os.environ.get("TETON_DISCORD_TOKEN", None)
CHANNEL_ID = os.environ.get("TETON_CHANNEL_ID", None)

CONFIG_FILE = "config.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

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
        print(f"Getting server stats failed: {e}")
        return None

    return ServerStats(
        description=status.description,
        player_count=query.players.online,
        max_player_count=query.players.max,
        player_list=query.players.list,
        favicon_file=favicon_file,
        mc_version=query.software.version,
    )

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def build_embed():
    retry_count = 0
    while retry_count < 5:
        stats = get_server_stats()
        if stats is None:
            print("Failed getting server info... retrying")
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

    embed.add_field(name="IP", value=SERVER_IP)

    if stats.mc_version:
        embed.add_field(name="Version", value=stats.mc_version)

    embed.add_field(name=f"Tetones   •   {stats.player_count}/{stats.max_player_count}", value=players, inline=False)

    embed.set_footer(text="Que miras gordo teton?")
    if stats.favicon_file is not None:
        embed.set_thumbnail(url="attachment://favicon.png")

    return (embed, stats)


async def get_or_create_message(channel):
    config = load_config()

    message_id = config.get("message_id")

    if message_id is not None:
        try:
            return await channel.fetch_message(message_id)
        except discord.NotFound:
            print("message deleted, creating new one")

    embed, stats = build_embed()

    message = await channel.send(
        embed=embed,
        file=stats.favicon_file if stats and stats.favicon_file else None,
    )

    config["message_id"] = message.id
    save_config(config)

    print(f"created message {message.id}")

    return message


async def updater():
    await client.wait_until_ready()

    channel = client.get_channel(int(CHANNEL_ID))

    if channel is None:
        print("channel not found")
        return

    message = await get_or_create_message(channel)

    while True:
        try:
            embed, stats = build_embed()
            await message.edit(
                embed=embed,
                attachments=[stats.favicon_file] if stats and stats.favicon_file else [],
            )

            print("Stats updated")

        except discord.errors.NotFound:
            print("Message got deleted, recreating...")
            message = await get_or_create_message(channel)

        except Exception as e:
            print(e)

        await asyncio.sleep(60)


@client.event
async def on_ready():
    print(f"logged in as {client.user}")

@client.event
async def setup_hook():
    asyncio.create_task(updater())

if __name__ == "__main__":
    if TOKEN is None or CHANNEL_ID is None or SERVER_IP is None:
        print("Missing required env vars. Aborting")
        exit()

    client.run(TOKEN)
