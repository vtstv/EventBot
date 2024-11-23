import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from events.views import EventSignupView

class EditEventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name='edit_event', description='Edit an existing event')
    @app_commands.default_permissions(administrator=True)
    async def edit_event_command(self, interaction: discord.Interaction, event_id: int, field: str, value: str):
        try:
            event = self.db.get_event(event_id)
            if not event:
                await interaction.response.send_message("Event not found.", ephemeral=True)
                return
            
            if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
                await interaction.response.send_message("You do not have permission to edit this event.", ephemeral=True)
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
                    await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD HH:MM", ephemeral=True)
                    return
            else:
                await interaction.response.send_message("Invalid field. Please try again.", ephemeral=True)
                return

            settings = self.db.get_guild_settings(interaction.guild.id)
            if not settings or 'listening_channel' not in settings:
                await interaction.response.send_message("Listening channel not set for this guild.", ephemeral=True)
                return

            channel = self.bot.get_channel(settings['listening_channel'])
            if not channel:
                await interaction.response.send_message("Listening channel not found.", ephemeral=True)
                return

            message = None
            message_id = self.db.get_event_message_id(event_id)
            
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    message = await self.find_event_message(channel, event_id)
            else:
                message = await self.find_event_message(channel, event_id)

            new_content = await self.format_event_message(event_id)
            
            if message:
                self.db.store_event_message_id(event_id, message.id)
                # Create new view and preserve the signup functionality
                view = EventSignupView(self.bot.get_cog('CreateEventCommand'), event_id, self.bot.templates)
                await message.edit(content=new_content, view=view)
                await interaction.response.send_message("Event updated successfully!", ephemeral=True)
            else:
                # Create new message with view
                view = EventSignupView(self.bot.get_cog('CreateEventCommand'), event_id, self.bot.templates)
                new_message = await channel.send(content=new_content, view=view)
                self.db.store_event_message_id(event_id, new_message.id)
                await interaction.response.send_message("Created a new event message.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    async def edit_event(self, event_id: int, **kwargs):
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, **kwargs)

    async def format_event_message(self, event_id: int) -> str:
        """Format event information as a text message"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        
        message_parts = [
            f"📅 **{event['name']}**\n",
            f"{event['description']}\n",
            f"🕒 Start: {event['start_date'].strftime('%Y-%m-%d %H:%M')}\n"
        ]

        participants = self.db.get_participants(event_id)
        
        if event['template_name'] and event['template_name'] in self.bot.templates:
            template = self.bot.templates[event['template_name']]
            message_parts.append("\n**Roles:**")
            
            for role_name, role_info in template['roles'].items():
                role_participants = [p for p in participants if p['role_name'] == role_name]
                participant_list = [f"<@{p['user_id']}>" for p in role_participants]
                remaining = role_info['limit'] - len(role_participants)
                
                message_parts.append(
                    f"\n{role_info['emoji']} {role_name} ({len(role_participants)}/{role_info['limit']})"
                )
                if participant_list:
                    message_parts.append("→ " + ", ".join(participant_list))
                else:
                    message_parts.append("→ No participants")
        else:
            message_parts.append(f"\n**Participants ({len(participants)}):**")
            if participants:
                participant_list = [f"<@{p['user_id']}>" for p in participants]
                message_parts.append("→ " + ", ".join(participant_list))
            else:
                message_parts.append("→ No participants yet")

        message_parts.append(f"\n📝 Event ID: {event_id} | Status: {event['status']}")
        
        return "\n".join(message_parts)

    async def find_event_message(self, channel, event_id):
        try:
            async for message in channel.history(limit=100):
                if f"Event ID: {event_id}" in message.content:
                    return message
            return None
        except discord.Forbidden:
            raise ValueError("Bot doesn't have permission to read message history")
        except Exception as e:
            raise ValueError(f"Error searching for event message: {str(e)}")

async def setup(bot):
    await bot.add_cog(EditEventCommand(bot))