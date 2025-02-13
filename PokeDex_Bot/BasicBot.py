import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
import logging
import traceback
from typing import Optional, List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pokemon_bot')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('PokeDex_TOKEN')

if TOKEN is None:
    raise ValueError("No token found. Please set the PokeDex_TOKEN environment variable in your .env file.")

# Bot Setup with proper intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help')

TYPE_COLORS = {
    "normal": 0xA8A878,
    "fire": 0xF08030,
    "water": 0x6890F0,
    "electric": 0xF8D030,
    "grass": 0x78C850,
    "ice": 0x98D8D8,
    "fighting": 0xC03028,
    "poison": 0xA040A0,
    "ground": 0xE0C068,
    "flying": 0xA890F0,
    "psychic": 0xF85888,
    "bug": 0xA8B820,
    "rock": 0xB8A038,
    "ghost": 0x705898,
    "dragon": 0x7038F8,
    "dark": 0x705848,
    "steel": 0xB8B8D0,
    "fairy": 0xEE99AC
}

TYPE_CHART = {
    "normal": {"weak": ["fighting"], "immune": ["ghost"], "resistant": []},
    "fire": {"weak": ["water", "ground", "rock"], "immune": [], "resistant": ["fire", "grass", "ice", "bug", "steel", "fairy"]},
    "water": {"weak": ["electric", "grass"], "immune": [], "resistant": ["fire", "water", "ice", "steel"]},
    "electric": {"weak": ["ground"], "immune": [], "resistant": ["electric", "flying", "steel"]},
    "grass": {"weak": ["fire", "ice", "poison", "flying", "bug"], "immune": [], "resistant": ["water", "electric", "grass", "ground"]},
    "ice": {"weak": ["fire", "fighting", "rock", "steel"], "immune": [], "resistant": ["ice"]},
    "fighting": {"weak": ["flying", "psychic", "fairy"], "immune": [], "resistant": ["bug", "rock", "dark"]},
    "poison": {"weak": ["ground", "psychic"], "immune": [], "resistant": ["grass", "fighting", "poison", "bug", "fairy"]},
    "ground": {"weak": ["water", "grass", "ice"], "immune": ["electric"], "resistant": ["poison", "rock"]},
    "flying": {"weak": ["electric", "ice", "rock"], "immune": ["ground"], "resistant": ["grass", "fighting", "bug"]},
    "psychic": {"weak": ["bug", "ghost", "dark"], "immune": [], "resistant": ["fighting", "psychic"]},
    "bug": {"weak": ["fire", "flying", "rock"], "immune": [], "resistant": ["grass", "fighting", "ground"]},
    "rock": {"weak": ["water", "grass", "fighting", "ground", "steel"], "immune": [], "resistant": ["normal", "fire", "poison", "flying"]},
    "ghost": {"weak": ["ghost", "dark"], "immune": ["normal", "fighting"], "resistant": ["poison", "bug"]},
    "dragon": {"weak": ["ice", "dragon", "fairy"], "immune": [], "resistant": ["fire", "water", "electric", "grass"]},
    "dark": {"weak": ["fighting", "bug", "fairy"], "immune": ["psychic"], "resistant": ["ghost", "dark"]},
    "steel": {"weak": ["fire", "fighting", "ground"], "immune": ["poison"], "resistant": ["normal", "grass", "ice", "flying", "psychic", "bug", "rock", "dragon", "steel", "fairy"]},
    "fairy": {"weak": ["poison", "steel"], "immune": ["dragon"], "resistant": ["fighting", "bug", "dark"]}
}

class PokemonAPI:
    BASE_URL = "https://pokeapi.co/api/v2"
    session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls.session is None:
            cls.session = aiohttp.ClientSession()
        return cls.session
    
    @classmethod
    async def close_session(cls):
        if cls.session:
            await cls.session.close()
            cls.session = None
    
    @classmethod
    async def get_pokemon_data(cls, pokemon_identifier: str) -> Optional[Dict]:
        try:
            session = await cls.get_session()
            async with session.get(f"{cls.BASE_URL}/pokemon/{pokemon_identifier.lower()}") as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching pokemon data: {e}")
            return None

    @classmethod
    async def get_pokemon_species(cls, pokemon_name: str) -> Optional[Dict]:
        try:
            session = await cls.get_session()
            async with session.get(f"{cls.BASE_URL}/pokemon-species/{pokemon_name.lower()}") as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching species data: {e}")
            return None

async def get_pokemon_stats(pokemon_identifier: str) -> Optional[Tuple]:
    data = await PokemonAPI.get_pokemon_data(pokemon_identifier)
    if not data:
        return None
    
    name = data["name"].capitalize()
    types = ", ".join([t["type"]["name"].capitalize() for t in data["types"]])
    stats = {
        stat["stat"]["name"]: stat["base_stat"]
        for stat in data["stats"]
    }
    sprite = data["sprites"]["front_default"]
    return name, types, stats, sprite

async def get_pokemon_evolution(pokemon_name: str) -> Optional[List[Tuple[str, str]]]:
    species_data = await PokemonAPI.get_pokemon_species(pokemon_name)
    if not species_data:
        return None
        
    try:
        session = await PokemonAPI.get_session()
        async with session.get(species_data["evolution_chain"]["url"]) as response:
            evolution_data = await response.json()
        
        chain = evolution_data["chain"]
        evolutions = []
        
        while chain:
            species_name = chain["species"]["name"].capitalize()
            evolves_to = chain["evolves_to"]
            evolution_details = []
            
            if evolves_to:
                for detail in evolves_to[0]["evolution_details"]:
                    if detail["trigger"]["name"] == "level-up":
                        if detail.get("min_level"):
                            evolution_details.append(f"Level {detail['min_level']}")
                        if detail.get("min_happiness"):
                            evolution_details.append("High friendship")
                        if detail.get("time_of_day"):
                            evolution_details.append(f"Time of day: {detail['time_of_day']}")
                    elif detail["trigger"]["name"] == "use-item":
                        evolution_details.append(f"Use {detail['item']['name'].replace('-', ' ').capitalize()}")
                    elif detail["trigger"]["name"] == "trade":
                        evolution_details.append("Trade")
                    elif detail["trigger"]["name"] == "shed":
                        evolution_details.append("Shed")
            
            evolutions.append((species_name, ", ".join(evolution_details)))
            chain = evolves_to[0] if evolves_to else None
            
        return evolutions
    except Exception as e:
        logger.error(f"Error fetching evolution data: {e}")
        return None

async def get_pokemon_moves(pokemon_name: str, limit: int = 20) -> Optional[List[Dict]]:
    data = await PokemonAPI.get_pokemon_data(pokemon_name)
    if not data:
        return None
    
    try:
        moves = []
        session = await PokemonAPI.get_session()
        
        for move in data["moves"][:limit]:
            async with session.get(move["move"]["url"]) as response:
                move_data = await response.json()
            
            moves.append({
                "name": move["move"]["name"].replace("-", " ").title(),
                "type": move_data["type"]["name"].capitalize(),
                "power": move_data.get("power", "N/A"),
                "accuracy": move_data.get("accuracy", "N/A"),
                "pp": move_data.get("pp", "N/A")
            })
        return moves
    except Exception as e:
        logger.error(f"Error fetching moves: {e}")
        return None

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f'Error in {event}:')
    logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f}s")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Please specify a Pokémon! Example: `!{ctx.command.name} pikachu`")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_shutdown():
    await PokemonAPI.close_session()

@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="pokedex", help="Get information about a Pokémon")
async def pokedex(ctx, pokemon: str):
    async with ctx.typing():
        stats = await get_pokemon_stats(pokemon)
        if stats is None:
            await ctx.send(f"Sorry, couldn't find information for '{pokemon}'")
            return
        
        name, types, stats_dict, sprite = stats
        type_list = types.split(", ")
        primary_type = type_list[0].lower()

        embed = discord.Embed(
           title=name,
            description=f"**Types**\n{types}",
            color=TYPE_COLORS.get(primary_type, 0xff0000)
        )
        
        for stat_name, value in stats_dict.items():
            embed.add_field(
                name=stat_name.replace("-", " ").title(),
                value=value,
                inline=True
            )
        embed.set_thumbnail(url=sprite)
        
        await ctx.send(embed=embed)

@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="evolve", help="Get evolution chain for a Pokémon")
async def evolve(ctx, pokemon: str):
    async with ctx.typing():
        evolutions = await get_pokemon_evolution(pokemon)
        if evolutions is None:
            await ctx.send(f"Sorry, couldn't find evolution information for '{pokemon}'")
            return
        
        embed = discord.Embed(
            title=f"{pokemon.capitalize()} Evolution Chain",
            color=0x00ff00
        )
        
        for evolution, details in evolutions:
            pokemon_data = await PokemonAPI.get_pokemon_data(evolution)
            sprite = pokemon_data["sprites"]["front_default"]
            description = details if details else "No special requirements"
            embed.add_field(name=evolution, value=description, inline=False)
            embed.set_image(url=sprite)
        
        await ctx.send(embed=embed)

@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="moveset", help="Get moveset for a Pokémon")
async def moveset(ctx, pokemon: str):
    async with ctx.typing():
        moves = await get_pokemon_moves(pokemon)
        if moves is None:
            await ctx.send(f"Sorry, couldn't find move information for '{pokemon}'")
            return

        embeds = []
        current_embed = discord.Embed(
            title=f"{pokemon.capitalize()} Moveset",
            description="List of moves this Pokémon can learn",
            color=0x9B59B6
        )
        
        for i in range(0, len(moves), 5):
            if len(current_embed.fields) >= 25:
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title=f"{pokemon.capitalize()} Moveset (Continued)",
                    color=0x9B59B6
                )
            
            move_group = moves[i:i+5]
            move_text = "\n\n".join(
                f"**{move['name']}**\n"
                f"Type: {move['type']} | Power: {move['power']} | "
                f"Accuracy: {move['accuracy']} | PP: {move['pp']}"
                for move in move_group
            )
            
            current_embed.add_field(
                name=f"Moves {i+1}-{min(i+5, len(moves))}",
                value=move_text,
                inline=False
            )
        
        embeds.append(current_embed)
        for embed in embeds:
            await ctx.send(embed=embed)

@bot.command(name="commands", help="Show all available commands")
async def show_commands(ctx):
    """Shows all available bot commands"""
    embed = discord.Embed(
        title="PokéDex Bot Commands",
        description="Here are all available commands:",
        color=TYPE_COLORS.get(types.split(", ")[0].lower(), 0xff0000)
    )
    
    commands_list = [
        ("!pokedex <pokemon>", "Get detailed information about a Pokémon"),
        ("!evolve <pokemon>", "Get the evolution chain for a Pokémon"),
        ("!moveset <pokemon>", "Get the list of moves a Pokémon can learn"),
        ("!stats <pokemon>", "Get detailed stats for a Pokémon"),
        ("!compare <pokemon1> <pokemon2>", "Compare two Pokémon's stats"),
        ("!commands", "Show this help message")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(
            name=cmd,
            value=desc,
            inline=False
        )
    
    await ctx.send(embed=embed)

# STATS FEATURE:

@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="stats", help="Get detailed stats for a Pokémon")
async def stats(ctx, pokemon: str):
    """Get detailed statistics for a Pokémon including base stats and type"""
    async with ctx.typing():
        stats = await get_pokemon_stats(pokemon)
        if stats is None:
            await ctx.send(f"Sorry, couldn't find information for '{pokemon}'")
            return
        
        name, types, stats_dict, sprite = stats
        
        # Create stat bars
        max_stat = 255  # Maximum possible base stat
        stat_bars = {}
        for stat_name, value in stats_dict.items():
            bars = "█" * int((value / max_stat) * 15)
            spaces = "░" * (15 - len(bars))
            stat_bars[stat_name] = f"{bars}{spaces} {value}"
        
        embed = discord.Embed(
            title=f"{name}'s Base Stats",
            description=f"Type: {types}",
            color=TYPE_COLORS.get(types.split(", ")[0].lower(), 0xff0000)
        )
        
        # Add stat bars to embed
        for stat_name, bar in stat_bars.items():
            embed.add_field(
                name=stat_name.replace("-", " ").title(),
                value=f"`{bar}`",
                inline=False
            )
        
        embed.set_thumbnail(url=sprite)
        total = sum(stats_dict.values())
        embed.set_footer(text=f"Base Stat Total: {total}")
        
        await ctx.send(embed=embed)

@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="compare", help="Compare two Pokémon's stats")
async def compare(ctx, pokemon1: str, pokemon2: str):
    """Compare base stats of two Pokémon side by side"""
    async with ctx.typing():
        stats1 = await get_pokemon_stats(pokemon1)
        stats2 = await get_pokemon_stats(pokemon2)
        
        if stats1 is None or stats2 is None:
            await ctx.send(f"Sorry, couldn't find information for one or both Pokémon.")
            return
        
        name1, types1, stats_dict1, sprite1 = stats1
        name2, types2, stats_dict2, sprite2 = stats2
        
        # Create comparison embed
        embed = discord.Embed(
            title=f"{name1} vs {name2}",
            description=f"Type comparison:\n{name1}: {types1}\n{name2}: {types2}",
            color=0x00ff00
        )
        
        # Compare stats with bars
        max_stat = 255
        for stat_name in stats_dict1.keys():
            value1 = stats_dict1[stat_name]
            value2 = stats_dict2[stat_name]
            
            # Create visual bars
            bars1 = "█" * int((value1 / max_stat) * 10)
            bars2 = "█" * int((value2 / max_stat) * 10)
            spaces1 = "░" * (10 - len(bars1))
            spaces2 = "░" * (10 - len(bars2))
            
            stat_display = f"{name1}: `{bars1}{spaces1}` {value1}\n{name2}: `{bars2}{spaces2}` {value2}"
            embed.add_field(
                name=stat_name.replace("-", " ").title(),
                value=stat_display,
                inline=False
            )
        
        # Add total stats comparison
        total1 = sum(stats_dict1.values())
        total2 = sum(stats_dict2.values())
        embed.add_field(
            name="Base Stat Total",
            value=f"{name1}: {total1}\n{name2}: {total2}",
            inline=False
        )
        
        # Add thumbnails
        embed.set_thumbnail(url=sprite1)
        # For the second sprite, we'll use a different embed field
        embed.set_footer(text="Use !stats <pokemon> for detailed individual stats", icon_url=sprite2)
        
        await ctx.send(embed=embed)

# Add this new command
@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(name="weakness", help="Get type effectiveness for a Pokémon")
async def weakness(ctx, pokemon: str):
    """Show type effectiveness chart for a Pokémon"""
    async with ctx.typing():
        data = await get_pokemon_stats(pokemon)
        if data is None:
            await ctx.send(f"Sorry, couldn't find information for '{pokemon}'")
            return
        
        name, types_str, _, sprite = data
        types = [t.strip().lower() for t in types_str.split(",")]
        
        # Calculate effectiveness
        weaknesses = set()
        resistances = set()
        immunities = set()
        
        for poke_type in types:
            chart = TYPE_CHART[poke_type]
            weaknesses.update(chart["weak"])
            resistances.update(chart["resistant"])
            immunities.update(chart["immune"])
        
        # Remove conflicts
        weaknesses = weaknesses - resistances - immunities
        resistances = resistances - immunities
        
        embed = discord.Embed(
            title=f"{name}'s Type Effectiveness",
            description=f"Type: {types_str}",
            color=TYPE_COLORS.get(types[0], 0xff0000)
        )
        
        if weaknesses:
            embed.add_field(
                name="💥 Weak Against (2x)",
                value=", ".join(t.capitalize() for t in sorted(weaknesses)),
                inline=False
            )
        
        if resistances:
            embed.add_field(
                name="🛡️ Resistant To (½x)",
                value=", ".join(t.capitalize() for t in sorted(resistances)),
                inline=False
            )
        
        if immunities:
            embed.add_field(
                name="✨ Immune To (0x)",
                value=", ".join(t.capitalize() for t in sorted(immunities)),
                inline=False
            )
        
        embed.set_thumbnail(url=sprite)
        await ctx.send(embed=embed)

# Update the commands list in show_commands
commands_list = [
    ("!pokedex <pokemon>", "Get detailed information about a Pokémon"),
    ("!evolve <pokemon>", "Get the evolution chain for a Pokémon"),
    ("!moveset <pokemon>", "Get the list of moves a Pokémon can learn"),
    ("!stats <pokemon>", "Get detailed stats for a Pokémon"),
    ("!weakness <pokemon>", "Get type effectiveness for a Pokémon"),
    ("!compare <pokemon1> <pokemon2>", "Compare two Pokémon's stats"),
    ("!commands", "Show this help message")
]

@compare.error
async def compare_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify two Pokémon to compare! Example: `!compare pikachu charizard`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f}s")
    else:
        logger.error(f"Error in compare command: {error}")
        await ctx.send(f"An error occurred: {str(error)}")

@weakness.error
async def weakness_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify a Pokémon! Example: `!weakness charizard`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f}s")
    else:
        logger.error(f"Error in weakness command: {error}")
        await ctx.send(f"An error occurred: {str(error)}")

# Cleanup


# Start the bot
bot.run(TOKEN)