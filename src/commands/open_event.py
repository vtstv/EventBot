import discord
from discord.ext import commands
from discord import app_commands

class OpenEventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name='open_event', description='Reopen a closed event')
    @app_commands.default_permissions(administrator=True)
    async def open_event_command(self, interaction: discord.Interaction, event_id: int):
        event = self.db.get_event(event_id)
        if not event:
            await interaction.response.send_message("Event not found.")
            return
        if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("You do not have permission to open this event.")
            return
        await self.open_event(event_id)
        await interaction.response.send_message(f"Event {event_id} has been reopened.")

    async def open_event(self, event_id: int):
        """Reopen a closed event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, status='open')

async def setup(bot):
    await bot.add_cog(OpenEventCommand(bot))
