#!/usr/bin/env python3
import time
import discord
import aiohttp
import datetime
from discord.ext import commands, tasks
import yaml
from zoneinfo import ZoneInfo
import random

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

time_format = "%H:%M"
discord_token = config['discord']['token']
accepted_channels = config['discord']['accepted_channels']
raw_nuke_time = config['discord']['channel_delete_time']
raw_warning_time = config['discord']['channel_warning_time']
nuke_time = datetime.datetime.strptime(raw_nuke_time, time_format)
warning_time = datetime.datetime.strptime(raw_warning_time, time_format)
monitoring_endpoint = config['monitoring']['endpoint']
client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

def main():
    @client.event
    async def on_ready():
        print('Weapons ready')
        print(f'Channel nuke time is {raw_nuke_time}, warning time is {raw_warning_time}')
        if not warning.is_running():
            warning.start()
            print('Starting deletion warning scheduled task')
        if not auto_nuke.is_running():
            auto_nuke.start()
            print('Starting auto nuke scheduled task')
        if not monitor.is_running():
            monitor.start()
            print('Starting heartbeat scheduled task')

    async def nuke(ctx, weapon, deleted, message_count, auto_nuke=0, channel=0):
        if deleted == 0:
            if auto_nuke == 0:
                print(f'Command called from {ctx.channel.name} by {ctx.author.name} using {weapon}')
                print(f'Message count is {message_count}')
                for _ in accepted_channels:
                    if ctx.channel.id not in accepted_channels:
                        print(f'{ctx.channel.name} is not in the accepted channel list, not running', flush=True)
                        return
            for i in range(3,0,-1):
                if auto_nuke == 0:
                    await ctx.channel.send(f'{weapon} in {i}')
                else:
                    await channel.send(f'{weapon} in {i}')
                time.sleep(1)
            if weapon == 'Nuke':
                gifs = config['gifs']['nuke']
                await ctx.channel.send('RBMK reactors don\'t explode')
                await ctx.send(file=discord.File(random.choice(gifs)))
            elif weapon == 'Exterminatus' and auto_nuke == 0:
                gifs = config['gifs']['exterminatus']
                await ctx.channel.send('In his name')
                await ctx.send(file=discord.File(random.choice(gifs)))
            else:
                gifs = config['gifs']['exterminatus']
                await channel.send('In his name')
                await channel.send(file=discord.File(random.choice(gifs)))
            time.sleep(2)
        if auto_nuke == 0:
            deleted = len(await ctx.channel.purge(limit=100))
        else:
            deleted = len(await channel.purge(limit=100))
        if deleted < 100:
            embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
            embed.description = f'{message_count} messages were destroyed'
            if auto_nuke == 0:
                await ctx.send(embed=embed)
            else:
                await channel.send(embed=embed)
            print(f'{weapon} complete. {message_count} messages were deleted.', flush=True)
            return
        elif auto_nuke == 0:
            await nuke(ctx, weapon, deleted+100, message_count)
            return
        else:
            await nuke(ctx, weapon, deleted+100, message_count, auto_nuke, channel)
            return

    @tasks.loop(time=datetime.time(hour=nuke_time.hour, minute=nuke_time.minute, tzinfo=ZoneInfo('Australia/Hobart')))
    async def auto_nuke():
        print('Deploying auto nuke')
        weapon = 'Exterminatus'
        message_count = 0
        ctx = None
        auto_nuke = 1
        for channel_id in accepted_channels:
            channel = client.get_channel(channel_id)
            async for _ in channel.history(limit=None):
                message_count += 1
            deleted = 0
            await nuke(ctx, weapon, deleted, message_count, auto_nuke, channel)
    
    @client.command(name='nuke', brief='Deletes all mesages from the current channel', aliases=['exterminatus'])
    async def manual_nuke(ctx):
        print('Deploying nuke')
        message_count = 0
        deleted = 0
        auto_nuke = 0
        channel = 0
        weapon = ctx.invoked_with.capitalize()
        async for _ in ctx.channel.history(limit=None):
            message_count += 1
        await nuke(ctx, weapon, deleted, message_count, auto_nuke)

    @tasks.loop(time=datetime.time(hour=warning_time.hour, minute=warning_time.minute, tzinfo=ZoneInfo('Australia/Hobart')))
    async def warning():
        print('Sending deletion warning')
        for channel_id in accepted_channels:
            channel = client.get_channel(channel_id)
            await channel.send('This channel will be nuked in 5 minutes!')

    @tasks.loop(seconds=59)
    async def monitor():
        print('Sending heartbeat to monitoring.gnuplusadam.com')
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            try:
                monitor = await session.get(monitoring_endpoint)
                data = await monitor.json()
                if data['ok'] == True:
                    return
                else:
                    print('Didn\'t get expected response from monitoring endpoint.')
            except aiohttp.ClientResponseError as e:
                print('Connection error, monitoring endpoint is down!!', str(e))
            
    client.run(discord_token)

if __name__ == "__main__":
    main()
