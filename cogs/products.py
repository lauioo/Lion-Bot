# cogs/products.py
import discord
from discord.ext import commands
from discord import app_commands
import os
from typing import List, Optional
from utils.data import load_json, save_json
from utils.permissions import require_staff, require_allowed_guild

# Files
DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
CONFIG_FILE = "config.json"   # project-level config (root)
# Example local uploaded image path (developer note / for testing)
LOCAL_EXAMPLE_IMAGE = "/mnt/data/7266CE9E-16F0-4545-B6C7-AD57CC09992.jpeg"

# Helpers for JSON
def load_products() -> List[dict]:
    data = load_json(PRODUCTS_FILE)
    # ensure list format
    if isinstance(data, dict):
        # legacy guard: if someone accidentally saved a dict, convert to list
        return list(data.values())
    return data or []

def save_products(products: List[dict]):
    save_json(PRODUCTS_FILE, products)

def load_config() -> dict:
    cfg = load_json(CONFIG_FILE)
    if not isinstance(cfg, dict):
        return {}
    return cfg

def save_config(cfg: dict):
    save_json(CONFIG_FILE, cfg)


class Products(commands.Cog):
    """Product management: add/list/edit/remove products and payment methods."""

    def __init__(self, bot):
        self.bot = bot

    # ----------------------------
    # Utility: embed generation
    # ----------------------------
    def product_embed(self, product: dict) -> discord.Embed:
        title = f"🛍️ {product.get('name', 'Item')}"
        embed = discord.Embed(title=title, color=discord.Color.blurple())
        embed.add_field(name="Price", value=f"${float(product.get('price', 0)):.2f}", inline=True)
        embed.add_field(name="Stock", value=str(product.get("stock", "∞")), inline=True)
        if product.get("description"):
            embed.description = product["description"]
        if product.get("discount_percent", 0):
            embed.add_field(name="Discount", value=f"{product['discount_percent']}% off", inline=False)
        if product.get("payment_methods"):
            embed.add_field(name="Payment methods", value=", ".join(product["payment_methods"]), inline=False)
        if product.get("image"):
            embed.set_image(url=product["image"])
        return embed

    # ----------------------------
    # Utility: forward attachment to storage channel
    # ----------------------------
    async def forward_attachment_to_storage_channel(self, guild: discord.Guild, attachment: discord.Attachment) -> Optional[str]:
        """
        If config.image_storage_channel exists and bot can access it, re-upload the file there
        and return the CDN URL. Otherwise return None.
        """
        cfg = load_config()
        storage_chan_id = cfg.get("image_storage_channel")
        if not storage_chan_id:
            return None

        storage_channel = guild.get_channel(storage_chan_id)
        if storage_channel is None:
            return None

        try:
            # read bytes and send as discord.File to storage channel
            data = await attachment.read()
            filename = attachment.filename or f"product_{attachment.id}"
            # discord.File expects a file-like; use BytesIO
            from io import BytesIO
            b = BytesIO(data)
            discord_file = discord.File(fp=b, filename=filename)
            sent = await storage_channel.send(file=discord_file)
            if sent.attachments:
                return sent.attachments[0].url
        except Exception:
            # fallback to None if anything fails
            return None
        return None

    # ----------------------------
    # /product add
    # ----------------------------
    @app_commands.command(name="add", description="Add a product (image attachment required).")
    @require_allowed_guild()
    @require_staff()
    async def add(self,
                  interaction: discord.Interaction,
                  name: str,
                  price: float,
                  stock: int,
                  description: str,
                  image: discord.Attachment):
        """
        Add a product. The image parameter must be provided (attach file in the command).
        If `image_storage_channel` is configured in config.json, the attachment will be forwarded there
        and the bot will save the stored CDN URL. Otherwise the attachment.url is used.
        """
        await interaction.response.defer(ephemeral=True)

        if image is None:
            return await interaction.followup.send("❌ You must attach an image file for the product.", ephemeral=True)

        products = load_products()
        new_id = max([p.get("id", 0) for p in products], default=0) + 1

        # Try to forward to storage channel for persistent CDN hosting
        saved_url = await self.forward_attachment_to_storage_channel(interaction.guild, image)
        image_url = saved_url or getattr(image, "url", None) or LOCAL_EXAMPLE_IMAGE

        product = {
            "id": new_id,
            "name": name,
            "description": description,
            "price": round(float(price), 2),
            "stock": int(stock) if stock is not None else None,
            "image": image_url,
            "message_id": None,
            "channel_id": None,
            "payment_methods": [],
            "discount_percent": 0
        }

        products.append(product)
        save_products(products)

        # Post product embed to the current channel
        embed = self.product_embed(product)
        try:
            sent = await interaction.channel.send(embed=embed)
            # save message & channel ids
            for p in products:
                if p["id"] == new_id:
                    p["message_id"] = sent.id
                    p["channel_id"] = sent.channel.id
                    break
            save_products(products)
        except Exception:
            # ignore sending failure
            pass

        await interaction.followup.send(f"✅ Product **{name}** (id {new_id}) added and posted.", ephemeral=True)

    # ----------------------------
    # /product list
    # ----------------------------
    @app_commands.command(name="list", description="Post embed messages for all products.")
    @require_allowed_guild()
    async def list_products(self, interaction: discord.Interaction):
        """List all products by sending their embed messages to the current channel."""
        products = load_products()
        if not products:
            return await interaction.response.send_message("No products available.", ephemeral=True)

        for p in products:
            embed = self.product_embed(p)
            await interaction.channel.send(embed=embed)

        await interaction.response.send_message("Posted product list.", ephemeral=True)

    # ----------------------------
    # /product editstock
    # ----------------------------
    @app_commands.command(name="editstock", description="Edit product stock by product id.")
    @require_allowed_guild()
    @require_staff()
    async def editstock(self, interaction: discord.Interaction, product_id: int, new_stock: int):
        """
        Change the stored stock for a specific product ID and update its posted embed (if available).
        """
        await interaction.response.defer(ephemeral=True)
        products = load_products()
        prod = next((p for p in products if p.get("id") == product_id), None)
        if not prod:
            return await interaction.followup.send("❌ Product ID not found.", ephemeral=True)

        prod["stock"] = int(new_stock)
        save_products(products)

        # try to update posted message
        await self.try_update_product_message(prod)
        await interaction.followup.send(f"✅ Updated stock for **{prod['name']}** to {new_stock}.", ephemeral=True)

    # ----------------------------
    # /product remove
    # ----------------------------
    @app_commands.command(name="remove", description="Remove a product by its posted message ID (does not modify carts).")
    @require_allowed_guild()
    @require_staff()
    async def remove(self, interaction: discord.Interaction, message_id: int):
        """
        Remove a product by the message_id that was stored when the product was posted.
        Option C semantics: this will NOT touch existing carts.
        """
        await interaction.response.defer(ephemeral=True)
        products = load_products()
        prod = next((p for p in products if p.get("message_id") == message_id), None)
        if not prod:
            return await interaction.followup.send("❌ No product found with that message ID.", ephemeral=True)

        # attempt to delete the message
        ch = interaction.guild.get_channel(prod.get("channel_id")) if prod.get("channel_id") else None
        if ch:
            try:
                msg = await ch.fetch_message(message_id)
                await msg.delete()
            except Exception:
                # ignore deletion errors
                pass

        # remove product entry
        new_products = [p for p in products if p.get("message_id") != message_id]
        save_products(new_products)
        await interaction.followup.send(f"✅ Removed product **{prod['name']}**. Existing carts were NOT modified.", ephemeral=True)

    # ----------------------------
    # /product setpaymentmethods
    # ----------------------------
    @app_commands.command(name="setpaymentmethods", description="Set payment methods for a product (comma-separated).")
    @require_allowed_guild()
    @require_staff()
    async def setpaymentmethods(self, interaction: discord.Interaction, product_id: int, methods: str):
        """
        Set payment methods for product. methods is a comma-separated string, e.g. "Tebex,PayPal,CashApp"
        """
        await interaction.response.defer(ephemeral=True)
        products = load_products()
        prod = next((p for p in products if p.get("id") == product_id), None)
        if not prod:
            return await interaction.followup.send("❌ Product not found.", ephemeral=True)

        prod["payment_methods"] = [m.strip() for m in methods.split(",") if m.strip()]
        save_products(products)
        await interaction.followup.send(f"✅ Payment methods set for **{prod['name']}**: {', '.join(prod['payment_methods'])}", ephemeral=True)

    # ----------------------------
    # /product setdiscount
    # ----------------------------
    @app_commands.command(name="setdiscount", description="Set per-product discount percent (0-100).")
    @require_allowed_guild()
    @require_staff()
    async def setdiscount(self, interaction: discord.Interaction, product_id: int, percent: int):
        """
        Set a per-product discount percentage.
        """
        await interaction.response.defer(ephemeral=True)
        if percent < 0 or percent > 100:
            return await interaction.followup.send("❌ Discount percent must be between 0 and 100.", ephemeral=True)

        products = load_products()
        prod = next((p for p in products if p.get("id") == product_id), None)
        if not prod:
            return await interaction.followup.send("❌ Product not found.", ephemeral=True)

        prod["discount_percent"] = int(percent)
        save_products(products)

        await self.try_update_product_message(prod)
        await interaction.followup.send(f"✅ Set discount for **{prod['name']}** to {percent}%.", ephemeral=True)

    # ----------------------------
    # Utility: update posted message
    # ----------------------------
    async def try_update_product_message(self, product: dict):
        """
        If the product has message_id & channel_id, attempt to edit the original message embed to reflect updated stock/discount.
        """
        mid = product.get("message_id")
        chid = product.get("channel_id")
        if not mid or not chid:
            return

        # find channel in bot guilds
        for g in self.bot.guilds:
            ch = g.get_channel(chid)
            if ch:
                try:
                    msg = await ch.fetch_message(mid)
                    embed = self.product_embed(product)
                    # If cart cog provides views, it will restore them. Here we only update embed.
                    await msg.edit(embed=embed)
                except Exception:
                    pass
                return


async def setup(bot):
    await bot.add_cog(Products(bot))
