from functools import lru_cache
from typing import Any

import requests

BASE_URL = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT_SECONDS = 10


class PokemonNotFoundError(Exception):
    """Raised when PokeAPI has no Pokemon matching the provided identifier."""


class PokeAPIError(Exception):
    """Raised when PokeAPI cannot be reached or returns an unexpected response."""


def _get_json(
    url: str,
    not_found_message: str | None = None,
) -> Any:
    """Fetch and decode a JSON response from PokeAPI."""
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise PokeAPIError(f"Could not connect to PokeAPI: {url}") from error

    if response.status_code == 404 and not_found_message:
        raise PokemonNotFoundError(not_found_message)

    try:
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise PokeAPIError(
            f"PokeAPI returned an unsuccessful response: {url}"
        ) from error
    except ValueError as error:
        raise PokeAPIError(f"PokeAPI returned invalid JSON: {url}") from error


REGIONAL_FORMS = {
    "alolan": "alola",
    "galarian": "galar",
    "hisuian": "hisui",
    "paldean": "paldea",
}

MODERN_EVOLUTION_ITEMS = {
    "leafeon": "Leaf Stone",
    "glaceon": "Ice Stone",
}

MOVE_CATEGORIES = {
    "physical": "Attack",
    "special": "Special Attack",
    "status": "Status",
}


def normalize_identifier(name_or_id: str | int) -> str:
    """Convert user input into a PokeAPI-compatible identifier.

    Args:
        name_or_id: Pokemon name, numeric ID, or common regional form.

    Returns:
        A lowercase, hyphen-separated PokeAPI identifier.

    Raises:
        ValueError: If the input is empty.
    """
    identifier = str(name_or_id).strip().lower()

    if not identifier:
        raise ValueError("Please provide a valid Pokemon name or numeric ID.")

    words = identifier.replace("_", " ").replace("-", " ").split()

    if len(words) >= 2 and words[0] in REGIONAL_FORMS:
        region = REGIONAL_FORMS[words[0]]
        pokemon_name = "-".join(words[1:])
        return f"{pokemon_name}-{region}"

    return "-".join(words)


def get_pokemon(name_or_id: str | int) -> dict[str, Any]:
    """Fetch basic information for one Pokemon.

    Args:
        name_or_id: Pokemon name, numeric ID, or supported regional name.

    Returns:
        A dictionary containing identity, dimensions, types, stats,
        and the default sprite URL.

    Raises:
        ValueError: If the identifier is empty.
        PokemonNotFoundError: If PokeAPI cannot find the Pokemon.
        PokeAPIError: If the API request fails.
    """
    identifier = normalize_identifier(name_or_id)
    return _get_pokemon_by_identifier(identifier)


@lru_cache(maxsize=128)
def _get_raw_pokemon(identifier: str) -> dict[str, Any]:
    url = f"{BASE_URL}/pokemon/{identifier}/"

    return _get_json(
        url,
        not_found_message=f"Pokemon '{identifier}' was not found",
    )


def _get_pokemon_by_identifier(identifier: str) -> dict[str, Any]:
    pokemon_data = _get_raw_pokemon(identifier)

    return {
        "ID": pokemon_data["id"],
        "Name": format_label(pokemon_data["name"]),
        "Height": pokemon_data["height"],
        "Weight": pokemon_data["weight"],
        "Types": [
            format_label(type_entry["type"]["name"])
            for type_entry in pokemon_data["types"]
        ],
        "Stats": {
            format_label(stat_entry["stat"]["name"]): stat_entry["base_stat"]
            for stat_entry in pokemon_data["stats"]
        },
        "Sprite URL": pokemon_data["sprites"]["front_default"],
    }


def format_label(value: str) -> str:
    abbreviations = {
        "hp": "HP",
    }

    if value in abbreviations:
        return abbreviations[value]

    return value.replace("-", " ").title()


@lru_cache(maxsize=256)
def get_move_details(move_name: str) -> dict[str, Any]:
    url = f"{BASE_URL}/move/{move_name}/"

    return _get_json(url)


@lru_cache(maxsize=32)
def get_type_details(type_name: str) -> dict[str, Any]:
    url = f"{BASE_URL}/type/{type_name}/"

    return _get_json(url)


@lru_cache(maxsize=64)
def get_version_details(version_name: str) -> dict[str, Any]:
    url = f"{BASE_URL}/version/{version_name}/"

    return _get_json(url)


TYPE_NAMES = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)


def get_type_effectiveness(
    name_or_id: str | int,
) -> list[dict[str, Any]]:
    identifier = normalize_identifier(name_or_id)
    pokemon_data = _get_raw_pokemon(identifier)

    defending_types = [
        type_entry["type"]["name"] for type_entry in pokemon_data["types"]
    ]

    effectiveness = []

    for attacking_type in TYPE_NAMES:
        type_data = get_type_details(attacking_type)
        relations = type_data["damage_relations"]
        double_damage_to = {item["name"] for item in relations["double_damage_to"]}
        half_damage_to = {item["name"] for item in relations["half_damage_to"]}
        no_damage_to = {item["name"] for item in relations["no_damage_to"]}
        multiplier = 1.0

        for defending_type in defending_types:
            if defending_type in double_damage_to:
                multiplier *= 2

            if defending_type in half_damage_to:
                multiplier *= 0.5

            if defending_type in no_damage_to:
                multiplier = 0

        effectiveness.append(
            {
                "Attack Type": format_label(attacking_type),
                "Effectiveness": f"{multiplier:g}x",
                "Multiplier": multiplier,
            }
        )

    return sorted(
        effectiveness,
        key=lambda entry: (
            -entry["Multiplier"],
            entry["Attack Type"],
        ),
    )


@lru_cache(maxsize=256)
def get_machine_details(machine_url: str) -> dict[str, Any]:
    return _get_json(machine_url)


def get_level_up_moves(
    name_or_id: str | int,
    version_group: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch moves learned by leveling up.

    Args:
        name_or_id: Pokemon name, numeric ID, or supported regional name.
        version_group: Optional PokeAPI version-group identifier, such as
            "red-blue" or "scarlet-violet".

    Returns:
        A list of dictionaries containing level, move, type, and category.

    Raises:
        ValueError: If the identifier is empty.
        PokemonNotFoundError: If the Pokemon is not found.
        PokeAPIError: If Pokemon or move data cannot be loaded.
    """
    identifier = normalize_identifier(name_or_id)
    pokemon_data = _get_raw_pokemon(identifier)

    moves = []
    seen_moves = set()

    for move_entry in pokemon_data["moves"]:
        move_name = move_entry["move"]["name"]

        for version_detail in move_entry["version_group_details"]:
            method_name = version_detail["move_learn_method"]["name"]
            current_version_group = version_detail["version_group"]["name"]

            if method_name != "level-up":
                continue

            if version_group is not None and current_version_group != version_group:
                continue

            level = version_detail["level_learned_at"]
            move_key = (move_name, level)

            if move_key in seen_moves:
                continue

            seen_moves.add(move_key)

            move_data = get_move_details(move_name)
            damage_class = move_data["damage_class"]["name"]

            moves.append(
                {
                    "Level": level,
                    "Move": format_label(move_name),
                    "Type": format_label(move_data["type"]["name"]),
                    "Category": MOVE_CATEGORIES.get(
                        damage_class,
                        format_label(damage_class),
                    ),
                }
            )

    return sorted(
        moves,
        key=lambda move: (move["Level"], move["Move"]),
    )


def get_machine_moves(
    name_or_id: str | int,
    version_group: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch TM and HM moves available to a Pokemon.

    Args:
        name_or_id: Pokemon name, numeric ID, or supported regional name.
        version_group: Optional PokeAPI version-group identifier, such as
            "red-blue" or "scarlet-violet".

    Returns:
        A list of dictionaries containing machine, move, type, and category.

    Raises:
        ValueError: If the identifier is empty.
        PokemonNotFoundError: If the Pokemon is not found.
        PokeAPIError: If move or machine data cannot be loaded.
    """
    identifier = normalize_identifier(name_or_id)
    pokemon_data = _get_raw_pokemon(identifier)

    machine_moves = []
    seen_machines = set()

    for move_entry in pokemon_data["moves"]:
        move_name = move_entry["move"]["name"]

        for version_detail in move_entry["version_group_details"]:
            if version_detail["move_learn_method"]["name"] != "machine":
                continue

            current_version_group = version_detail["version_group"]["name"]

            if version_group is not None and current_version_group != version_group:
                continue

            move_data = get_move_details(move_name)

            for machine_entry in move_data["machines"]:
                if machine_entry["version_group"]["name"] != current_version_group:
                    continue

                machine_data = get_machine_details(machine_entry["machine"]["url"])
                machine_name = machine_data["item"]["name"]

                if machine_name in seen_machines:
                    continue

                seen_machines.add(machine_name)

                damage_class = move_data["damage_class"]["name"]

                machine_moves.append(
                    {
                        "Machine": format_label(machine_name),
                        "Move": format_label(move_name),
                        "Type": format_label(move_data["type"]["name"]),
                        "Category": MOVE_CATEGORIES.get(
                            damage_class,
                            format_label(damage_class),
                        ),
                    }
                )

    return sorted(
        machine_moves,
        key=lambda move: (
            move["Machine"],
            move["Move"],
        ),
    )


def get_pokemon_species(name_or_id: str | int) -> dict[str, Any]:
    """Fetch species and Pokédex information for a Pokemon."""
    identifier = normalize_identifier(name_or_id)
    url = f"{BASE_URL}/pokemon-species/{identifier}/"

    species_data = _get_json(
        url,
        not_found_message=(f"Pokemon species '{identifier}' was not found"),
    )

    english_genus = next(
        (
            entry["genus"]
            for entry in species_data["genera"]
            if entry["language"]["name"] == "en"
        ),
        None,
    )

    return {
        "ID": species_data["id"],
        "Name": format_label(species_data["name"]),
        "Is Legendary": species_data["is_legendary"],
        "Is Mythical": species_data["is_mythical"],
        "Genus": english_genus,
        "Capture Rate": species_data["capture_rate"],
        "Evolution Chain URL": species_data["evolution_chain"]["url"],
    }


def format_evolution_requirement(
    details: list[dict[str, Any]],
    evolved_name: str | None = None,
) -> str:
    if not details:
        return "Special condition"

    detail = details[0]
    requirements = []

    if detail.get("min_level") is not None:
        requirements.append(f"Level {detail['min_level']}")

    if detail.get("item"):
        requirements.append(f"Use {format_label(detail['item']['name'])}")

    if detail.get("held_item"):
        requirements.append(f"Holding {format_label(detail['held_item']['name'])}")

    if detail.get("time_of_day"):
        requirements.append(format_label(detail["time_of_day"]))

    if detail.get("min_happiness") is not None:
        requirements.append(f"Happiness {detail['min_happiness']}")

    if detail.get("trigger"):
        requirements.append(format_label(detail["trigger"]["name"]))

    if detail.get("min_affection") is not None:
        requirements.append(f"Affection {detail['min_affection']}")

    if detail.get("known_move_type"):
        requirements.append(
            f"Know a {format_label(detail['known_move_type']['name'])}-type move"
        )

    if detail.get("location"):
        requirements.append(f"At {format_label(detail['location']['name'])}")

    if detail.get("near_special_rock"):
        requirements.append("Near a special rock")

        if evolved_name in MODERN_EVOLUTION_ITEMS:
            requirements.append(f"Use {MODERN_EVOLUTION_ITEMS[evolved_name]}")

    return " / ".join(requirements) or "Special condition"


def build_evolution_node(
    chain_link: dict[str, Any],
) -> dict[str, Any]:
    pokemon_name = chain_link["species"]["name"]
    pokemon = get_pokemon(pokemon_name)

    return {
        "Identifier": pokemon_name,
        "Name": pokemon["Name"],
        "Sprite URL": pokemon["Sprite URL"],
        "Evolves To": [
            {
                "Requirement": format_evolution_requirement(
                    child["evolution_details"],
                    child["species"]["name"],
                ),
                "Pokemon": build_evolution_node(child),
            }
            for child in chain_link["evolves_to"]
        ],
    }


def get_evolution_chain(name_or_id: str | int) -> dict[str, Any]:
    """Fetch a display-friendly Pokemon evolution tree."""
    identifier = normalize_identifier(name_or_id)
    species_url = f"{BASE_URL}/pokemon-species/{identifier}/"

    species_data = _get_json(
        species_url,
        not_found_message=(f"Pokemon species '{identifier}' was not found"),
    )

    chain_url = species_data["evolution_chain"]["url"]
    chain_data = _get_json(chain_url)

    return build_evolution_node(chain_data["chain"])


def get_available_version_groups(
    name_or_id: str | int,
) -> set[str]:
    identifier = normalize_identifier(name_or_id)
    pokemon_data = _get_raw_pokemon(identifier)

    version_groups = set()

    for game_index in pokemon_data["game_indices"]:
        version_name = game_index["version"]["name"]
        version_data = get_version_details(version_name)
        version_group = version_data["version_group"]["name"]
        version_groups.add(version_group)

    return version_groups
