#!/usr/bin/env python
# Count the messages in a channel, e.g. ./count_messages.py 1558334429422686248 --post
import argparse
import asyncio
import discord
import yaml

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    discord_token = config['discord']['token']

parser = argparse.ArgumentParser(description='Count the messages in a channel.')
parser.add_argument('channel_id', type=int, help='channel to count')
parser.add_argument('--post', action='store_true', help='also post the count in the channel')
args = parser.parse_args()

async def main():
    # REST only, no gateway connection, so this can run alongside the bot on the same token
    client = discord.Client()
    await client.login(discord_token)
    try:
        channel = await client.fetch_channel(args.channel_id)
        count = 0
        async for _ in channel.history(limit=None):
            count += 1
        print(f'There were {count} messages in #{channel.name}')
        if args.post:
            await channel.send(f'There were {count} messages in {channel.mention}')
    finally:
        await client.close()

asyncio.run(main())
