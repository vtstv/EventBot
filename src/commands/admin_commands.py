import discord
from discord import app_commands
from discord.ext import commands
from utils.permissions import is_admin

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='settings')
    @app_commands.check(is_admin)
    async def settings(self, interaction: discord.Interaction):
        """Manage server-specific settings"""
        # Create settings menu
        pass

    @app_commands.command(name='setup')
    @app_commands.check(is_admin)
    async def setup(self, interaction: discord.Interaction):
        """Initial bot setup"""
        print(f"Received setup command from {interaction.user}")
        await interaction.response.send_message("Please specify the channel where the bot should listen for commands!", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            print("Waiting for channel message...")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            channel_id = int(msg.content.strip('<>#'))
            # Save channel settings to the database
            self.bot.db.update_guild_settings(interaction.guild.id, listening_channel=channel_id)
            print(f"Channel ID received: {channel_id}")
            await interaction.followup.send(f"Bot will now listen to <#{channel_id}>", ephemeral=True)
        except asyncio.TimeoutError:
            print("Setup timed out.")
            await interaction.followup.send("Setup timed out. Please try again.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
