#!/usr/bin/env python3
import logging
from logging.handlers import RotatingFileHandler
from buttons import nuke_controls, exterminatus_controls, obliterate_controls
import asyncio
import functools
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
# The top level auto nuke settings are the defaults, entries in auto_nuke_channels override them per channel
auto_nuke_defaults = {
    'auto_nuke': config['discord'].get('auto_nuke', False),
    'channel_warning_time': config['discord']['channel_warning_time'],
    'channel_delete_time': config['discord']['channel_delete_time'],
    'weapon': 'exterminatus',
}
auto_nuke_channels = config['discord'].get('auto_nuke_channels') or {}
post_nuke_gifs = config.get('post_nuke_gifs') or {}
gif_load_time = 1.5
obliterate_users = config['discord'].get('obliterate_users') or []
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

def load_schedule(channel_id):
    settings = {**auto_nuke_defaults, **(auto_nuke_channels.get(channel_id) or {})}
    if not settings['auto_nuke']:
        return None
    nuke_time = datetime.datetime.strptime(settings['channel_delete_time'], time_format).time()
    warning_time = datetime.datetime.strptime(settings['channel_warning_time'], time_format).time()
    weapon = settings['weapon'].lower()
    if weapon not in ('nuke', 'exterminatus'):
        raise ValueError(f'Auto nuke weapon for channel {channel_id} must be nuke or exterminatus, not {weapon}')
    return {
        'nuke_time': nuke_time,
        'warning_time': warning_time,
        'warning_lead': (nuke_time.hour * 60 + nuke_time.minute - warning_time.hour * 60 - warning_time.minute) % (24 * 60),
        'weapon': weapon.capitalize(),
    }

# Channel id: auto nuke schedule, only for accepted channels with auto nuke turned on
schedules = {channel_id: schedule for channel_id in accepted_channels if (schedule := load_schedule(channel_id))}

bot = discord.Bot()

@functools.cache
def gif_duration(path):
    # Sum the frame delays from the gif's Graphic Control Extensions. Browsers (and so Discord)
    # play a frame with no delay, or one under 20ms, for 100ms, so count them the same way
    with open(path, 'rb') as f:
        data = f.read()
    pos = 13
    if data[10] & 0x80:
        pos += 3 * 2 ** ((data[10] & 0x07) + 1)
    total = 0
    delay = 0
    while pos < len(data) and data[pos] != 0x3B:
        if data[pos] == 0x21:
            if data[pos + 1] == 0xF9:
                delay = int.from_bytes(data[pos + 4:pos + 6], 'little')
            pos += 2
        elif data[pos] == 0x2C:
            total += delay if delay >= 2 else 10
            delay = 0
            flags = data[pos + 9]
            pos += 10
            if flags & 0x80:
                pos += 3 * 2 ** ((flags & 0x07) + 1)
            pos += 1
        else:
            break
        while pos < len(data) and data[pos]:
            pos += data[pos] + 1
        pos += 1
    return total / 100

def replace_channel_id(old_id, new_id):
    # Obliterating recreates the channel with a new id, so carry it over in memory and in the config file
    accepted_channels[accepted_channels.index(old_id)] = new_id
    for mapping in (post_nuke_gifs, auto_nuke_channels, schedules):
        if old_id in mapping:
            mapping[new_id] = mapping.pop(old_id)
    with open(config_path, 'r') as f:
        text = f.read()
    with open(f'{config_path}.tmp', 'w') as f:
        f.write(re.sub(rf'\b{old_id}\b', str(new_id), text))
    os.replace(f'{config_path}.tmp', config_path)

def main():
    @bot.event
    async def on_ready():
        log.info('Weapons ready')
        log.info(f'Auto nuke timezone is {tz}')
        for channel_id, schedule in schedules.items():
            channel = bot.get_channel(channel_id)
            log.info(f'Auto {schedule["weapon"].lower()} for {channel.name if channel else channel_id} at {schedule["nuke_time"]}, warning at {schedule["warning_time"]}')
        for channel_id in auto_nuke_channels.keys() - set(accepted_channels):
            log.warning(f'Channel {channel_id} has auto nuke settings but is not in the accepted channel list, ignoring them')
        log.info(f'Setting presence to: {presence_msg}')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=presence_msg))
        if schedules and not auto_nuke.is_running():
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

    async def finish(channel, weapon, description):
        embed = discord.Embed(title=f'{weapon} complete', color=0xe42313)
        embed.description = description
        await channel.send(embed=embed)

    async def nuke_routine(channel, weapon):
        first = await countdown(channel, weapon)
        if weapon == 'Nuke':
            gifs = config['gifs']['nuke']
        else:
            gifs = config['gifs']['exterminatus']
            await channel.send('In his name')
        gif = random.choice(gifs)
        await channel.send(file=discord.File(gif))
        # Let the gif play through once, plus time for clients to download it, before the messages go
        await asyncio.sleep(gif_duration(gif) + gif_load_time)

        # Only count what was there before the countdown, then sweep up the countdown messages too
        message_count = len(await channel.purge(limit=None, before=first))
        await channel.purge(limit=None)

        await finish(channel, weapon, f'{message_count} messages were destroyed')
        gif_set = post_nuke_gifs.get(channel.id)
        if gif_set:
            await channel.send(file=discord.File(random.choice(config['gifs'][gif_set])))
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
        # Once the channel is back, show the old one collapsing into nothing instead of the usual weapon and post-nuke gifs
        gifs = config['gifs'].get('obliterate')
        if gifs:
            await new_channel.send(file=discord.File(random.choice(gifs)))
        await finish(new_channel, weapon, 'The channel was erased from existence')
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
        if ctx.author.id not in obliterate_users:
            log.info(f'{ctx.author.name} tried to obliterate {ctx.channel.name} but is not allowed to')
            await ctx.respond('Only the chosen may obliterate.', ephemeral=True)
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.respond('I need the Manage Channels permission to obliterate this channel.', ephemeral=True)
            return
        await launch(ctx, obliterate_controls(), obliterate_routine)

    # py-cord's time based loops mix UTC dates with local times and misfire, so poll the clock each minute
    # instead and fire each job at most once per day when the local time in the configured timezone matches
    last_run = {}

    def is_due(name, target):
        now = datetime.datetime.now(tz)
        # Round trip through UTC so a time skipped by a DST change moves to just after the gap
        scheduled = datetime.datetime.combine(now.date(), target, tzinfo=tz).astimezone(datetime.timezone.utc).astimezone(tz)
        if (now.hour, now.minute) != (scheduled.hour, scheduled.minute) or last_run.get(name) == now.date():
            return False
        last_run[name] = now.date()
        return True

    def get_channel(channel_id):
        channel = bot.get_channel(channel_id)
        if channel is None:
            log.warning(f'Cannot see channel {channel_id}, skipping')
        return channel

    # Run each auto nuke as its own task so a slow one doesn't hold up the clock for channels due later
    running_nukes = set()

    def auto_nuke_done(task):
        running_nukes.discard(task)
        if not task.cancelled() and task.exception():
            log.error('Auto nuke failed', exc_info=task.exception())

    @tasks.loop(minutes=1)
    async def auto_nuke():
        # Obliterating swaps channel ids in schedules, so iterate over a copy
        for channel_id, schedule in list(schedules.items()):
            if is_due(('warning', channel_id), schedule['warning_time']) and (channel := get_channel(channel_id)):
                log.info(f'Sending deletion warning to {channel.name}')
                lead = schedule['warning_lead']
                try:
                    await channel.send(f'This channel will be nuked in {lead} minute{"" if lead == 1 else "s"}!')
                except discord.HTTPException as e:
                    log.error(f'Could not send deletion warning to {channel.name}: {e}')
            if is_due(('auto_nuke', channel_id), schedule['nuke_time']) and (channel := get_channel(channel_id)):
                log.info(f'Deploying auto {schedule["weapon"].lower()} on {channel.name}')
                task = asyncio.create_task(nuke_routine(channel, schedule['weapon']))
                running_nukes.add(task)
                task.add_done_callback(auto_nuke_done)

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
