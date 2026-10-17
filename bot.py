import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration des intents Discord
intents = discord.Intents.default()
intents.message_content = True

class LeakBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Synchronise les commandes Slash avec Discord au démarrage
        await self.tree.sync()
        print("Commandes Slash synchronisées avec succès !")

bot = LeakBot()

# Variables d'environnement (configurées sur Railway)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Liste des catégories FiveVault disponibles
CATEGORIES = {
    "Script": {"url": "https://fivevault.net/category/scripts", "emoji": "📜"},
    "MLO": {"url": "https://fivevault.net/category/mlo", "emoji": "🏰"},
    "Vehicles": {"url": "https://fivevault.net/category/vehicles", "emoji": "🚗"},
    "EUP / Clothing": {"url": "https://fivevault.net/category/eup", "emoji": "👕"},
}

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user.name}")

# --- COMMANDE SLASH /leaks ---
@bot.tree.command(name="leaks", description="Récupère et publie le dernier leak de FiveVault dans le salon")
@app_commands.describe(categorie="Choisis la catégorie du leak à récupérer")
@app_commands.choices(categorie=[
    app_commands.Choice(name="Script", value="Script"),
    app_commands.Choice(name="MLO", value="MLO"),
    app_commands.Choice(name="Vehicles", value="Vehicles"),
    app_commands.Choice(name="EUP / Clothing", value="EUP / Clothing")
])
async def leaks(interaction: discord.Interaction, categorie: str):
    # Diffère la réponse pour éviter le timeout pendant le scraping du site
    await interaction.response.defer(thinking=True, ephemeral=True)

    config = CATEGORIES.get(categorie)
    if not config:
        await interaction.followup.send("Catégorie invalide.", ephemeral=True)
        return

    url_categorie = config["url"]
    emoji_categorie = config["emoji"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url_categorie, headers=headers, timeout=10)
        if response.status_code != 200:
            await interaction.followup.send("Erreur lors de l'accès au site FiveVault.", ephemeral=True)
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('.resource-card, .post-item, article, .card')

        if not items:
            await interaction.followup.send(f"Aucune ressource trouvée pour la catégorie {categorie}.", ephemeral=True)
            return

        # On prend le tout dernier item de la page
        item = items[0]
        lien_element = item.select_one('a')
        if not lien_element or 'href' not in lien_element.attrs:
            await interaction.followup.send("Impossible de récupérer le lien de la ressource.", ephemeral=True)
            return

        lien_ressource = lien_element['href']
        titre = item.select_one('.title, h2, h3').text.strip() if item.select_one('.title, h2, h3') else "Ressource FiveM"
        desc_element = item.select_one('.description, .excerpt, p')
        description = desc_element.text.strip() if desc_element else "Aucune description fournie."

        date_str = datetime.now().strftime("%d/%m/%Y")

        # 1. Traitement GoFile
        lien_gofile = uploader_ou_convertir_gofile(lien_ressource)

        # 2. Recherche YouTube
        lien_youtube = chercher_youtube(f"FiveM {titre}")

        # 3. Format du message Discord identique à ton image
        message_content = (
            f"{emoji_categorie} **Nouvel ajout — {categorie}**\n"
            f"Une ressource a été ajoutée dans les leaks.\n\n"
            f"📄 **Contenu**\n"
            f"# {categorie}\n\n"
            f"• 🎬 **Preview** : {lien_youtube}\n"
            f"• 💻 **Download** : {lien_gofile}\n\n"
            f"**Description**\n"
            f"{description[:350]}...\n\n"
            f"📁 **Type**\n"
            f"{emoji_categorie} **{categorie}**\n"
            f"📅 **Date**\n"
            f"{date_str}\n"
            f"📍 **Source**\n"
            f"# inconnu"
        )

        # Envoie le message publiquement dans le salon où la commande a été tapée
        await interaction.channel.send(message_content)
        
        # Confirme discrètement à toi que c'est posté
        await interaction.followup.send("✅ Leak publié avec succès dans le salon !", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"Une erreur est survenue : {e}", ephemeral=True)

def uploader_ou_convertir_gofile(url_ressource):
    """Logique d'upload GoFile"""
    return "https://gofile.io/d/exemple"

def chercher_youtube(query):
    """Recherche une vidéo YouTube pertinente"""
    if not YOUTUBE_API_KEY:
        return "https://youtube.com"

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if "items" in res and len(res["items"]) > 0:
            video_id = res["items"][0]["id"]["videoId"]
            return f"https://youtu.be/{video_id}"
    except:
        pass
    return "Aucune preview disponible"

# Lancement du bot
bot.run(DISCORD_TOKEN)
