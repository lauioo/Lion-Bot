import discord
from discord.ext import commands
from discord import app_commands
import json
import os

OWNER_ID = int(os.getenv("OWNER_ID"))

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(self, user: discord.Member):
        if user.id == OWNER_ID:
            return True
        config = load_config()
        staff_ids = config["staff_roles"]
        return any(role.id in staff_ids for role in user.roles)

    async def interaction_check(self, interaction: discord.Interaction):
        return True

    @app_commands.command(
        name="staff_addrole",
        description="Adds a role to the staff whitelist."
    )
    async def staff_addrole(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You cannot use this.", ephemeral=True)

        if role.id not in config["staff_roles"]:
            config["staff_roles"].append(role.id)
            save_config(config)

        await interaction.response.send_message(f"✅ Added {role.mention} as staff.", ephemeral=True)

    @app_commands.command(
        name="staff_removerole",
        description="Removes a staff role from whitelist."
    )
    async def staff_removerole(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You cannot use this.", ephemeral=True)

        if role.id in config["staff_roles"]:
            config["staff_roles"].remove(role.id)
            save_config(config)

        await interaction.response.send_message(f"🗑 Removed {role.mention} from staff.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Permissions(bot))
