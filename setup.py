from setuptools import find_packages, setup

setup(
    name="pokepydex",
    version="0.1.0",
    description="An user friendly Pokedex using PokeAPI",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31,<3",
    ],
    extras_require={
        "app": [
            "streamlit>=1.35,<2",
            "pandas>=2,<3",
        ],
        "test": [
            "pytest>=8,<9",
        ],
    },
    python_requires=">=3.10",
)
