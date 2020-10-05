"""CLI interface for generating Factorio-Noir sprites.

Notes:
- On masOS --factorio-data should be /Applications/factorio.app/Contents/data
"""
import tempfile
from pathlib import Path

import click

from factorio_noir.category import SpriteCategory
from factorio_noir.mods import VANILLA_MODS, prepare_vanilla_mod



@click.command()
@click.option("--pack-version", default="0.0.1")
@click.option(
    "--factorio-data",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    help="Factorio install directory, needed only if packaging Vanilla pack.",
    envvar="FACTORIO_DATA",
)
@click.argument(
    "pack-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
)
def cli(pack_dir, pack_version, factorio_data):
    """Generate a Factorio-Noir package from pack directory."""
    click.echo(f"Loading categories for pack: {pack_dir}")
    categories = [
        SpriteCategory.from_yaml(category_file)
        for category_file in Path(pack_dir).glob("**/*.yml")
    ]

    used_mods = {c.mod for c in categories}
    click.secho(
        f"Loaded {len(categories)} categories using a total of {len(used_mods)} mods.",
        fg="green",
    )

    pack_name = f"Factorio-Noir-{Path(pack_dir).name}_{pack_version}"
    target_dir = Path(tempfile.mkdtemp()) / pack_name
    target_dir.mkdir(exist_ok=True, parents=True)

    click.echo(f"Created temporary directory: {target_dir}")
    if VANILLA_MODS & used_mods:
        if factorio_data is None:
            click.secho(
                "Missing --factorio-data value, required for editing vanilla graphics.",
                fg="red",
            )
            raise click.Abort

        factorio_data = Path(factorio_data)
        if any(not (factorio_data / mod).exists() for mod in VANILLA_MODS):
            click.secho(
                f"{factorio_data} is not a valid factorio data directory.",
                fg="red",
            )
            raise click.Abort

        for mod in VANILLA_MODS & used_mods:
            click.echo(f"Preparing mod: {mod}")
            prepare_vanilla_mod(factorio_data, mod, target_dir=target_dir)

    if VANILLA_MODS ^ used_mods:
        raise NotImplementedError(
            "Loading other mods than vanilla is not implemented yet."
        )

    click.secho("Prepared all mods, now adding info.json and other files.", fg="green")

if __name__ == "__main__":
    cli()
