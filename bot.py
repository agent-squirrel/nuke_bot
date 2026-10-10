#!/usr/bin/env python3
import logging
from buttons import nuke_controls, exterminatus_controls
import asyncio
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
tz = ZoneInfo(config['discord']['timezone'])
auto_nuke_enabled = config['discord'].get('auto_nuke', False)
raw_nuke_time = config['discord']['channel_delete_time']
raw_warning_time = config['discord']['channel_warning_time']
nuke_time = datetime.datetime.strptime(raw_nuke_time, time_format).time()
warning_time = datetime.datetime.strptime(raw_warning_time, time_format).time()
post_nuke_gifs = config.get('post_nuke_gifs') or {}
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
        if auto_nuke_enabled:
            if not warning.is_running():
                warning.start()
                print('Starting deletion warning scheduled task')
            if not auto_nuke.is_running():
                auto_nuke.start()
                print('Starting auto nuke scheduled task')
        if not monitor.is_running():
            monitor.start()
            print('Starting heartbeat scheduled task')

    async def nuke_routine(channel, weapon):
        countdown = None
        for i in range(3,0,-1):
            message = await channel.send(f'{weapon} in {i}')
            countdown = countdown or message
            await asyncio.sleep(1)
        if weapon == 'Nuke':
            gifs = config['gifs']['nuke']
        else:
            gifs = config['gifs']['exterminatus']
            await channel.send('In his name')
        await channel.send(file=discord.File(random.choice(gifs)))
        await asyncio.sleep(2)

        # Only count what was there before the countdown, then sweep up the countdown messages too
        message_count = len(await channel.purge(limit=None, before=countdown))
        await channel.purge(limit=None)

        embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
        embed.description = f'{message_count} messages were destroyed'
        await channel.send(embed=embed)
        gif_set = post_nuke_gifs.get(channel.id)
        if gif_set:
            await channel.send(file=discord.File(random.choice(config['gifs'][gif_set])))
        print(f'{weapon} complete. {message_count} messages were deleted.', flush=True)

    async def launch(ctx, view):
        if ctx.channel.id not in accepted_channels:
            print(f'{ctx.channel.name} is not in the accepted channel list, not running', flush=True)
            await ctx.respond('This channel is not in the accepted channel list.', ephemeral=True)
            return
        weapon = ctx.command.qualified_name.capitalize()
        await ctx.respond(view=view)
        await view.wait()
        if view.value:
            print(f'Command called from {ctx.channel.name} by {ctx.author.name} using {weapon}')
            await nuke_routine(ctx.channel, weapon)
        else:
            print(f'Aborting {weapon.lower()}')

    @bot.slash_command(description='Nukes the chat in a spectacular white hot fireball', guild_ids=guilds)
    async def nuke(ctx):
        await launch(ctx, nuke_controls())

    @bot.slash_command(description='Calls down the holy wrath of the inquisition', guild_ids=guilds)
    async def exterminatus(ctx):
        await launch(ctx, exterminatus_controls())

    # py-cord's time based loops mix UTC dates with local times and misfire, so poll the clock each
    # minute instead and fire at most once per day when the local time in the configured timezone matches
    last_run = {}

    def is_due(name, target):
        now = datetime.datetime.now(tz)
        if (now.hour, now.minute) != (target.hour, target.minute) or last_run.get(name) == now.date():
            return False
        last_run[name] = now.date()
        return True

    def get_accepted_channels():
        for channel_id in accepted_channels:
            channel = bot.get_channel(channel_id)
            if channel is None:
                print(f'Cannot see channel {channel_id}, skipping', flush=True)
                continue
            yield channel

    @tasks.loop(minutes=1)
    async def auto_nuke():
        if not is_due('auto_nuke', nuke_time):
            return
        print('Deploying auto nuke')
        for channel in get_accepted_channels():
            await nuke_routine(channel, 'Exterminatus')

    @tasks.loop(minutes=1)
    async def warning():
        if not is_due('warning', warning_time):
            return
        print('Sending deletion warning')
        for channel in get_accepted_channels():
            await channel.send('This channel will be nuked in 5 minutes!')

    monitor_session = None

    @tasks.loop(seconds=59)
    async def monitor():
        nonlocal monitor_session
        if monitor_session is None:
            monitor_session = aiohttp.ClientSession(raise_for_status=True, timeout=aiohttp.ClientTimeout(total=10))
        print('Sending heartbeat to monitoring.gnuplusadam.com')
        try:
            async with monitor_session.get(monitoring_endpoint) as response:
                data = await response.json()
            if isinstance(data, dict) and data.get('ok') == True:
                return
            print('Didn\'t get expected response from monitoring endpoint.')
        except aiohttp.ClientResponseError as e:
            print('Monitoring endpoint returned an error!!', str(e))
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            print('Connection error, monitoring endpoint is down!!', repr(e))
            
    bot.run(discord_token)

if __name__ == "__main__":
    main()
