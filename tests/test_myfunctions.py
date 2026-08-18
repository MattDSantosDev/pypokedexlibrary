from unittest.mock import Mock, patch

import pytest

from PokePyDex.myfunctions import (
    PokeAPIError,
    PokemonNotFoundError,
    _get_json,
    format_evolution_requirement,
    get_available_version_groups,
    get_level_up_moves,
    get_machine_moves,
    get_type_effectiveness,
)


def test_format_evolution_requirement() -> None:
    details = [
        {
            "min_level": 16,
            "item": None,
            "trigger": {"name": "level-up"},
            "time_of_day": "",
            "min_affection": None,
            "known_move_type": None,
        }
    ]

    result = format_evolution_requirement(details)

    assert "Level 16" in result
    assert "Level Up" in result


def test_format_evolution_requirement_with_item() -> None:
    details = [
        {
            "min_level": None,
            "item": {"name": "leaf-stone"},
            "trigger": {"name": "use-item"},
            "time_of_day": "",
            "min_affection": None,
            "known_move_type": None,
        }
    ]

    result = format_evolution_requirement(details, "leafeon")

    assert "Leaf Stone" in result


def test_format_evolution_requirement_without_details() -> None:
    assert format_evolution_requirement([]) == "Special condition"


def test_get_level_up_moves_filters_level_up_moves() -> None:
    pokemon_data = {
        "moves": [
            {
                "move": {"name": "thunder-shock"},
                "version_group_details": [
                    {
                        "level_learned_at": 1,
                        "move_learn_method": {"name": "level-up"},
                        "version_group": {"name": "red-blue"},
                    },
                    {
                        "level_learned_at": 0,
                        "move_learn_method": {"name": "machine"},
                        "version_group": {"name": "red-blue"},
                    },
                ],
            },
            {
                "move": {"name": "iron-tail"},
                "version_group_details": [
                    {
                        "level_learned_at": 20,
                        "move_learn_method": {"name": "machine"},
                        "version_group": {"name": "red-blue"},
                    },
                ],
            },
        ]
    }

    move_data = {
        "type": {"name": "electric"},
        "damage_class": {"name": "special"},
    }

    with (
        patch(
            "PokePyDex.myfunctions._get_raw_pokemon",
            return_value=pokemon_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_move_details",
            return_value=move_data,
        ),
    ):
        moves = get_level_up_moves(
            "pikachu",
            version_group="red-blue",
        )

    assert moves == [
        {
            "Level": 1,
            "Move": "Thunder Shock",
            "Type": "Electric",
            "Category": "Special Attack",
        }
    ]


def test_get_machine_moves_filters_machine_moves() -> None:
    pokemon_data = {
        "moves": [
            {
                "move": {"name": "thunderbolt"},
                "version_group_details": [
                    {
                        "move_learn_method": {"name": "machine"},
                        "version_group": {"name": "red-blue"},
                    }
                ],
            },
            {
                "move": {"name": "quick-attack"},
                "version_group_details": [
                    {
                        "move_learn_method": {"name": "level-up"},
                        "version_group": {"name": "red-blue"},
                    }
                ],
            },
        ]
    }

    move_data = {
        "type": {"name": "electric"},
        "damage_class": {"name": "special"},
        "machines": [
            {
                "machine": {"url": "https://pokeapi.co/api/v2/machine/24/"},
                "version_group": {"name": "red-blue"},
            }
        ],
    }

    machine_data = {
        "item": {"name": "tm24"},
    }

    with (
        patch(
            "PokePyDex.myfunctions._get_raw_pokemon",
            return_value=pokemon_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_move_details",
            return_value=move_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_machine_details",
            return_value=machine_data,
        ),
    ):
        moves = get_machine_moves(
            "pikachu",
            version_group="red-blue",
        )

    assert moves == [
        {
            "Machine": "Tm24",
            "Move": "Thunderbolt",
            "Type": "Electric",
            "Category": "Special Attack",
        }
    ]


def test_get_type_effectiveness_for_electric_pokemon() -> None:
    pokemon_data = {
        "types": [
            {"type": {"name": "electric"}},
        ],
    }

    def type_details_for(type_name: str) -> dict:
        damage_relations = {
            "double_damage_to": [],
            "half_damage_to": [],
            "no_damage_to": [],
        }

        if type_name == "ground":
            damage_relations["double_damage_to"] = [
                {"name": "electric"},
            ]

        return {"damage_relations": damage_relations}

    with (
        patch(
            "PokePyDex.myfunctions._get_raw_pokemon",
            return_value=pokemon_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_type_details",
            side_effect=type_details_for,
        ),
    ):
        effectiveness = get_type_effectiveness("pikachu")

    ground = next(entry for entry in effectiveness if entry["Attack Type"] == "Ground")
    normal = next(entry for entry in effectiveness if entry["Attack Type"] == "Normal")

    assert ground["Effectiveness"] == "2x"
    assert ground["Multiplier"] == 2
    assert normal["Effectiveness"] == "1x"


def test_get_available_version_groups() -> None:
    pokemon_data = {
        "game_indices": [
            {"version": {"name": "gold"}},
            {"version": {"name": "silver"}},
            {"version": {"name": "crystal"}},
        ],
    }

    version_groups = {
        "gold": {"version_group": {"name": "gold-silver"}},
        "silver": {"version_group": {"name": "gold-silver"}},
        "crystal": {"version_group": {"name": "crystal-clear"}},
    }

    with (
        patch(
            "PokePyDex.myfunctions._get_raw_pokemon",
            return_value=pokemon_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_version_details",
            side_effect=version_groups.__getitem__,
        ),
    ):
        available_groups = get_available_version_groups("pichu")

    assert available_groups == {"gold-silver", "crystal-clear"}


def test_get_type_effectiveness_handles_immunity() -> None:
    pokemon_data = {
        "types": [{"type": {"name": "flying"}}],
    }

    def type_details_for(type_name: str) -> dict:
        relations = {
            "double_damage_to": [],
            "half_damage_to": [],
            "no_damage_to": [],
        }

        if type_name == "ground":
            relations["no_damage_to"] = [{"name": "flying"}]

        return {"damage_relations": relations}

    with (
        patch(
            "PokePyDex.myfunctions._get_raw_pokemon",
            return_value=pokemon_data,
        ),
        patch(
            "PokePyDex.myfunctions.get_type_details",
            side_effect=type_details_for,
        ),
    ):
        effectiveness = get_type_effectiveness("flygon")

    ground = next(item for item in effectiveness if item["Attack Type"] == "Ground")

    assert ground["Multiplier"] == 0
    assert ground["Effectiveness"] == "0x"


def test_get_json_raises_api_error_on_network_failure() -> None:
    from requests import RequestException

    from PokePyDex.myfunctions import _get_json

    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            side_effect=RequestException("connection failed"),
        ),
        pytest.raises(PokeAPIError),
    ):
        _get_json("https://example.com")


def test_get_json_raises_not_found_error() -> None:
    from PokePyDex.myfunctions import _get_json

    response = Mock()
    response.status_code = 404

    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            return_value=response,
        ),
        pytest.raises(PokemonNotFoundError),
    ):
        _get_json(
            "https://example.com/pokemon/missing",
            not_found_message="Pokemon was not found",
        )


def test_get_json_raises_api_error_for_invalid_json() -> None:
    from PokePyDex.myfunctions import _get_json

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("invalid JSON")

    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            return_value=response,
        ),
        pytest.raises(PokeAPIError),
    ):
        _get_json("https://example.com")


from requests import RequestException


def test_get_json_handles_network_failure() -> None:
    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            side_effect=RequestException("connection failed"),
        ),
        pytest.raises(PokeAPIError),
    ):
        _get_json("https://example.com")


def test_get_json_handles_not_found() -> None:
    response = Mock()
    response.status_code = 404

    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            return_value=response,
        ),
        pytest.raises(PokemonNotFoundError),
    ):
        _get_json(
            "https://example.com/missing",
            not_found_message="Pokemon was not found",
        )


def test_get_json_handles_invalid_json() -> None:
    response = Mock()
    response.status_code = 200
    response.json.side_effect = ValueError("invalid JSON")

    with (
        patch(
            "PokePyDex.myfunctions.requests.get",
            return_value=response,
        ),
        pytest.raises(PokeAPIError),
    ):
        _get_json("https://example.com")
