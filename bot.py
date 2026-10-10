#!/usr/bin/env python3
import logging
from logging.handlers import RotatingFileHandler
from buttons import nuke_controls, exterminatus_controls, obliterate_controls
import asyncio
import discord
import aiohttp
import datetime
from discord.ext import tasks
import yaml
from zoneinfo import ZoneInfo
import random
import os
import re
import sys

config_path = 'config.yaml'
with open (config_path, 'r') as f:
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
warning_lead = (nuke_time.hour * 60 + nuke_time.minute - warning_time.hour * 60 - warning_time.minute) % (24 * 60)
post_nuke_gifs = config.get('post_nuke_gifs') or {}
monitoring_endpoint = config['monitoring']['endpoint']
config_log_level = config['logging']['level']

file_handler = RotatingFileHandler(filename='bot.log', encoding='utf-8', maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.getLevelNamesMapping().get(config_log_level, logging.INFO))
discord_logger.addHandler(file_handler)
# The bot's own messages always go to stdout (journald) as well as the log file
log = logging.getLogger('nuke_bot')
log.setLevel(logging.INFO)
log.addHandler(file_handler)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
log.addHandler(console_handler)

bot = discord.Bot()

def replace_channel_id(old_id, new_id):
    # Obliterating recreates the channel with a new id, so carry it over in memory and in the config file
    accepted_channels[accepted_channels.index(old_id)] = new_id
    if old_id in post_nuke_gifs:
        post_nuke_gifs[new_id] = post_nuke_gifs.pop(old_id)
    with open(config_path, 'r') as f:
        text = f.read()
    with open(f'{config_path}.tmp', 'w') as f:
        f.write(re.sub(rf'\b{old_id}\b', str(new_id), text))
    os.replace(f'{config_path}.tmp', config_path)

def main():
    @bot.event
    async def on_ready():
        log.info('Weapons ready')
        log.info(f'Channel nuke time is {nuke_time}, warning time is {warning_time} and timezone is {tz}')
        log.info(f'Setting presence to: {presence_msg}')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=presence_msg))
        if auto_nuke_enabled:
            if not warning.is_running():
                warning.start()
                log.info('Starting deletion warning scheduled task')
            if not auto_nuke.is_running():
                auto_nuke.start()
                log.info('Starting auto nuke scheduled task')
        if not monitor.is_running():
            monitor.start()
            log.info('Starting heartbeat scheduled task')

    async def countdown(channel, weapon):
        first = None
        for i in range(3,0,-1):
            message = await channel.send(f'{weapon} in {i}')
            first = first or message
            await asyncio.sleep(1)
        return first

    async def finish(channel, weapon, description, gifs=None):
        if gifs:
            await channel.send(file=discord.File(random.choice(gifs)))
        embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
        embed.description = description
        await channel.send(embed=embed)
        gif_set = post_nuke_gifs.get(channel.id)
        if gif_set:
            await channel.send(file=discord.File(random.choice(config['gifs'][gif_set])))

    async def nuke_routine(channel, weapon):
        first = await countdown(channel, weapon)
        if weapon == 'Nuke':
            gifs = config['gifs']['nuke']
        else:
            gifs = config['gifs']['exterminatus']
            await channel.send('In his name')
        await channel.send(file=discord.File(random.choice(gifs)))
        await asyncio.sleep(2)

        # Only count what was there before the countdown, then sweep up the countdown messages too
        message_count = len(await channel.purge(limit=None, before=first))
        await channel.purge(limit=None)

        await finish(channel, weapon, f'{message_count} messages were destroyed')
        log.info(f'{weapon} complete. {message_count} messages were deleted.')

    async def obliterate_routine(channel, weapon):
        # Deleting and recreating the channel is instant no matter how many (or how old) the messages are
        await countdown(channel, weapon)
        reason = f'{weapon} from the nuke bot'
        new_channel = await channel.clone(reason=reason)
        try:
            await new_channel.edit(position=channel.position)
            await channel.delete(reason=reason)
        except discord.HTTPException:
            await new_channel.delete(reason=f'{weapon} failed')
            raise
        replace_channel_id(channel.id, new_channel.id)
        await finish(new_channel, weapon, 'The channel was erased from existence',
                     config['gifs'].get('obliterate') or config['gifs']['nuke'])
        log.info(f'{weapon} complete. Channel {channel.name} recreated as {new_channel.id}.')

    async def launch(ctx, view, routine):
        if ctx.channel.id not in accepted_channels:
            log.info(f'{ctx.channel.name} is not in the accepted channel list, not running')
            await ctx.respond('This channel is not in the accepted channel list.', ephemeral=True)
            return
        weapon = ctx.command.qualified_name.capitalize()
        await ctx.respond(view=view)
        await view.wait()
        if view.value:
            log.info(f'Command called from {ctx.channel.name} by {ctx.author.name} using {weapon}')
            await routine(ctx.channel, weapon)
        else:
            log.info(f'Aborting {weapon.lower()}')

    @bot.slash_command(description='Nukes the chat in a spectacular white hot fireball', guild_ids=guilds)
    async def nuke(ctx):
        await launch(ctx, nuke_controls(), nuke_routine)

    @bot.slash_command(description='Calls down the holy wrath of the inquisition', guild_ids=guilds)
    async def exterminatus(ctx):
        await launch(ctx, exterminatus_controls(), nuke_routine)

    @bot.slash_command(description='Erases the channel from existence and rebuilds it, instantly', guild_ids=guilds)
    async def obliterate(ctx):
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.respond('I need the Manage Channels permission to obliterate this channel.', ephemeral=True)
            return
        await launch(ctx, obliterate_controls(), obliterate_routine)

    # py-cord's time based loops mix UTC dates with local times and misfire, so poll the clock each
    # minute instead and fire at most once per day when the local time in the configured timezone matches
    last_run = {}

    def is_due(name, target):
        now = datetime.datetime.now(tz)
        # Round trip through UTC so a time skipped by a DST change moves to just after the gap
        scheduled = datetime.datetime.combine(now.date(), target, tzinfo=tz).astimezone(datetime.timezone.utc).astimezone(tz)
        if (now.hour, now.minute) != (scheduled.hour, scheduled.minute) or last_run.get(name) == now.date():
            return False
        last_run[name] = now.date()
        return True

    def get_accepted_channels():
        for channel_id in accepted_channels:
            channel = bot.get_channel(channel_id)
            if channel is None:
                log.warning(f'Cannot see channel {channel_id}, skipping')
                continue
            yield channel

    @tasks.loop(minutes=1)
    async def auto_nuke():
        if not is_due('auto_nuke', nuke_time):
            return
        log.info('Deploying auto nuke')
        for channel in get_accepted_channels():
            await nuke_routine(channel, 'Exterminatus')

    @tasks.loop(minutes=1)
    async def warning():
        if not is_due('warning', warning_time):
            return
        log.info('Sending deletion warning')
        for channel in get_accepted_channels():
            await channel.send(f'This channel will be nuked in {warning_lead} minute{"" if warning_lead == 1 else "s"}!')

    monitor_session = None

    @tasks.loop(seconds=59)
    async def monitor():
        nonlocal monitor_session
        if monitor_session is None:
            monitor_session = aiohttp.ClientSession(raise_for_status=True, timeout=aiohttp.ClientTimeout(total=10))
        log.debug('Sending heartbeat to monitoring endpoint')
        try:
            async with monitor_session.get(monitoring_endpoint) as response:
                data = await response.json()
            if isinstance(data, dict) and data.get('ok') == True:
                return
            log.warning('Didn\'t get expected response from monitoring endpoint.')
        except aiohttp.ClientResponseError as e:
            log.error(f'Monitoring endpoint returned an error!! {e}')
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.error(f'Connection error, monitoring endpoint is down!! {e!r}')

    @monitor.after_loop
    async def close_monitor_session():
        if monitor_session is not None:
            await monitor_session.close()

    bot.run(discord_token)

if __name__ == "__main__":
    main()
