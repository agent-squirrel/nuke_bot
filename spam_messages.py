#!/usr/bin/env python
# Fill a channel with messages to test the nukes, e.g. ./spam_messages.py 1558334429422686248 -n 500
import argparse
import asyncio
import sys
import time
import discord
import yaml

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    discord_token = config['discord']['token']
    accepted_channels = config['discord']['accepted_channels']

parser = argparse.ArgumentParser(description='Fill a channel with messages to test the nukes.')
parser.add_argument('channel_id', type=int, help='channel to fill, must be in accepted_channels')
parser.add_argument('-n', '--count', type=int, default=300, help='number of messages to send (default 300)')
args = parser.parse_args()

if args.channel_id not in accepted_channels:
    sys.exit(f'{args.channel_id} is not in accepted_channels, refusing to spam it')

async def main():
    # REST only, no gateway connection, so this can run alongside the bot on the same token
    client = discord.Client()
    await client.login(discord_token)
    try:
        channel = await client.fetch_channel(args.channel_id)
        print(f'Sending {args.count} messages to #{channel.name}')
        sent = 0
        start = time.monotonic()

        async def send(i):
            nonlocal sent
            await channel.send(f'Test message {i}/{args.count}')
            sent += 1
            if sent % 25 == 0:
                print(f'{sent}/{args.count} sent ({sent / (time.monotonic() - start):.1f}/s)', flush=True)

        # Fire them all at once and let py-cord queue them against Discord's rate limit
        results = await asyncio.gather(*(send(i) for i in range(1, args.count + 1)), return_exceptions=True)
        failed = [r for r in results if isinstance(r, Exception)]
        print(f'Done: {sent} sent, {len(failed)} failed in {time.monotonic() - start:.0f}s')
        if failed:
            print(f'First failure: {failed[0]!r}')
    finally:
        await client.close()

asyncio.run(main())
