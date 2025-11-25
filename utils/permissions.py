import discord
from discord import app_commands
from utils.data import load_json

CONFIG_FILE = "data/config.json"

# ------------------------------------------------------------
# Load config helper
# ------------------------------------------------------------
def get_config():
    return load_json(CONFIG_FILE)


# ------------------------------------------------------------
# OWNER CHECK — owner can use ALL commands regardless of roles
# ------------------------------------------------------------
async def is_owner(interaction: discord.Interaction) -> bool:
    config = get_config()
    owner_id = config.get("owner_id")

    return interaction.user.id == owner_id


# ------------------------------------------------------------
# STAFF CHECK — staff + owner can use Staff commands
# ------------------------------------------------------------
async def is_staff(interaction: discord.Interaction) -> bool:
    config = get_config()

    # Owner bypass
    if interaction.user.id == config.get("owner_id"):
        return True

    staff_roles = config.get("staff_roles", [])

    # Check if member has any staff role
    if any(role.id in staff_roles for role in interaction.user.roles):
        return True

    return False


# ------------------------------------------------------------
# GUILD WHITELIST CHECK
# ------------------------------------------------------------
async def in_allowed_guild(interaction: discord.Interaction) -> bool:
    config = get_config()
    allowed = config.get("allowed_guilds")

    # If no whitelist defined, allow everywhere
    if not allowed:
        return True

    return interaction.guild_id in allowed


# ------------------------------------------------------------
# Decorators for App Commands
# ------------------------------------------------------------
def require_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if await is_owner(interaction):
            return True
        raise app_commands.CheckFailure("You do not have permission to use this command.")
    return app_commands.check(predicate)


def require_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if await is_staff(interaction):
            return True
        raise app_commands.CheckFailure("You do not have permission to use this command.")
    return app_commands.check(predicate)


def require_allowed_guild():
    async def predicate(interaction: discord.Interaction) -> bool:
        if await in_allowed_guild(interaction):
            return True
        raise app_commands.CheckFailure("This bot is not enabled in this server.")
    return app_commands.check(predicate)
