from discord.ext import commands
import discord

def is_admin(interaction: discord.Interaction):
    print(f"Checking admin permissions for user: {interaction.user}")
    if interaction.guild is None:
        print("Interaction is not within a guild context.")
        return False
    # Ensure the user is a Member object
    member = interaction.guild.get_member(interaction.user.id)
    if member and member.guild_permissions.administrator:
        print(f"User {interaction.user} is an admin.")
        return True
    print(f"User {interaction.user} is not an admin.")
    return False

def has_event_permission(interaction: discord.Interaction):
    if interaction.guild is None:
        return False
    # Ensure the user is a Member object
    member = interaction.guild.get_member(interaction.user.id)
    # Check for admin permissions
    if member and member.guild_permissions.administrator:
        return True
    # Check for Manager role
    manager_role = discord.utils.get(interaction.guild.roles, name='Manager')
    if manager_role and manager_role in member.roles:
        return True
    return False

def is_event_creator(interaction: discord.Interaction, event_creator_id: int):
    return interaction.user.id == event_creator_id
