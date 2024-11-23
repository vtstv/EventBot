from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from events.views import EventSignupView

class CreateEventCommand(commands.Cog):
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

    @app_commands.command(name='create_event', description="Create a new event")
    @app_commands.default_permissions(administrator=True)
    async def create_event(self, interaction: discord.Interaction):
        """Start the event creation process via DM"""
        user = interaction.user
        try:
            await user.send("Let's create a new event! What would you like to name it?")
        except discord.Forbidden:
            await interaction.response.send_message("I can't send you a DM. Please check your privacy settings.")
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
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                name=name,
                description=description,
                start_date=start_date,
                template_name=template_name
            )
            print(f"Event created with ID: {event_id}")
            await user.send(f"Event created successfully! Event ID: {event_id}")

            # Post the event to the channel with interactive buttons
            settings = self.db.get_guild_settings(interaction.guild.id)
            if settings and 'listening_channel' in settings:
                channel = self.bot.get_channel(settings['listening_channel'])
                if channel:
                    embed = await self.get_event_embed(event_id)
                    view = EventSignupView(self, event_id)
                    message = await channel.send(embed=embed, view=view)
                    print(f"Event posted to channel {channel.name} with ID {channel.id}")

                    # Create a thread for the event
                    thread = await message.create_thread(name=name)
                    print(f"Thread created for event: {thread.name} with ID {thread.id}")
                else:
                    print(f"Channel with ID {settings['listening_channel']} not found")
            else:
                print(f"Listening channel not set for guild {interaction.guild.id}")

        except asyncio.TimeoutError:
            await user.send("Event creation timed out. Please try again.")

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

async def setup(bot):
    await bot.add_cog(CreateEventCommand(bot))
