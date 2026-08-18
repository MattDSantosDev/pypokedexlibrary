from html import escape
from textwrap import dedent
from urllib.parse import quote

import pandas as pd
import streamlit as st

from PokePyDex.myfunctions import (
    PokeAPIError,
    PokemonNotFoundError,
    get_available_version_groups,
    get_evolution_chain,
    get_level_up_moves,
    get_machine_moves,
    get_pokemon,
    get_pokemon_species,
    get_type_effectiveness,
)

VERSION_GROUPS = {
    "All versions": None,
    "Red / Blue": "red-blue",
    "Gold / Silver": "gold-silver",
    "Ruby / Sapphire": "ruby-sapphire",
    "Diamond / Pearl": "diamond-pearl",
    "Black / White": "black-white",
    "X / Y": "x-y",
    "Sun / Moon": "sun-moon",
    "Sword / Shield": "sword-shield",
    "Scarlet / Violet": "scarlet-violet",
}


def render_stat_with_bar(stat_name, stat_value, max_value=255):
    """Renders 'Stat Name - Stat Value' centered above a progress bar with 1-255 bounds."""
    pct = min(max((stat_value / max_value) * 100, 0), 100)

    st.markdown(
        f"""
        <div style="margin-bottom: 20px; text-align: center;">
            <div style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">
                {stat_name} - <span style="font-weight: 700;">{stat_value}</span>
            </div>
            <div style="background-color: rgba(128, 128, 128, 0.25); border-radius: 6px; height: 8px; width: 100%; overflow: hidden;">
                <div style="background-color: #4CAF50; width: {pct}%; height: 100%; border-radius: 6px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; opacity: 0.65; margin-top: 2px;">
                <span>1</span>
                <span>255</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def centered_dataframe(rows: list[dict]) -> None:
    if not rows:
        st.info("No data was found for this selection.")
        return

    dataframe = pd.DataFrame(rows)

    styled_dataframe = dataframe.style.set_properties(
        **{"text-align": "center"}
    ).set_table_styles(
        [
            {
                "selector": "th",
                "props": [("text-align", "center")],
            },
        ]
    )

    st.dataframe(
        styled_dataframe,
        hide_index=True,
        use_container_width=True,
    )


def load_and_display_moves(
    title: str,
    loader,
    identifier: str,
    version_group: str | None,
    state_key: str,
) -> None:
    if not st.session_state.get(state_key, False):
        return

    try:
        with st.spinner(f"Loading {title.lower()}..."):
            moves = loader(identifier, version_group)
    except PokeAPIError as error:
        st.warning(f"{title} unavailable: {error}")
        return

    st.markdown(
        f"<h3 style='text-align: center;'>{title}</h3>",
        unsafe_allow_html=True,
    )
    centered_dataframe(moves)


@st.cache_data(show_spinner=False)
def load_species(identifier: str) -> dict:
    return get_pokemon_species(identifier)


@st.cache_data(show_spinner=False)
def load_evolution_chain(identifier: str) -> dict:
    return get_evolution_chain(identifier)


@st.cache_data(show_spinner=False)
def load_level_up_moves(
    identifier: str,
    version_group: str | None,
) -> list[dict]:
    return get_level_up_moves(identifier, version_group)


@st.cache_data(show_spinner=False)
def load_machine_moves(
    identifier: str,
    version_group: str | None,
) -> list[dict]:
    return get_machine_moves(identifier, version_group)


@st.cache_data(show_spinner=False)
def load_type_effectiveness(identifier: str) -> list[dict]:
    return get_type_effectiveness(identifier)


@st.cache_data(show_spinner=False)
def load_available_version_groups(identifier: str) -> set[str]:
    return get_available_version_groups(identifier)


def collect_evolution_paths(
    node: dict,
    path: list[dict] | None = None,
    incoming_requirement: str | None = None,
) -> list[list[dict]]:
    current_node = {
        "Identifier": node["Identifier"],
        "Name": node["Name"],
        "Sprite URL": node["Sprite URL"],
        "Requirement": incoming_requirement,
    }

    current_path = (path or []) + [current_node]

    if not node["Evolves To"]:
        return [current_path]

    paths = []

    for evolution in node["Evolves To"]:
        paths.extend(
            collect_evolution_paths(
                evolution["Pokemon"],
                current_path,
                evolution["Requirement"],
            )
        )

    return paths


def render_evolution_chain(root_node: dict) -> None:
    paths = collect_evolution_paths(root_node)

    st.html(
        dedent(
            """
            <style>
                .evolution-row {
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    gap: 14px;
                    width: 100%;
                    overflow-x: auto;
                    padding: 12px 8px 20px;
                }

                .evolution-card {
                    flex: 0 0 120px;
                    text-align: center;
                }

                .evolution-card img {
                    width: 110px;
                    height: 110px;
                    object-fit: contain;
                }

                .evolution-name {
                    font-weight: 600;
                    white-space: nowrap;
                    margin-top: 4px;
                }

                .evolution-arrow {
                    flex: 0 0 100px;
                    text-align: center;
                    padding-top: 30px;
                }

                .arrow {
                    font-size: 30px;
                    line-height: 1;
                }

                .requirement {
                    font-size: 12px;
                    line-height: 1.3;
                    margin-top: 8px;
                    white-space: normal;
                }

                @media (max-width: 640px) {
                    .evolution-row {
                        justify-content: flex-start;
                        gap: 8px;
                    }

                    .evolution-card {
                        flex-basis: 96px;
                    }

                    .evolution-card img {
                        width: 88px;
                        height: 88px;
                    }

                    .evolution-arrow {
                        flex-basis: 76px;
                    }
                }
            </style>
            """
        )
    )

    for path in paths:
        elements = []

        for index, node in enumerate(path):
            if index > 0:
                requirement = escape(node["Requirement"] or "Special condition")

                elements.append(
                    f"""
                    <div class="evolution-arrow">
                        <div class="arrow">→</div>
                        <div class="requirement">{requirement}</div>
                    </div>
                    """
                )

            name = escape(node["Name"])
            identifier = quote(node["Identifier"])
            sprite_url = escape(node["Sprite URL"] or "")

            elements.append(
                f"""
                <div class="evolution-card">
                    <a href="?pokemon={identifier}" title="Open {name}">
                        <img src="{sprite_url}" alt="{name}">
                    </a>
                    <div class="evolution-name">{name}</div>
                </div>
                """
            )

        st.html(
            dedent(
                f"""
                <div class="evolution-row">
                    {"".join(elements)}
                </div>
                """
            )
        )

        if len(paths) > 1:
            st.divider()


st.set_page_config(page_title="PokePyDex", layout="wide")
st.title("🎮 PokePyDex")

# 1. State Management for Reset functionality
if "pokemon_query" not in st.session_state:
    st.session_state.pokemon_query = ""


def reset_search():
    st.session_state["pokemon_query"] = ""
    st.session_state.pop("search_identifier", None)
    st.session_state.pop("level_up_moves_loaded", None)
    st.session_state.pop("machine_moves_loaded", None)
    st.session_state.pop("effectiveness_loaded", None)
    st.session_state.pop("move_options_loaded", None)
    st.session_state.pop("evolution_loaded", None)
    st.query_params.clear()


query_identifier = st.query_params.get("pokemon")

if (
    query_identifier
    and query_identifier != st.session_state.get("search_identifier")
):
    st.session_state["pokemon_query"] = query_identifier
    st.session_state["search_identifier"] = query_identifier
    st.session_state.pop("level_up_moves_loaded", None)
    st.session_state.pop("machine_moves_loaded", None)
    st.session_state.pop("effectiveness_loaded", None)
    st.session_state.pop("move_options_loaded", None)
    st.session_state.pop("evolution_loaded", None)

# 2. Input Row with Search and Reset Buttons
with st.form("pokemon_search_form"):
    input_col, search_col = st.columns([5, 1], vertical_alignment="bottom")

    with input_col:
        identifier = st.text_input(
            "Enter a Pokemon name or ID:",
            placeholder="pikachu",
            key="pokemon_query",
        )

    with search_col:
        search_clicked = st.form_submit_button(
            "🔍 Search",
            use_container_width=True,
            type="primary",
        )

st.button(
    "🔄 Reset",
    on_click=reset_search,
    use_container_width=True,
)

if st.button("Clear cached data", key="clear_cached_data"):
    st.cache_data.clear()
    st.rerun()

search_target = identifier.strip()

if search_clicked and search_target:
    st.session_state["search_identifier"] = search_target
    st.query_params["pokemon"] = search_target
    st.session_state.pop("level_up_moves_loaded", None)
    st.session_state.pop("machine_moves_loaded", None)
    st.session_state.pop("effectiveness_loaded", None)
    st.session_state.pop("move_options_loaded", None)
    st.session_state.pop("evolution_loaded", None)

active_identifier = st.session_state.get("search_identifier")

if active_identifier:
    try:
        with st.spinner("Loading Pokémon data..."):
            pokemon = get_pokemon(active_identifier)
    except PokemonNotFoundError:
        st.error(f"No Pokemon was found for '{active_identifier}'.")
    except PokeAPIError as error:
        st.error(f"Could not load Pokemon data: {error}")
    except ValueError as error:
        st.warning(str(error))
    else:
        species = None
        evolution_chain = None

        try:
            species = load_species(active_identifier)
        except PokeAPIError as error:
            st.warning(f"Species data unavailable: {error}")

        sprite_url = escape(pokemon["Sprite URL"] or "")
        pokemon_name = escape(pokemon["Name"])
        pokemon_types = escape(", ".join(pokemon["Types"]))

        summary_html = f"""
        <div style="text-align: center; width: 100%;">
            <img src="{sprite_url}" alt="{pokemon_name}"
                 style="width: 200px; height: 200px; object-fit: contain;">
            <h2>#{pokemon['ID']} - {pokemon_name}</h2>
            <p><strong>Type:</strong> {pokemon_types}</p>
        """

        if species is not None:
            genus = escape(species["Genus"] or "Unknown")
            summary_html += f"""
            <h3>Pokédex Information</h3>
            <p><strong>Genus:</strong> {genus}</p>
            <p><strong>Capture Rate:</strong> {species['Capture Rate']}</p>
            """

        summary_html += "</div>"
        st.html(summary_html)

        if species is not None:
            if species["Is Legendary"]:
                st.warning("Legendary Pokémon")

            if species["Is Mythical"]:
                st.warning("Mythical Pokémon")

        evolution_tab, stats_tab, moves_tab = st.tabs(["Evolution", "Stats", "Moves"])

        with evolution_tab:
            evolution_clicked = st.button(
                "Load Evolution Chain",
                key="load_evolution_chain",
            )

            if evolution_clicked:
                st.session_state["evolution_loaded"] = True

            if not st.session_state.get("evolution_loaded", False):
                st.info("Select this option to load the evolution chain.")
            elif evolution_chain is None:
                try:
                    with st.spinner("Loading evolution chain..."):
                        evolution_chain = load_evolution_chain(
                            active_identifier
                        )
                except PokeAPIError as error:
                    st.warning(f"Evolution data unavailable: {error}")

            if evolution_chain is not None:
                st.markdown(
                    "<h2 style='text-align: center;'>Evolution Chain</h2>",
                    unsafe_allow_html=True,
                )
                render_evolution_chain(evolution_chain)
            else:
                st.info("Evolution data is unavailable.")

        with stats_tab:
            st.markdown(
                "<h2 style='text-align: center;'>Base Stats</h2>",
                unsafe_allow_html=True,
            )

            target_stats_col1 = ["HP", "Special Attack"]
            target_stats_col2 = ["Attack", "Special Defense"]
            target_stats_col3 = ["Defense", "Speed"]

            stat_col1, stat_col2, stat_col3 = st.columns(3)

            with stat_col1:
                for stat in target_stats_col1:
                    if stat in pokemon["Stats"]:
                        render_stat_with_bar(stat, pokemon["Stats"][stat])

            with stat_col2:
                for stat in target_stats_col2:
                    if stat in pokemon["Stats"]:
                        render_stat_with_bar(stat, pokemon["Stats"][stat])

            with stat_col3:
                for stat in target_stats_col3:
                    if stat in pokemon["Stats"]:
                        render_stat_with_bar(stat, pokemon["Stats"][stat])

            all_stats = [
                "HP",
                "Attack",
                "Defense",
                "Special Attack",
                "Special Defense",
                "Speed",
            ]
            bst = sum(pokemon["Stats"].get(stat, 0) for stat in all_stats)

            st.divider()
            st.markdown(
                f"""
                <div style="text-align: center; margin-top: 10px;">
                    <span style="font-size: 18px; font-weight: 600; opacity: 0.85;">Base Stat Total (BST): </span>
                    <span style="font-size: 22px; font-weight: 700; color: #FF4B4B;">{bst}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            show_effectiveness = st.button(
                "Load Type Effectiveness",
                key="load_type_effectiveness",
            )

            if show_effectiveness:
                st.session_state["effectiveness_loaded"] = True

            if st.session_state.get("effectiveness_loaded", False):
                try:
                    with st.spinner("Loading type effectiveness..."):
                        effectiveness = load_type_effectiveness(active_identifier)
                except PokeAPIError as error:
                    st.warning(f"Type effectiveness unavailable: {error}")
                else:
                    st.markdown(
                        "<h2 style='text-align: center;'>Type Effectiveness</h2>",
                        unsafe_allow_html=True,
                    )
                    centered_dataframe(effectiveness)

        with moves_tab:
            st.markdown(
                "<h2 style='text-align: center;'>Moves</h2>",
                unsafe_allow_html=True,
            )

            load_move_options_clicked = st.button(
                "Show Move Options",
                key="load_move_options",
            )

            if load_move_options_clicked:
                st.session_state["move_options_loaded"] = True

            if not st.session_state.get(
                "move_options_loaded",
                False,
            ):
                st.info("Select this option to load game versions and move data.")
            else:
                st.markdown(
                    "<h3 style='text-align: center;'>Move Version</h3>",
                    unsafe_allow_html=True,
                )

                try:
                    available_version_groups = load_available_version_groups(
                        active_identifier
                    )
                except PokeAPIError as error:
                    st.warning(f"Available game versions could not be loaded: {error}")
                    available_version_groups = None

                available_version_options = {
                    label: value
                    for label, value in VERSION_GROUPS.items()
                    if (
                        available_version_groups is None
                        or value is None
                        or value in available_version_groups
                    )
                }

                selected_version_label = st.selectbox(
                    "Choose a game version group:",
                    options=list(available_version_options),
                    key=(f"selected_version_label_{active_identifier}"),
                )

                selected_version_group = available_version_options[
                    selected_version_label
                ]

                level_up_clicked = st.button(
                    "Load Level-Up Moves",
                    key="load_level_up_moves",
                )

                if level_up_clicked:
                    st.session_state["level_up_moves_loaded"] = True

                if st.session_state.get(
                    "level_up_moves_loaded",
                    False,
                ):
                    load_and_display_moves(
                        f"Level-Up Moves ({selected_version_label})",
                        load_level_up_moves,
                        active_identifier,
                        selected_version_group,
                        "level_up_moves_loaded",
                    )

                machine_clicked = st.button(
                    "Load TM/HM Moves",
                    key="load_machine_moves",
                )

                if machine_clicked:
                    st.session_state["machine_moves_loaded"] = True

                if st.session_state.get(
                    "machine_moves_loaded",
                    False,
                ):
                    load_and_display_moves(
                        f"TM/HM Moves ({selected_version_label})",
                        load_machine_moves,
                        active_identifier,
                        selected_version_group,
                        "machine_moves_loaded",
                    )
