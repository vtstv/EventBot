import discord
from discord.ext import commands
from discord import app_commands

class EditEventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name='edit_event', description='Edit an existing event')
    @app_commands.default_permissions(administrator=True)
    async def edit_event_command(self, interaction: discord.Interaction, event_id: int, field: str, value: str):
        event = self.db.get_event(event_id)
        if not event:
            await interaction.response.send_message("Event not found.")
            return
        if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("You do not have permission to edit this event.")
            return
        if field == 'name':
            await self.edit_event(event_id, name=value)
        elif field == 'description':
            await self.edit_event(event_id, description=value)
        elif field == 'start_date':
            try:
                start_date = datetime.strptime(value, '%Y-%m-%d %H:%M')
                await self.edit_event(event_id, start_date=start_date)
            except ValueError:
                await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD HH:MM")
                return
        else:
            await interaction.response.send_message("Invalid field. Please try again.")
            return
        await interaction.response.send_message("Event updated successfully!")

    async def edit_event(self, event_id: int, **kwargs):
        """Edit an existing event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, **kwargs)

async def setup(bot):
    await bot.add_cog(EditEventCommand(bot))
