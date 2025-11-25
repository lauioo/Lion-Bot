import discord
from discord.ext import commands
import os
import json

INTENTS = discord.Intents.default()
INTENTS.message_content = False

OWNER_ID = int(os.getenv("OWNER_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

ALLOWED_GUILDS = [
    1431698219892478074,
    1441231445283704943
]

class ShopBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            application_id=os.getenv("APPLICATION_ID")
        )

    async def setup_hook(self):
        for guild_id in ALLOWED_GUILDS:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)

        # Load cogs
        await self.load_extension("cogs.permissions")
        await self.load_extension("cogs.products")
        await self.load_extension("cogs.cart")
        await self.load_extension("cogs.tickets")
        await self.load_extension("cogs.discounts")

        for guild_id in ALLOWED_GUILDS:
            await self.tree.sync(guild=discord.Object(id=guild_id))

    async def on_guild_join(self, guild):
        if guild.id not in ALLOWED_GUILDS:
            await guild.leave()

bot = ShopBot()

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

bot.run(BOT_TOKEN)
