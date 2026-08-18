from PokePyDex import (
    format_evolution_requirement,
    get_available_version_groups,
    get_evolution_chain,
    get_level_up_moves,
    get_machine_moves,
    get_pokemon,
    get_pokemon_species,
    get_type_effectiveness,
    normalize_identifier,
)


def test_public_api_exports_expected_functions() -> None:
    public_functions = (
        format_evolution_requirement,
        get_available_version_groups,
        get_evolution_chain,
        get_level_up_moves,
        get_machine_moves,
        get_pokemon,
        get_pokemon_species,
        get_type_effectiveness,
        normalize_identifier,
    )

    assert all(callable(function) for function in public_functions)
