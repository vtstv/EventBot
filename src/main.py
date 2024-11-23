import discord
from discord.ext import commands
import yaml
import os
import json  # Add this import statement
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
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        template_dir = 'templates'
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
        for filename in os.listdir(template_dir):
            if filename.endswith('.json'):
                with open(os.path.join(template_dir, filename), 'r') as f:
                    try:
                        template_name = filename[:-5]  # Remove .json extension
                        self.templates[template_name] = json.load(f)
                        print(f"Successfully loaded template: {template_name}")
                    except json.JSONDecodeError as e:
                        print(f"Error loading template {filename}: {e}")

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
