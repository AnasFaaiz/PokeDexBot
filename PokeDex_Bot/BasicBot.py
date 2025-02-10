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

def get_pokemon_data(pokemon_identifier):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_identifier.lower()}"
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

def get_pokemon_evolution(pokemon_name):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_name.lower()}"
        response = requests.get(url)
        response.raise_for_status()
        
        species_data = response.json()
        evolution_chain_url = species_data["evolution_chain"]["url"]
        
        response = requests.get(evolution_chain_url)
        response.raise_for_status()
        
        evolution_data = response.json()
        chain = evolution_data["chain"]
        
        evolutions = []
        while chain:
            species_name = chain["species"]["name"].capitalize()
            evolves_to = chain["evolves_to"]
            evolution_details = []
            if evolves_to:
                for detail in evolves_to[0]["evolution_details"]:
                    if detail["trigger"]["name"] == "level-up":
                        if detail["min_level"]:
                            evolution_details.append(f"Level {detail['min_level']}")
                        if detail["min_happiness"]:
                            evolution_details.append("High friendship")
                        if detail["time_of_day"]:
                            evolution_details.append(f"Time of day: {detail['time_of_day']}")
                    elif detail["trigger"]["name"] == "use-item":
                        evolution_details.append(f"Use {detail['item']['name'].replace('-', ' ').capitalize()}")
                    elif detail["trigger"]["name"] == "trade":
                        evolution_details.append("Trade")
                    elif detail["trigger"]["name"] == "shed":
                        evolution_details.append("Shed")
            evolutions.append((species_name, ", ".join(evolution_details)))
            if evolves_to:
                chain = evolves_to[0]
            else:
                break
        
        return evolutions
    except requests.RequestException as e:
        print(f"Error fetching evolution data: {e}")
        return None

def get_pokemon_sprite(pokemon_name):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        sprite = data["sprites"]["front_default"]
        return sprite
    except requests.RequestException as e:
        print(f"Error fetching sprite: {e}")
        return None

def get_pokemon_abilities(pokemon_name):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        abilities = [(ability["ability"]["name"].capitalize(), ability["is_hidden"]) for ability in data["abilities"]]
        return abilities
    except requests.RequestException as e:
        print(f"Error fetching abilities: {e}")
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

@bot.command()
async def evolve(ctx, pokemon: str):
    evolutions = get_pokemon_evolution(pokemon)
    if evolutions is None:
        await ctx.send(f"Sorry, couldn't find evolution information for '{pokemon}'")
        return
    
    embed = discord.Embed(
        title=f"{pokemon.capitalize()} Evolution Chain",
        color=0x00ff00
    )
    
    for evolution, details in evolutions:
        sprite = get_pokemon_sprite(evolution)
        description = details if details else "No special requirements"
        embed.add_field(name=evolution, value=description, inline=False)
        embed.set_image(url=sprite)
    
    await ctx.send(embed=embed)

@bot.command()
async def ability(ctx, pokemon: str):
    abilities = get_pokemon_abilities(pokemon)
    if abilities is None:
        await ctx.send(f"Sorry, couldn't find abilities for '{pokemon}'")
        return

    regular_abilities = [ability[0] for ability in abilities if not ability[1]]
    hidden_abilities = [ability[0] for ability in abilities if ability[1]]
    
    embed = discord.Embed(
        title=f"{pokemon.capitalize()} Abilities",
        color=0x0000ff
    )
    if regular_abilities:
        embed.add_field(name="Regular Abilities", value=", ".join(regular_abilities), inline=False)
    if hidden_abilities:
        embed.add_field(name="Hidden Abilities", value=", ".join(hidden_abilities), inline=False)
        embed.color = 0xffd700  # Change color to gold for hidden abilities

    await ctx.send(embed=embed)

# Start the bot
bot.run(TOKEN)