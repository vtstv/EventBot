import discord
from discord.ext import commands
import yaml
import os
from dotenv import load_dotenv
from database.db_manager import DatabaseManager
from utils.config_loader import ConfigLoader

load_dotenv()

class EventBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='%', intents=intents)
        self.config = ConfigLoader().load_config()
        self.db = DatabaseManager()
        self.listening_channel = None

    async def setup_hook(self):
        await self.load_extension('commands.admin_commands')
        await self.load_extension('commands.create_event')
        await self.load_extension('commands.edit_event')
        await self.load_extension('commands.close_event')
        await self.load_extension('commands.open_event')
        await self.load_extension('commands.delete_event')

    async def on_ready(self):
        print(f'{self.user} has connected to Discord')
        await self.tree.sync()

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get('custom_id', ' ')
            if custom_id.startswith('signup_'):
                event_id = int(custom_id.split('_')[1])
                role_name = custom_id.split('_')[2]
                create_event_command = self.get_cog('CreateEventCommand')
                if create_event_command:
                    await create_event_command.handle_signup(interaction, event_id, role_name)
            elif custom_id.startswith('cancel_'):
                event_id = int(custom_id.split('_')[1])
                create_event_command = self.get_cog('CreateEventCommand')
                if create_event_command:
                    await create_event_command.handle_cancel(interaction)

def main():
    bot = EventBot()
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    main()
