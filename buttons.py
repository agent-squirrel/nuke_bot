
import discord
class nuke_controls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

    @discord.ui.button(label='Burn!', style=discord.ButtonStyle.danger, emoji='<a:nuke:1192384311232569455>')
    async def burn_callback(self, button, interaction):
      self.disable_all_items()  
      await interaction.response.edit_message(view=self)
      await interaction.followup.send('Beginning countdown', ephemeral=True)
      self.value = True
      self.stop()
    
    @discord.ui.button(label='Abort!', style=discord.ButtonStyle.secondary, emoji='\U0001F6D1')
    async def abort_nuke_callback(self, button, interaction):
      self.disable_all_items()
      await interaction.response.edit_message(view=self)
      await interaction.followup.send('Aborting nuclear launch', ephemeral=True)
      self.value = False
      self.stop()

class exterminatus_controls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

    @discord.ui.button(label='Purge!', style=discord.ButtonStyle.danger, emoji='<:inquisition:1192768677314039888>')
    async def exterminatus_callback(self, button, interaction):
      self.disable_all_items()  
      await interaction.response.edit_message(view=self)
      await interaction.followup.send('+++ INCOMING TRANSMISSION +++\nIt shall be done my lord\n+++ END TRANSMISSION +++', ephemeral=True)
      self.value = True
      self.stop()
    
    @discord.ui.button(label='Abort!', style=discord.ButtonStyle.secondary, emoji='\U0001F6D1')
    async def abort_exterminatus_callback(self, button, interaction):
      self.disable_all_items()
      await interaction.response.edit_message(view=self)
      await interaction.followup.send('Aborting exterminatus', ephemeral=True)
      self.value = False
      self.stop()
