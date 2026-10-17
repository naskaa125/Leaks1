import os
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup

# Configuration des intents Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables d'environnement (configurées sur ton hébergeur)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Liste des catégories FiveVault à surveiller
# (Ajuste les URLs selon les liens exacts des catégories sur le site)
CATEGORIES = {
    "Script": {"url": "https://fivevault.net/category/scripts", "emoji": "📜"},
    "MLO": {"url": "https://fivevault.net/category/mlo", "emoji": "🏰"},
    "Vehicles": {"url": "https://fivevault.net/category/vehicles", "emoji": "🚗"},
    "EUP / Clothing": {"url": "https://fivevault.net/category/eup", "emoji": "👕"},
}

# Dictionnaire pour stocker les derniers liens connus par catégorie (pour éviter les doublons)
derniers_liens_connus = {cat: None for cat in CATEGORIES}

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user.name}")
    # Démarre la boucle de vérification toutes les 20 minutes
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

    # On parcourt chaque catégorie enregistrée
    for nom_categorie, config in CATEGORIES.items():
        try:
            url_categorie = config["url"]
            emoji_categorie = config["emoji"]

            response = requests.get(url_categorie, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # --- PARSING DU SITE (À adapter selon la structure HTML réelle) ---
            # Exemple : trouver le premier article de la page
            item = soup.select_one('.resource-card, .post-item, article') 
            if not item:
                continue

            lien_element = item.select_one('a')
            if not lien_element or 'href' not in lien_element.attrs:
                continue

            lien_ressource = lien_element['href']
            titre = item.select_one('.title, h2, h3').text.strip() if item.select_one('.title, h2, h3') else "Ressource FiveM"
            
            # Récupération de la description courte si disponible
            desc_element = item.select_one('.description, .excerpt, p')
            description = desc_element.text.strip() if desc_element else "Aucune description fournie."

            # Vérification s'il s'agit d'un nouveau leak pour cette catégorie
            if lien_ressource != derniers_liens_connus[nom_categorie]:
                derniers_liens_connus[nom_categorie] = lien_ressource

                # 1. Traitement GoFile (Exemple d'intégration ou conversion de lien)
                lien_gofile = uploader_ou_convertir_gofile(lien_ressource)

                # 2. Recherche automatique de la preview YouTube
                lien_youtube = chercher_youtube(f"FiveM {titre}")

                # 3. Date du jour au format JJ/MM/AAAA
                from datetime import datetime
                date_str = datetime.now().strftime("%d/%m/%Y")

                # 4. Formattage du message textuel (identique à ton image)
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
                    f"{date_str}\n"
                    f"📍 **Source**\n"
                    f"# inconnu"
                )

                await channel.send(message_content)

        except Exception as e:
            print(f"Erreur lors de la vérification de {nom_categorie} : {e}")

def uploader_ou_convertir_gofile(url_ressource):
    """
    Ici tu mets la logique pour récupérer le fichier source 
    et l'uploader sur GoFile via son API.
    """
    # Exemple temporaire : retourne un lien ou ton script d'upload API GoFile
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
    except Exception as e:
        print(f"Erreur recherche YouTube : {e}")
    
    return "Aucune preview disponible"

# Lancement du bot
bot.run(DISCORD_TOKEN)
