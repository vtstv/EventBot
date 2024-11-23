import discord
from discord.ext import commands
from discord import app_commands

class DeleteEventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name='delete_event', description='Delete an event')
    @app_commands.default_permissions(administrator=True)
    async def delete_event_command(self, interaction: discord.Interaction, event_id: int):
        event = self.db.get_event(event_id)
        if not event:
            await interaction.response.send_message("Event not found.")
            return
        if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("You do not have permission to delete this event.")
            return
        await self.delete_event(event_id)
        await interaction.response.send_message(f"Event {event_id} has been deleted.")

    async def delete_event(self, event_id: int):
        """Delete an event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.delete_event(event_id)

async def setup(bot):
    await bot.add_cog(DeleteEventCommand(bot))
