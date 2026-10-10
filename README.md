# Nuke Discord Bot

A simple bot that deletes the contents of a channel(s) on a schedule or manually.

# Install

## Discord

> [!NOTE]
> Instructions for creating a bot are beyond the scope of this document.

Create a [Discord bot](https://discord.com/developers/applications).

Grab the OAuth URL from the URL Generator. 

Visit the URL and invite the bot to your server.

## Bot

Clone this repo somewhere

```bash
mkdir /opt/bots
cd /opt/bots
git clone https://github.com/agent-squirrel/nuke_bot.git
cd nuke_bot
mv config.yaml.example config.yaml
```
Add the token from the Discord dev portal to `config.yaml`.

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Create a systemd unit to start the bot automatically.
```bash
cat << EOF > /etc/systemd/system/nuke_bot.service
[Unit]
Description=Nuke Discord Bot
After=network.target

[Service]
WorkingDirectory=/opt/bots/nuke_bot
ExecStart=/opt/bots/nuke_bot/venv/bin/python -u bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```
Reload systemd and start the bot.
```bash
systemctl daemon-reload
systemctl enable --now nuke_bot
```
# Usage

Edit the `config.yaml` file.

Add channel ids to accepted channels. These channels can be nuked manually.

To nuke the accepted channels automatically every day, set `auto_nuke: true`, set `timezone` to an IANA timezone name (e.g. `Australia/Hobart`) and change the channel_delete_time and channel_warning_time to the desired values in 24hr format.

The channels to be deleted will receive a warning at the warning time and will then have their contents deleted at the deletion time.

To post an extra gif after a nuke in specific channels, map the channel id to a gif set under `post_nuke_gifs`.

Manually delete a channel's contents with either `/nuke` or for fun `/exterminatus`.

Messages older than 14 days have to be deleted one at a time, so nuking a big old channel can take a while. `/obliterate` instead deletes the channel and recreates it with the same name, topic, category, position and permissions, which is instant. Only the user ids listed under `obliterate_users` in `config.yaml` can use it, and the bot needs the Manage Channels permission. Pins, threads and webhooks are not carried over. Because the recreated channel has a new id, the bot rewrites the old id to the new one in `config.yaml`. Once the channel is back, the bot posts a gif from the `obliterate` gif set (a black hole implosion is included) instead of the usual weapon and post-nuke gifs.

After changing the config file, the nuke_bot service needs to be restarted.
