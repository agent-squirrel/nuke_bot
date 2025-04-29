#!/usr/bin/env python3
import logging
from buttons import nuke_controls, exterminatus_controls
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
guilds = config['discord']['guilds']
presence_msg = config['discord']['presence_msg']
tz = datetime.datetime.now().astimezone().tzinfo
raw_nuke_time = config['discord']['channel_delete_time']
raw_warning_time = config['discord']['channel_warning_time']
nuke_time = datetime.datetime.strptime(raw_nuke_time, time_format).time()
warning_time = datetime.datetime.strptime(raw_warning_time, time_format).time()
monitoring_endpoint = config['monitoring']['endpoint']
config_log_level = config['logging']['level']
logging_dict = {'DEBUG': logging.DEBUG, 
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                }
logger = logging.getLogger('discord')
log_level = logging_dict.get(config_log_level, logging.INFO)
logger.setLevel(log_level)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot = discord.Bot()

def main():
    @bot.event
    async def on_ready():
        print('Weapons ready')
        print(f'Channel nuke time is {nuke_time}, warning time is {warning_time} and timezone is {tz}')
        print(f'Setting presence to: {presence_msg}')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=presence_msg))
#        if not warning.is_running():
#            warning.start()
#            print('Starting deletion warning scheduled task')
#        if not auto_nuke.is_running():
#            auto_nuke.start()
#            print('Starting auto nuke scheduled task')
        if not monitor.is_running():
            monitor.start()
            print('Starting heartbeat scheduled task')

    async def nuke_routine(ctx, weapon, deleted, message_count, auto_nuke=0, channel=0):
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
                if ctx.channel.id == 1317720410808258568:
                    await ctx.send(file=discord.File('assets/images/spice.gif'))
                elif ctx.channel.id == 1126322559122677812:
                    await ctx.send(file=discord.File('assets/images/yakobs.gif'))
            else:
                await channel.send(embed=embed)
                if channel.id == 1317720410808258568:
                    await channel.send(file=discord.File('assets/images/spice.gif'))
                elif ctx.channel.id == 1126322559122677812:
                    await ctx.send(file=discord.File('assets/images/yakobs.gif'))
            print(f'{weapon} complete. {message_count} messages were deleted.', flush=True)
            return
        elif auto_nuke == 0:
            await nuke_routine(ctx, weapon, deleted+100, message_count)
            return
        else:
            await nuke_routine(ctx, weapon, deleted+100, message_count, auto_nuke, channel)
            return
    
    @bot.slash_command(description='Nukes the chat in a spectacular white hot fireball', guild_ids=guilds)
    async def nuke(ctx):
        view = nuke_controls()
        await ctx.respond(view=view)
        await view.wait()
        if view.value:
            print('Deploying nuke')
            message_count = 0
            deleted = 0
            auto_nuke = 0
            channel = 0
            weapon = ctx.command.qualified_name.capitalize()
            async for _ in ctx.channel.history(limit=None):
                message_count += 1
            await nuke_routine(ctx, weapon, deleted, message_count, auto_nuke)
        else:
            print('Aborting nuke')
            return

    @bot.slash_command(description='Calls down the holy wrath of the inquisition', guild_ids=guilds)
    async def exterminatus(ctx):
        view = exterminatus_controls()
        await ctx.respond(view=view)
        await view.wait()
        if view.value:
            print('Deploying exterminatus')
            message_count = 0
            deleted = 0
            auto_nuke = 0
            channel = 0
            weapon = ctx.command.qualified_name.capitalize()
            async for _ in ctx.channel.history(limit=None):
                message_count += 1
            await nuke_routine(ctx, weapon, deleted, message_count, auto_nuke)
        else:
            print('Aborting exterminatus')
            return

    @tasks.loop(time=datetime.time(hour=nuke_time.hour, minute=nuke_time.minute, tzinfo=tz), reconnect=False)
    async def auto_nuke():
        print('Deploying auto nuke')
        weapon = 'Exterminatus'
        message_count = 0
        ctx = None
        auto_nuke = 1
        for channel_id in accepted_channels:
            channel = bot.get_channel(channel_id)
            async for _ in channel.history(limit=None):
                message_count += 1
            deleted = 0
            await nuke_routine(ctx, weapon, deleted, message_count, auto_nuke, channel)

    @tasks.loop(time=datetime.time(hour=warning_time.hour, minute=warning_time.minute, tzinfo=tz), reconnect=False)
    async def warning():
        print('Sending deletion warning')
        for channel_id in accepted_channels:
            channel = bot.get_channel(channel_id)
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
            
    bot.run(discord_token)

if __name__ == "__main__":
    main()
