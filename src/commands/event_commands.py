from datetime import datetime
import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
from utils.permissions import has_event_permission
import json
import os
from events.views import EventSignupView, EventManagementView  

class EventManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.load_templates()

    def load_templates(self):
        self.templates = {}
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

    @commands.command(name='create')
    @commands.has_permissions(administrator=True)
    async def create(self, ctx):
        """Start the event creation process via DM"""
        user = ctx.author
        try:
            await user.send("Let's create a new event! What would you like to name it?")
        except discord.Forbidden:
            await ctx.send("I can't send you a DM. Please check your privacy settings.")
            return

        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)

        try:
            name_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            name = name_msg.content
            print(f"Event name: {name}")
            await user.send("Please provide a description for the event.")
            description_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            description = description_msg.content
            print(f"Event description: {description}")
            await user.send("When will the event start? (Format: YYYY-MM-DD HH:MM)")
            start_date_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            start_date = start_date_msg.content
            print(f"Event start date: {start_date}")
            await user.send("Do you want to use a template for this event? (yes/no)")
            template_choice_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            template_choice = template_choice_msg.content.lower()
            print(f"Template choice: {template_choice}")
            template_name = None
            if template_choice == 'yes':
                await user.send("Please provide the template name.")
                template_name_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                template_name = template_name_msg.content
                print(f"Template name: {template_name}")

            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
            except ValueError:
                await user.send("Invalid date format. Please use YYYY-MM-DD HH:MM")
                return

            if template_name and template_name not in self.templates:
                await user.send(f"Template '{template_name}' not found")
                return

            event_id = self.db.create_event(
                guild_id=ctx.guild.id,
                creator_id=ctx.author.id,
                name=name,
                description=description,
                start_date=start_date,
                template_name=template_name
            )
            print(f"Event created with ID: {event_id}")
            await user.send(f"Event created successfully! Event ID: {event_id}")

            # Post the event to the channel with interactive buttons
            settings = self.db.get_guild_settings(ctx.guild.id)
            if settings and 'listening_channel' in settings:
                channel = self.bot.get_channel(settings['listening_channel'])
                if channel:
                    embed = await self.get_event_embed(event_id)
                    view = EventSignupView(self, event_id)
                    await channel.send(embed=embed, view=view)
                    print(f"Event posted to channel {channel.name} with ID {channel.id}")
                else:
                    print(f"Channel with ID {settings['listening_channel']} not found")
            else:
                print(f"Listening channel not set for guild {ctx.guild.id}")

        except TimeoutError:
            await user.send("Event creation timed out. Please try again.")

    @app_commands.command(name='create_event', description='Create a new event')
    @app_commands.default_permissions(administrator=True)
    async def create_event(self, interaction: discord.Interaction):
        await self.create(interaction)

    async def edit_event(self, event_id: int, **kwargs):
        """Edit an existing event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, **kwargs)

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

    async def open_event(self, event_id: int):
        """Reopen a closed event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.update_event(event_id, status='open')

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

    async def delete_event(self, event_id: int):
        """Delete an event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.delete_event(event_id)

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

    async def add_participant(self, event_id: int, user_id: int, role_name: str):
        """Add a participant to an event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        if event['status'] != 'open':
            raise ValueError("Event is not open for registration")
        template = self.templates.get(event['template_name'])
        if template:
            if role_name not in template['roles']:
                raise ValueError(f"Invalid role: {role_name}")
            current_participants = self.db.get_participants(event_id)
            role_count = len([p for p in current_participants if p['role_name'] == role_name])
            if role_count >= template['roles'][role_name]['limit']:
                raise ValueError(f"Role {role_name} is full")
        self.db.add_participant(event_id, user_id, role_name)

    async def remove_participant(self, event_id: int, user_id: int):
        """Remove a participant from an event"""
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        self.db.remove_participant(event_id, user_id)

    async def get_event_embed(self, event_id: int):
        """Create a Discord embed for an event"""
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
        if event['template_name'] and event['template_name'] in self.templates:
            template = self.templates[event['template_name']]
            for role_name, role_info in template['roles'].items():
                role_participants = [p for p in participants if p['role_name'] == role_name]
                participant_list = [f"<@{p['user_id']}>" for p in role_participants]
                remaining = role_info['limit'] - len(role_participants)
                embed.add_field(
                    name=f"{role_info['emoji']} {role_name} ({len(role_participants)}/{role_info['limit']})",
                    value='\n'.join(participant_list) if participant_list else "No participants",
                    inline=False
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

    async def handle_signup(self, interaction: discord.Interaction, event_id: int, role_name: str):
        try:
            user_id = interaction.user.id
            # Check if user is already signed up
            participants = self.db.get_participants(event_id)
            if any(p['user_id'] == user_id for p in participants):
                await interaction.response.send_message(
                    "You are already signed up for this event. Cancel your current signup first.",
                    ephemeral=True
                )
                return
            await self.add_participant(event_id, user_id, role_name)
            # Update the event embed
            embed = await self.get_event_embed(event_id)
            message = interaction.message
            await message.edit(embed=embed)
            await interaction.response.send_message(
                f"You have successfully signed up as {role_name}.",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            print(f"Error in handle_signup: {e}")
            await interaction.response.send_message(
                "An error occurred while signing up.",
                ephemeral=True
            )

    async def handle_cancel(self, interaction: discord.Interaction):
        try:
            event_id = int(interaction.data['custom_id'].split('_')[1])
            user_id = interaction.user.id
            # Check if user is actually signed up
            participants = self.db.get_participants(event_id)
            if not any(p['user_id'] == user_id for p in participants):
                await interaction.response.send_message(
                    "You are not signed up for this event.",
                    ephemeral=True
                )
                return
            await self.remove_participant(event_id, user_id)
            # Update the event embed
            embed = await self.get_event_embed(event_id)
            message = interaction.message
            await message.edit(embed=embed)
            await interaction.response.send_message(
                "You have successfully canceled your sign up.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error in handle_cancel: {e}")
            await interaction.response.send_message(
                "An error occurred while canceling your sign up.",
                ephemeral=True
            )

    async def handle_edit(self, interaction: discord.Interaction):
        try:
            event_id = int(interaction.data['custom_id'].split('_')[1])
            event = self.db.get_event(event_id)
            if not event:
                await interaction.response.send_message(
                    "Event not found.",
                    ephemeral=True
                )
                return
            if interaction.user.id != event['creator_id'] and interaction.user.id != self.bot.owner_id:
                await interaction.response.send_message(
                    "You do not have permission to edit this event.",
                    ephemeral=True
                )
                return
            user = interaction.user
            await user.send("Let's edit the event. What would you like to change? (name, description, start_date)")
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)
            try:
                field_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                field = field_msg.content.lower()
                if field == 'name':
                    await user.send("Please provide the new name for the event.")
                    name_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                    name = name_msg.content
                    await self.edit_event(event_id, name=name)
                elif field == 'description':
                    await user.send("Please provide the new description for the event.")
                    description_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                    description = description_msg.content
                    await self.edit_event(event_id, description=description)
                elif field == 'start_date':
                    await user.send("Please provide the new start date for the event. (Format: YYYY-MM-DD HH:MM)")
                    start_date_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                    start_date = start_date_msg.content
                    try:
                        start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
                        await self.edit_event(event_id, start_date=start_date)
                    except ValueError:
                        await user.send("Invalid date format. Please use YYYY-MM-DD HH:MM")
                        return
                else:
                    await user.send("Invalid field. Please try again.")
                    return
                await user.send("Event updated successfully!")
                # Update the event embed
                embed = await self.get_event_embed(event_id)
                message = interaction.message
                await message.edit(embed=embed)
            except TimeoutError:
                await user.send("Event edit timed out. Please try again.")
        except Exception as e:
            print(f"Error in handle_edit: {e}")
            await interaction.response.send_message(
                "An error occurred while editing the event.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(EventManager(bot))
