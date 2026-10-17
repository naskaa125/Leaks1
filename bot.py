import os
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Configuration des intents Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables d'environnement (configurées sur Railway)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Liste des catégories FiveVault à surveiller
CATEGORIES = {
    "Script": {"url": "https://fivevault.net/category/scripts", "emoji": "📜"},
    "MLO": {"url": "https://fivevault.net/category/mlo", "emoji": "🏰"},
    "Vehicles": {"url": "https://fivevault.net/category/vehicles", "emoji": "🚗"},
    "EUP / Clothing": {"url": "https://fivevault.net/category/eup", "emoji": "👕"},
}

# Pour stocker l'historique des liens déjà postés et éviter les doublons
liens_deja_postes = set()

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user.name}")
    
    # Message de confirmation au démarrage sur Discord
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🚀 **Bot démarré !** Analyse des ressources des 7 derniers jours en cours...")
        
    # Démarre la boucle de vérification (toutes les 20 minutes)
    verifier_nouvelles_ressources.start()

@tasks.loop(minutes=20)
async def verifier_nouvelles_ressources():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Salon Discord introuvable !")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Date limite : il y a 7 jours par rapport à aujourd'hui
    date_limite = datetime.now() - timedelta(days=7)

    for nom_categorie, config in CATEGORIES.items():
        try:
            url_categorie = config["url"]
            emoji_categorie = config["emoji"]

            response = requests.get(url_categorie, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # On récupère tous les articles/cartes de la page (pas seulement le premier)
            items = soup.select('.resource-card, .post-item, article') 
            
            for item in items:
                lien_element = item.select_one('a')
                if not lien_element or 'href' not in lien_element.attrs:
                    continue

                lien_ressource = lien_element['href']

                # Si on a déjà posté cette ressource, on passe
                if lien_ressource in liens_deja_postes:
                    continue

                titre = item.select_one('.title, h2, h3').text.strip() if item.select_one('.title, h2, h3') else "Ressource FiveM"
                desc_element = item.select_one('.description, .excerpt, p')
                description = desc_element.text.strip() if desc_element else "Aucune description fournie."

                # --- Tentative de récupération et de vérification de la date ---
                # (Adapte le sélecteur .date selon la classe HTML exacte de la date sur FiveVault)
                date_element = item.select_one('.date, time')
                resource_date = datetime.now() # Par défaut, date du jour si non trouvée
                
                if date_element:
                    date_str_site = date_element.text.strip()
                    try:
                        # Essaie de parser le format de date du site (ex: JJ/MM/AAAA)
                        resource_date = datetime.strptime(date_str_site, "%d/%m/%Y")
                    except:
                        pass

                # FILTRE : On ne prend que ce qui date de moins d'une semaine (ou égal)
                if resource_date >= date_limite:
                    # On marque le lien comme posté pour éviter les doublons futurs
                    liens_deja_postes.add(lien_ressource)

                    # 1. Traitement GoFile
                    lien_gofile = uploader_ou_convertir_gofile(lien_ressource)

                    # 2. Recherche YouTube
                    lien_youtube = chercher_youtube(f"FiveM {titre}")

                    date_formatee = resource_date.strftime("%d/%m/%Y")

                    # 3. Format du message Discord
                    message_content = (
                        f"{emoji_categorie} **Nouvel ajout — {nom_categorie}**\n"
                        f"Une ressource a été ajoutée dans les leaks.\n\n"
                        f"📄 **Contenu**\n"
                        f"# {nom_categorie}\n\n"
                        f"• 🎬 **Preview** : {lien_youtube}\n"
                        f"• 💻 **Download** : {lien_gofile}\n\n"
                        f"**Description**\n"
                        f"{description[:350]}...\n\n"
                        f"📁 **Type**\n"
                        f"{emoji_categorie} **{nom_categorie}**\n"
                        f"📅 **Date**\n"
                        f"{date_formatee}\n"
                        f"📍 **Source**\n"
                        f"# inconnu"
                    )

                    await channel.send(message_content)

        except Exception as e:
            print(f"Erreur lors de la vérification de {nom_categorie} : {e}")

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
