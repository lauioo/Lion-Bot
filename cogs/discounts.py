import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import is_staff, is_owner
from utils.data import load_json, save_json

DISCOUNTS_FILE = "data/discounts.json"
TICKETS_FILE = "data/tickets.json"


class Discounts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------
    # Utility Functions
    # ------------------------------------------------------------
    def get_discounts(self):
        return load_json(DISCOUNTS_FILE)

    def save_discounts(self, data):
        save_json(DISCOUNTS_FILE, data)

    def get_ticket(self, channel_id):
        return load_json(TICKETS_FILE).get(str(channel_id))

    # ------------------------------------------------------------
    # /discount set — sets a discount for this ticket
    # ------------------------------------------------------------
    @app_commands.command(
        name="discount_set",
        description="Set a discount amount for this ticket. (Staff Only)"
    )
    @app_commands.check(is_staff)
    async def discount_set(self, interaction: discord.Interaction, amount: int):
        ticket = self.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "❌ This is not a ticket.",
                ephemeral=True
            )

        if amount < 0:
            return await interaction.response.send_message(
                "❌ Discount cannot be negative.",
                ephemeral=True
            )

        discounts = self.get_discounts()
        discounts[str(interaction.channel.id)] = amount
        self.save_discounts(discounts)

        await interaction.response.send_message(
            f"💲 Set a **{amount}** discount for this ticket.",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # /discount_clear — removes discount for the ticket
    # ------------------------------------------------------------
    @app_commands.command(
        name="discount_clear",
        description="Clear the discount applied to this ticket. (Staff Only)"
    )
    @app_commands.check(is_staff)
    async def discount_clear(self, interaction: discord.Interaction):
        ticket = self.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "❌ This is not a ticket.",
                ephemeral=True
            )

        discounts = self.get_discounts()

        if str(interaction.channel.id) in discounts:
            del discounts[str(interaction.channel.id)]
            self.save_discounts(discounts)

        await interaction.response.send_message(
            "🗑 Cleared the discount for this ticket.",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # /discount_view — shows current ticket discount
    # ------------------------------------------------------------
    @app_commands.command(
        name="discount_view",
        description="View the discount applied to this ticket. (Staff Only)"
    )
    @app_commands.check(is_staff)
    async def discount_view(self, interaction: discord.Interaction):
        ticket = self.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "❌ This is not a ticket.",
                ephemeral=True
            )

        discounts = self.get_discounts()
        discount = discounts.get(str(interaction.channel.id), 0)

        await interaction.response.send_message(
            f"💲 Current discount: **{discount}**",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Discounts(bot))
