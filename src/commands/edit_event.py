import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

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

            new_embed = await self.get_event_embed(event_id)
            
            if message:
                self.db.store_event_message_id(event_id, message.id)
                await message.edit(embed=new_embed)
                await interaction.response.send_message("Event updated successfully!", ephemeral=True)
            else:
                new_message = await channel.send(embed=new_embed)
                self.db.store_event_message_id(event_id, new_message.id)
                await interaction.response.send_message("Created a new event message.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    async def edit_event(self, event_id: int, **kwargs):
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, **kwargs)

    async def get_event_embed(self, event_id: int):
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        embed = discord.Embed(
            title=event['name'],
            description=event['description'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Time",
            value=f"Start: {event['start_date'].strftime('%Y-%m-%d %H:%M')}",
            inline=False
        )
        participants = self.db.get_participants(event_id)
        if event['template_name'] and event['template_name'] in self.bot.templates:
            template = self.bot.templates[event['template_name']]
            for role_name, role_info in template['roles'].items():
                role_participants = [p for p in participants if p['role_name'] == role_name]
                participant_list = [f"<@{p['user_id']}>" for p in role_participants]
                remaining = role_info['limit'] - len(role_participants)
                embed.add_field(
                    name=f"{role_info['emoji']} {role_name} ({len(role_participants)}/{role_info['limit']})",
                    value='\n'.join(participant_list) if participant_list else "No participants",
                    inline=True
                )
        else:
            participant_list = [f"<@{p['user_id']}>" for p in participants]
            embed.add_field(
                name=f"Participants ({len(participants)})",
                value='\n'.join(participant_list) if participant_list else "No participants",
                inline=False
            )
        embed.set_footer(text=f"Event ID: {event_id} | Status: {event['status']}")
        return embed

    async def find_event_message(self, channel, event_id):
        try:
            async for message in channel.history(limit=100):
                if message.embeds and message.embeds[0].footer.text.startswith(f"Event ID: {event_id}"):
                    return message
            return None
        except discord.Forbidden:
            raise ValueError("Bot doesn't have permission to read message history")
        except Exception as e:
            raise ValueError(f"Error searching for event message: {str(e)}")

async def setup(bot):
    await bot.add_cog(EditEventCommand(bot))