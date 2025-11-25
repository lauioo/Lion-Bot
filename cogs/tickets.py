# cogs/tickets.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from typing import Optional

# Utilities (assumes these helper modules/files exist in your project)
from utils.permissions import require_staff, require_allowed_guild, require_owner
from utils.data import load_json, save_json

# Data files
TICKETS_FILE = "data/tickets.json"
TICKET_COUNTER_FILE = "data/ticket_counter.json"
CONFIG_FILE = "data/config.json"

# Local example image (developer-provided upload)
LOCAL_EXAMPLE_IMAGE = "/mnt/data/7266CE9E-16F0-4545-B6C7-AD57CCB09992.jpeg"

# Ensure data files exist
for f, default in [
    (TICKETS_FILE, "{}"),
    (TICKET_COUNTER_FILE, json.dumps({"count": 0})),
    (CONFIG_FILE, json.dumps({"staff_roles": [], "ticket_category": None}))
]:
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(default)


def load_tickets() -> dict:
    return load_json(TICKETS_FILE)


def save_tickets(data: dict):
    save_json(TICKETS_FILE, data)


def load_counter() -> dict:
    return load_json(TICKET_COUNTER_FILE)


def save_counter(data: dict):
    save_json(TICKET_COUNTER_FILE, data)


def load_config() -> dict:
    return load_json(CONFIG_FILE)


def save_config(cfg: dict):
    save_json(CONFIG_FILE, cfg)


class Tickets(commands.Cog):
    """Ticket creation and management (create, mark paid, delivered, set category)."""

    def __init__(self, bot):
        self.bot = bot

    # -------------------------
    # Helpers
    # -------------------------
    def next_ticket_number(self) -> int:
        counter = load_counter()
        cnt = int(counter.get("count", 0)) + 1
        counter["count"] = cnt
        save_counter(counter)
        return cnt

    def store_ticket(self, channel: discord.TextChannel, buyer: discord.Member, number: int):
        tickets = load_tickets()
        tickets[str(channel.id)] = {
            "buyer_id": buyer.id,
            "number": number,
            "status": "open",
            "delivered": False,
            "discount": 0
        }
        save_tickets(tickets)

    def get_ticket_by_channel(self, channel: discord.TextChannel) -> Optional[dict]:
        tickets = load_tickets()
        return tickets.get(str(channel.id))

    def update_ticket(self, channel: discord.TextChannel, data: dict):
        tickets = load_tickets()
        tickets[str(channel.id)] = data
        save_tickets(tickets)

    def remove_ticket(self, channel: discord.TextChannel):
        tickets = load_tickets()
        if str(channel.id) in tickets:
            del tickets[str(channel.id)]
            save_tickets(tickets)

    # -------------------------
    # /ticket new
    # -------------------------
    @app_commands.command(name="ticket_new", description="Create a new purchase ticket (private channel).")
    @require_allowed_guild()
    async def ticket_new(self, interaction: discord.Interaction):
        """
        Creates a private ticket channel named ticket-<n>. Stores ticket info in data/tickets.json.
        """
        await interaction.response.defer(ephemeral=True)

        cfg = load_config()
        category_id = cfg.get("ticket_category")
        category = None
        if category_id:
            category = interaction.guild.get_channel(category_id)
            # ensure category exists and is a CategoryChannel
            if category is None or not isinstance(category, discord.CategoryChannel):
                category = None

        ticket_number = self.next_ticket_number()
        channel_name = f"ticket-{ticket_number}"

        # Build permissions: hide from @everyone, show to buyer and staff roles
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        # Add staff roles if present in config
        staff_roles = cfg.get("staff_roles", [])
        for rid in staff_roles:
            role = interaction.guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"Ticket created by {interaction.user} ({interaction.user.id})"
        )

        # Save ticket record
        self.store_ticket(channel, interaction.user, ticket_number)

        # Ping staff roles (if any) and notify buyer
        staff_mentions = " ".join([f"<@&{rid}>" for rid in staff_roles]) if staff_roles else ""
        embed = discord.Embed(
            title="🛒 Purchase Ticket Created",
            description=(
                f"Buyer: {interaction.user.mention}\n"
                f"Ticket Number: **{ticket_number}**\n\n"
                "A staff member will assist you shortly."
            ),
            color=discord.Color.green()
        )
        # Use example image if available for a nicer embed (non-critical)
        embed.set_thumbnail(url=LOCAL_EXAMPLE_IMAGE)

        await channel.send(content=staff_mentions or None, embed=embed)
        await interaction.followup.send(f"🎫 Ticket created: {channel.mention}", ephemeral=True)

    # -------------------------
    # /ticket_paid
    # -------------------------
    @app_commands.command(name="ticket_paid", description="Mark this ticket as paid (staff only).")
    @require_staff()
    async def ticket_paid(self, interaction: discord.Interaction):
        """
        Staff command to mark the current ticket as paid. Renames channel to paid-<n>.
        """
        await interaction.response.defer(ephemeral=True)

        ticket = self.get_ticket_by_channel(interaction.channel)
        if not ticket:
            return await interaction.followup.send("❌ This channel is not a stored ticket.", ephemeral=True)

        # rename channel
        number = ticket.get("number")
        new_name = f"paid-{number}"
        try:
            await interaction.channel.edit(name=new_name)
        except Exception:
            pass

        ticket["status"] = "paid"
        self.update_ticket(interaction.channel, ticket)

        await interaction.followup.send(f"✅ Ticket {number} marked as **paid**.", ephemeral=True)

    # -------------------------
    # /ticket_delivered
    # -------------------------
    @app_commands.command(name="ticket_delivered", description="Mark this ticket as delivered (staff only).")
    @require_staff()
    async def ticket_delivered(self, interaction: discord.Interaction):
        """
        Staff command to mark ticket delivered. Renames channel to delivered-<n>.
        """
        await interaction.response.defer(ephemeral=True)

        ticket = self.get_ticket_by_channel(interaction.channel)
        if not ticket:
            return await interaction.followup.send("❌ This channel is not a stored ticket.", ephemeral=True)

        number = ticket.get("number")
        new_name = f"delivered-{number}"
        try:
            await interaction.channel.edit(name=new_name)
        except Exception:
            pass

        ticket["status"] = "delivered"
        ticket["delivered"] = True
        self.update_ticket(interaction.channel, ticket)

        await interaction.followup.send(f"📦 Ticket {number} marked as **delivered**.", ephemeral=True)

    # -------------------------
    # /ticket_setcategory
    # -------------------------
    @app_commands.command(name="ticket_setcategory", description="Set the category where new tickets are created (staff only).")
    @require_staff()
    async def ticket_setcategory(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """
        Configure the category where tickets will be created.
        """
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        cfg["ticket_category"] = category.id
        save_config(cfg)
        await interaction.followup.send(f"✅ Ticket category set to **{category.name}**.", ephemeral=True)

    # -------------------------
    # /ticket_checkpayment (placeholder for webhook / auto-detect)
    # -------------------------
    @app_commands.command(name="ticket_checkpayment", description="(Placeholder) Check external payment status for this ticket.")
    @require_staff()
    async def ticket_checkpayment(self, interaction: discord.Interaction):
        """
        Placeholder command to demonstrate where auto-detection / webhook logic can be hooked.
        This currently simulates checking an external API or webhook and returns 'no change'.
        You can later implement a real API check here.
        """
        await interaction.response.defer(ephemeral=True)

        ticket = self.get_ticket_by_channel(interaction.channel)
        if not ticket:
            return await interaction.followup.send("❌ This channel is not a stored ticket.", ephemeral=True)

        # Placeholder: in future, call external API / webhook here
        # Example: result = webhook_payment_check(ticket_id=ticket['number'])
        # If result indicates payment, set ticket['status']="paid" and rename the channel

        # Current behavior: no-op
        await interaction.followup.send("ℹ️ Payment check placeholder executed — no change (manual /webhook integration required).", ephemeral=True)

    # -------------------------
    # /ticket_close
    # -------------------------
    @app_commands.command(name="ticket_close", description="Close and delete this ticket (staff only).")
    @require_staff()
    async def ticket_close(self, interaction: discord.Interaction):
        """
        Closes (deletes) the ticket channel and clears its stored record.
        """
        await interaction.response.defer(ephemeral=True)

        ticket = self.get_ticket_by_channel(interaction.channel)
        if not ticket:
            return await interaction.followup.send("❌ This channel is not a stored ticket.", ephemeral=True)

        # Remove record then delete channel
        self.remove_ticket(interaction.channel)
        await interaction.followup.send("🗑 Closing ticket...", ephemeral=True)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

    # -------------------------
    # Admin: show ticket info
    # -------------------------
    @app_commands.command(name="ticket_info", description="Show stored info for this ticket (staff only).")
    @require_staff()
    async def ticket_info(self, interaction: discord.Interaction):
        ticket = self.get_ticket_by_channel(interaction.channel)
        if not ticket:
            return await interaction.response.send_message("❌ This channel is not a ticket.", ephemeral=True)
        embed = discord.Embed(title=f"Ticket #{ticket.get('number')}", color=discord.Color.blue())
        embed.add_field(name="Buyer ID", value=str(ticket.get("buyer_id")), inline=False)
        embed.add_field(name="Status", value=str(ticket.get("status")), inline=False)
        embed.add_field(name="Delivered", value=str(ticket.get("delivered", False)), inline=False)
        embed.add_field(name="Discount", value=str(ticket.get("discount", 0)), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
