import discord
from discord.ext import commands
from discord import app_commands

from utils.data import load_json, save_json
from utils.permissions import is_staff, is_owner
from utils.data import load_json, save_json

CART_FILE = "data/carts.json"
PRODUCTS_FILE = "data/products.json"
TICKETS_FILE = "data/tickets.json"
DISCOUNTS_FILE = "data/discounts.json"


def get_cart(user_id):
    carts = load_json(CART_FILE)
    return carts.get(str(user_id), {})


def save_cart(user_id, cart):
    carts = load_json(CART_FILE)
    carts[str(user_id)] = cart
    save_json(CART_FILE, carts)


def get_ticket(channel_id):
    return load_json(TICKETS_FILE).get(str(channel_id))


def get_discount(channel_id):
    return load_json(DISCOUNTS_FILE).get(str(channel_id), 0)


class Cart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------
    # Utility: Check if command allowed outside ticket
    # ------------------------------------------------------------
    async def allowed_here(self, interaction: discord.Interaction):
        # staff can use anywhere
        if await is_staff(interaction):
            return True

        # regular users must be inside ticket
        if get_ticket(interaction.channel.id):
            return True

        return False

    # ------------------------------------------------------------
    # /cart view — View your cart
    # ------------------------------------------------------------
    @app_commands.command(
        name="cart_view",
        description="View your cart contents."
    )
    async def cart_view(self, interaction: discord.Interaction):
        if not await self.allowed_here(interaction):
            return await interaction.response.send_message(
                "❌ You can only use this command inside your ticket.",
                ephemeral=True,
            )

        cart = get_cart(interaction.user.id)

        if not cart:
            return await interaction.response.send_message(
                "🛒 Your cart is empty.",
                ephemeral=True,
            )

        products = load_json(PRODUCTS_FILE)
        embed = discord.Embed(
            title="🛒 Your Cart",
            color=discord.Color.blurple()
        )

        total = 0

        for product_id, amount in cart.items():
            product = products.get(product_id)
            if not product:
                continue

            embed.add_field(
                name=product["name"],
                value=f"Quantity: **{amount}**\nPrice: **{product['price']}** each",
                inline=False
            )

            total += product["price"] * amount

        # Apply discount
        discount = get_discount(interaction.channel.id)
        final = max(0, total - discount)

        embed.add_field(name="Subtotal", value=f"💰 {total}", inline=False)
        embed.add_field(name="Discount", value=f"💲 {discount}", inline=False)
        embed.add_field(name="Total", value=f"✅ {final}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------
    # /cart_other — staff view someone else’s cart
    # ------------------------------------------------------------
    @app_commands.command(
        name="cart_other",
        description="(Staff) View another user's cart."
    )
    @app_commands.check(is_staff)
    async def cart_other(self, interaction: discord.Interaction, user: discord.User):
        cart = get_cart(user.id)
        products = load_json(PRODUCTS_FILE)

        embed = discord.Embed(
            title=f"🛒 Cart of {user}",
            color=discord.Color.gold()
        )

        if not cart:
            embed.description = "Cart is empty."
            return await interaction.response.send_message(embed=embed)

        total = 0
        for product_id, amount in cart.items():
            product = products.get(product_id)
            if not product:
                continue

            embed.add_field(
                name=product["name"],
                value=f"Quantity: **{amount}**\nPrice: **{product['price']}** each",
                inline=False
            )

            total += product["price"] * amount

        embed.add_field(name="Subtotal", value=f"💰 {total}", inline=False)

        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------
    # /cart_remove — Remove item by product_id
    # ------------------------------------------------------------
    @app_commands.command(
        name="cart_remove",
        description="Remove a product from your cart using its product ID."
    )
    async def cart_remove(self, interaction: discord.Interaction, product_id: str):
        if not await self.allowed_here(interaction):
            return await interaction.response.send_message(
                "❌ You can only use this inside your ticket.",
                ephemeral=True
            )

        cart = get_cart(interaction.user.id)

        if product_id not in cart:
            return await interaction.response.send_message(
                "❌ That product is not in your cart.",
                ephemeral=True
            )

        del cart[product_id]
        save_cart(interaction.user.id, cart)

        await interaction.response.send_message(
            "🗑 Removed item from your cart.",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # /cart_clear — Clear your cart
    # ------------------------------------------------------------
    @app_commands.command(
        name="cart_clear",
        description="Clear your entire cart."
    )
    async def cart_clear(self, interaction: discord.Interaction):
        if not await self.allowed_here(interaction):
            return await interaction.response.send_message(
                "❌ You can only use this inside your ticket.",
                ephemeral=True
            )

        save_cart(interaction.user.id, {})

        await interaction.response.send_message(
            "🧹 Cleared your cart.",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # /cart_checkout — shows final price, payment methods
    # ------------------------------------------------------------
    @app_commands.command(
        name="cart_checkout",
        description="Checkout — shows total and payment instructions."
    )
    async def cart_checkout(self, interaction: discord.Interaction):
        if not await self.allowed_here(interaction):
            return await interaction.response.send_message(
                "❌ You can only use this inside your ticket.",
                ephemeral=True
            )

        cart = get_cart(interaction.user.id)
        if not cart:
            return await interaction.response.send_message(
                "❌ Your cart is empty.",
                ephemeral=True
            )

        products = load_json(PRODUCTS_FILE)
        ticket = get_ticket(interaction.channel.id)

        if not ticket:
            return await interaction.response.send_message(
                "❌ This is not a ticket.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="💳 Checkout",
            color=discord.Color.green()
        )

        total = 0
        payment_methods = set()

        for product_id, amount in cart.items():
            product = products.get(product_id)
            if not product:
                continue

            line_total = product["price"] * amount
            total += line_total

            embed.add_field(
                name=product["name"],
                value=f"{amount} × {product['price']} = **{line_total}**",
                inline=False
            )

            for m in product["payment_methods"]:
                payment_methods.add(m)

        discount = get_discount(interaction.channel.id)
        final = max(0, total - discount)

        embed.add_field(name="Subtotal", value=f"💰 {total}", inline=False)
        embed.add_field(name="Discount", value=f"💲 {discount}", inline=False)
        embed.add_field(name="Total Due", value=f"✅ {final}", inline=False)
        embed.add_field(
            name="Accepted Payments",
            value="\n".join(payment_methods) or "No methods configured",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(Cart(bot))
