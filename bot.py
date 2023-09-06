#!/usr/bin/env python3
import time
import discord
import datetime
from discord.ext import commands, tasks
import yaml
from zoneinfo import ZoneInfo

with open ('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

time_format = "%H:%M"
discord_token = config['discord']['token']
accepted_channels = config['discord']['accepted_channels']
raw_nuke_time = config['discord']['channel_delete_time']
raw_warning_time = config['discord']['channel_warning_time']
nuke_time = datetime.datetime.strptime(raw_nuke_time, time_format)
warning_time = datetime.datetime.strptime(raw_warning_time, time_format)
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
            print('Starting nuke scheduled task')

    @tasks.loop(time=datetime.time(hour=warning_time.hour, minute=warning_time.minute, tzinfo=ZoneInfo('Australia/Hobart')))
    async def warning():
        print('Sending deletion warning')
        for channel_id in accepted_channels:
            channel = client.get_channel(channel_id)
            await channel.send('This channel will be nuked in 5 minutes!')

    @tasks.loop(time=datetime.time(hour=nuke_time.hour, minute=nuke_time.minute, tzinfo=ZoneInfo('Australia/Hobart')))
    async def auto_nuke(deleted=0):
        weapon = 'Exterminatus'
        print('Sending nuke')
        for channel_id in accepted_channels:
            channel = client.get_channel(channel_id)
            for i in range(3,0,-1):
                await channel.send(f'{weapon} in {i}')
                time.sleep(1)
            await channel.send('No one expects The Inquisition')
            await channel.send(file=discord.File('assets/images/exterminatus.gif'))
            time.sleep(2)
            deleted = len(await channel.purge(limit=100))
        if deleted < 100:
            embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
            embed.description = f'{deleted} messages were destroyed'
            await channel.send(embed=embed)
            print(f'{deleted} messages were deleted.', flush=True)
            return
        else:
            await auto_nuke(deleted+100)
            return
    
    @client.command(name='nuke', brief='Deletes all messages from the current channel', aliases=['exterminatus'])
    async def nuke(ctx, deleted=0):
        weapon = ctx.invoked_with.capitalize()
        if deleted == 0:
            print(f'Command called from {ctx.channel.name} by {ctx.author.name} using {weapon}')
            for channel in accepted_channels:
                if ctx.channel.id not in accepted_channels:
                    print(f'{ctx.channel.name} is not in the accepted channel list, not running', flush=True)
                    return
            for i in range(3,0,-1):
                await ctx.channel.send(f'{weapon} in {i}')
                time.sleep(1)
            if ctx.invoked_with == 'nuke':
                await ctx.channel.send('RBMK reactors don\'t explode')
                await ctx.send(file=discord.File('assets/images/nuke.gif'))
            else:
                await ctx.channel.send('In his name')
                await ctx.send(file=discord.File('assets/images/exterminatus.gif'))
            time.sleep(2)
        deleted = len(await ctx.channel.purge(limit=100))
        if deleted < 100:
            embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
            embed.description = f'{deleted} messages were destroyed'
            await ctx.send(embed=embed)
            print(f'{deleted} messages were deleted.', flush=True)
            return
        else:
            await nuke(ctx, deleted+100)
            return

    client.run(discord_token)

if __name__ == "__main__":
    main()
