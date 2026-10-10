#!/usr/bin/env python3
import argparse
import logging
import yaml
import discord
from discord.ext import commands
import asyncio

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

discord_token = config['discord']['token']
TARGET_WORD = "holly"  # Word to search for

# Parse CLI arguments
parser = argparse.ArgumentParser(description="Clean messages around a target word in a Discord channel.")
parser.add_argument("guild_id", type=int, help="ID of the Discord guild (server)")
parser.add_argument("channel_id", type=int, help="ID of the Discord channel")
args = parser.parse_args()

# Set up the bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    guild = bot.get_guild(args.guild_id)
    if not guild:
        print(f"Guild with ID {args.guild_id} not found.")
        await bot.close()
        return

    channel = guild.get_channel(args.channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        print(f"Channel with ID {args.channel_id} not found or not a text channel.")
        await bot.close()
        return

    print(f"Cleaning messages in #{channel.name} (ID: {channel.id})...")

    try:
        async for message in channel.history(limit=None):
            if TARGET_WORD.lower() in message.content.lower():
                messages_to_delete = []

                async for before_message in channel.history(limit=5, before=message):
                    messages_to_delete.append(before_message)

                messages_to_delete.append(message)

                async for after_message in channel.history(limit=5, after=message):
                    messages_to_delete.append(after_message)

                for msg in messages_to_delete:
                    try:
                        await msg.delete()
                    except discord.HTTPException as e:
                        print(f"Failed to delete message: {e}")

                print(f"Deleted messages around: {message.content}")

        print("Done!")
    except discord.Forbidden:
        print("Permission denied: Cannot delete messages in this channel.")
    except discord.HTTPException as e:
        print(f"An error occurred: {e}")

    await bot.close()

# Run the bot
bot.run(discord_token)

