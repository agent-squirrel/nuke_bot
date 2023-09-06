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
cat << EOF >
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

Add channel ids to accepted channels. These channels will be nuked automatically and are also able to be manually nuked.

Change the channel_delete_time and channel_warning_time to the desired values in 24hr format.

The channels to be deleted will recieve a warning at the warning time and will then have their contents deleted at the deletion time.

Manually delete a channel's contents with either `!nuke` or for fun `!exterminatus`.

After changing the config file, the callout_bot service needs to be restarted.
