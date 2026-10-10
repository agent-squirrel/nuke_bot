#!/usr/bin/env python
import discord
from discord.ext import tasks, commands
import asyncio
import yaml
import time
import sys

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    discord_token = config['discord']['token']

channelid = sys.argv[1]
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@tasks.loop(seconds=1)
async def test():
    channel = client.get_channel(int(channelid))
    #Loop and send messages to channel
    for i in range(200,0,-1):
        await channel.send(i)
        time.sleep(1)

@client.event
async def on_ready():
    test.start()
client.run(discord_token)
