import discord

class launch_controls(discord.ui.View):
    def __init__(self, label, emoji, confirm_msg, abort_msg):
        super().__init__(timeout=60, disable_on_timeout=True)
        self.value = None
        self.confirm_msg = confirm_msg
        self.abort_msg = abort_msg

        confirm = discord.ui.Button(label=label, style=discord.ButtonStyle.danger, emoji=emoji)
        confirm.callback = self.confirm_callback
        self.add_item(confirm)
        abort = discord.ui.Button(label='Abort!', style=discord.ButtonStyle.secondary, emoji='\U0001F6D1')
        abort.callback = self.abort_callback
        self.add_item(abort)

    async def finish(self, interaction, value, msg):
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)
        self.value = value
        self.stop()

    async def confirm_callback(self, interaction):
        await self.finish(interaction, True, self.confirm_msg)

    async def abort_callback(self, interaction):
        await self.finish(interaction, False, self.abort_msg)

def nuke_controls():
    return launch_controls('Burn!', '<a:nuke:1192384311232569455>', 'Beginning countdown', 'Aborting nuclear launch')

def exterminatus_controls():
    return launch_controls('Purge!', '<:inquisition:1192768677314039888>',
                           '+++ INCOMING TRANSMISSION +++\nIt shall be done my lord\n+++ END TRANSMISSION +++',
                           'Aborting exterminatus')

def obliterate_controls():
    return launch_controls('Obliterate!', '\U0001F573', 'Erasing the channel from existence', 'Aborting obliteration')
