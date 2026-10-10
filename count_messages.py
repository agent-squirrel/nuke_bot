#!/usr/bin/env python
import discord
from discord.ext import tasks, commands
import asyncio
import yaml
import time

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    discord_token = config['discord']['token']

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    channel = client.get_channel(1095581847917965343)
    count = 0
    async for _ in channel.history(limit=None):
        count += 1
    await channel.send("There were {} messages in {}".format(count, channel.mention))

client.run(discord_token)
