import discord
from discord.ext import commands
from discord import app_commands

class CloseEventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name='close_event', description='Close an event')
    @app_commands.default_permissions(administrator=True)
    async def close_event_command(self, interaction: discord.Interaction, event_id: int):
        event = self.db.get_event(event_id)
        if not event:
            await interaction.response.send_message("Event not found.")
            return
        if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("You do not have permission to close this event.")
            return
        await self.close_event(event_id, notify=True)
        await interaction.response.send_message(f"Event {event_id} has been closed.")

    async def close_event(self, event_id: int, notify: bool = False):
        """Close an event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, status='closed')
        if notify:
            participants = self.db.get_participants(event_id)
            for participant in participants:
                user = self.bot.get_user(participant['user_id'])
                if user:
                    try:
                        await user.send(f"Event '{event['name']}' has been closed.")
                    except discord.Forbidden:
                        pass  # Cannot send DM to user

async def setup(bot):
    await bot.add_cog(CloseEventCommand(bot))
