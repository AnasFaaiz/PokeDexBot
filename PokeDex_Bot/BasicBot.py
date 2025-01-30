import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('PokeDex_TOKEN')

if TOKEN is None:
    raise ValueError("No token found. Please set the PokeDex_TOKEN environment variable in your .env file.")

# Bot Setup with proper intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_pokemon_data(pokemon_name):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        name = data["name"].capitalize()
        types = ", ".join([t["type"]["name"].capitalize() for t in data["types"]])
        hp = data["stats"][0]["base_stat"]
        attack = data["stats"][1]["base_stat"]
        defense = data["stats"][2]["base_stat"]
        sprite = data["sprites"]["front_default"]
        return name, types, hp, attack, defense, sprite
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
@bot.command()
async def pokedex(ctx, pokemon: str):
    data = get_pokemon_data(pokemon)
    if data is None:
        await ctx.send(f"Sorry, couldn't find information for '{pokemon}'")
        return
    
    name, types, hp, attack, defense, sprite = data
    embed = discord.Embed(
        title=name,
        description=f"Type: {types}",
        color=0xff0000
    )
    embed.add_field(name="HP", value=hp, inline=True)
    embed.add_field(name="Attack", value=attack, inline=True)
    embed.add_field(name="Defense", value=defense, inline=True)
    embed.set_thumbnail(url=sprite)
    
    await ctx.send(embed=embed)

# Start the bot
bot.run(TOKEN)