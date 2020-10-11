"""CLI interface for generating Factorio-Noir sprites.

Notes:
- On masOS --factorio-data should be /Applications/factorio.app/Contents/data
"""
import json
import os
import pprint
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import click

from factorio_noir.category import SpriteCategory
from factorio_noir.render import process_sprite
from factorio_noir.worker import sprite_processor

MOD_ROOT = Path(__file__).parent.parent.resolve()

VANILLA_MODS = {"core", "base"}
DEFAULT_FACTORIO_DIRS = [
    str(MOD_ROOT.parent / "data"),
    "~/.local/share/Steam/steamapps/common/Factorio/data/",
    "/Applications/factorio.app/Contents/data/",
    "~/Library/Application Support/Steam/steamapps/common/Factorio/factorio.app/Contents/data/",
    "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Factorio\\data\\",
    "C:\\Program Files\\Factorio\\data\\",
]

DEFAULT_MODS_DIRS = [
    str(MOD_ROOT.parent / "mods"),
    "~/.factorio/mods/",
    "~/Library/Application Support/factorio/mods/",
    # 'C:\Program Files (x86)\Steam\userdata\[user number]\427520\remote',
]


def find_default_dir(dirs: List[str]) -> Optional[str]:
    home = os.path.expanduser("~")

    for d in dirs:
        full_dir = Path(d.replace("~", home))

        if full_dir.is_dir():
            return str(full_dir)

    return None


DEFAULT_FACTORIO_DIR = find_default_dir(DEFAULT_FACTORIO_DIRS)
DEFAULT_MODS_DIR = find_default_dir(DEFAULT_MODS_DIRS)


@click.command()
@click.option("--pack-version")
@click.option("--dev", is_flag=True, envvar="DEV")
@click.option(
    "--factorio-data",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    help="Factorio install directory, needed only if packaging Vanilla pack.\n"
    f"Default: {DEFAULT_FACTORIO_DIR}",  # type: ignore
    envvar="FACTORIO_DATA",
    default=DEFAULT_FACTORIO_DIR,
)
@click.option(
    "--factorio-mods",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    help="Factorio mod directory. Needed only if packaging non-vanilla pack.\n"
    f"Default: {DEFAULT_MODS_DIR}",
    envvar="FACTORIO_MODS",
    default=DEFAULT_MODS_DIR,
)
@click.option(
    "--target",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    help="The output directory/zip that should be used",
    envvar="FACTORIO_NOIR_TARGET",
)
@click.argument(
    "pack-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    nargs=-1,
)
@click.pass_context
def cli(
    ctx: click.Context,
    pack_dir: List[Path],
    dev: bool,
    pack_version: str,
    factorio_data: Optional[Path],
    factorio_mods: Optional[Path],
    target: Optional[Path],
):
    if len(pack_dir) == 0:
        click.secho("At least one path to a pack is needed", fg="red")
        raise click.Abort()

    if len(pack_dir) > 1:
        for p in pack_dir:
            ctx.invoke(
                cli,
                pack_dir=[p],
                dev=dev,
                pack_version=pack_version,
                factorio_data=factorio_data,
                factorio_mods=factorio_mods,
                target=target,
            )
        return

    pack_dir = pack_dir[0]
    is_vanilla = Path(pack_dir).name.lower() == "vanilla"

    pack_name = "factorio-noir"
    if not is_vanilla:
        pack_name += f"-{Path(pack_dir).name}"

    if dev is True:
        if target is not None:
            target_dir: Path = Path(target_dir)
        else:
            # for JD h4x
            # target_dir = MOD_ROOT / ".." / "mods" / pack_name
            target_dir = MOD_ROOT / "dist" / "dev" / pack_name

        click.secho(
            f"Using dev directory: {target_dir.relative_to(Path.cwd())}", fg="blue"
        )
        if target_dir.exists() and not target_dir.is_dir():
            click.secho("  - Not a directory, deleting it", fg="yellow")
            target_dir.unlink()
        elif target_dir.exists():
            click.secho("  - Emptying directory", fg="yellow")
            for f in target_dir.iterdir():
                if f.is_file():
                    f.unlink()
                else:
                    shutil.rmtree(f)

        target_dir.mkdir(exist_ok=True, parents=True)

    else:
        target_dir = Path(tempfile.mkdtemp()) / f"{pack_name}_{pack_version}"
        target_dir.mkdir(exist_ok=True, parents=True)
        click.echo(f"Created temporary directory: {target_dir}")

    mods_dirs = []
    if is_vanilla:
        if factorio_data is None:
            click.secho(
                "Missing --factorio-data value, required for editing vanilla graphics.",
                fg="red",
            )
            raise click.Abort

    else:
        if factorio_mods is None:
            click.secho(
                "Missing --factorio-mods value, required for editing mod graphics.",
                fg="red",
            )
            raise click.Abort

    if factorio_data is not None:
        factorio_data = Path(factorio_data)
        if any(not (factorio_data / mod).exists() for mod in VANILLA_MODS):
            click.secho(
                f"{factorio_data} is not a valid factorio data directory.",
                fg="red",
            )
            raise click.Abort

        mods_dirs.append(factorio_data)

    if factorio_mods is not None:
        mods_dirs.append(Path(factorio_mods))

    gen_pack_files(
        pack_dir,
        mods_dirs,
        target_dir,
        pack_name,
        pack_version,
        is_vanilla,
    )

    if dev is True:
        return

    click.echo("Making ZIP package")
    if target is not None:
        zip_loc = Path(target)
    else:
        zip_loc = MOD_ROOT / "dist" / f"{pack_name}_{pack_version}"

    zip_loc.parent.mkdir(parents=True, exist_ok=True)
    archive_name = shutil.make_archive(
        str(zip_loc),
        format="zip",
        root_dir=target_dir.parent,
        base_dir=target_dir.name,
    )
    click.secho(
        f"Created archive for pack: {Path(archive_name).relative_to(Path.cwd())}",
        fg="green",
    )
    click.secho("Removing temp dir, and cleaning up.", fg="yellow")
    shutil.rmtree(target_dir)


def gen_pack_files(
    pack_dir: Path,
    source_dirs: List[Path],
    target_dir: Path,
    pack_name: str,
    pack_version: str,
    is_vanilla: bool,
) -> None:
    """Generate a Factorio-Noir package from pack directory."""
    click.echo(f"Loading categories for pack: {pack_dir}")
    categories = [
        SpriteCategory.from_yaml(category_file, source_dirs)
        for category_file in Path(pack_dir).glob("**/*.yml")
    ]

    used_mods = {m for c in categories for m in c.mods}
    click.secho(
        f"Loaded {len(categories)} categories using a total of {len(used_mods)} mods.",
        fg="green",
    )

    click.secho("Prepared all mods, now adding info.json and other files.", fg="green")
    marked_for_processing = {}

    shutil.copy(MOD_ROOT / "data-final-fixes.lua", target_dir)

    if is_vanilla:
        graphics_dir = target_dir / "data" / "core" / "graphics"
        graphics_dir.mkdir(exist_ok=True, parents=True)

        shutil.copy(MOD_ROOT / "background-image.jpg", graphics_dir)
        marked_for_processing["__core__/graphics/background-image.jpg"] = "<Builtin>"

    click.echo("Patching the info.json file")
    with (MOD_ROOT / "info.json").open() as file:
        info_file = json.load(file)

    info_file["name"] = pack_name

    if not is_vanilla:
        info_file["title"] += " - " + pack_name

    if pack_version is not None:
        info_file["version"] = pack_version

    info_file["dependencies"].extend(used_mods - VANILLA_MODS)

    with (target_dir / "info.json").open("w") as file:
        json.dump(info_file, file, indent=4, sort_keys=True)

    click.echo("Starting to process sprites")
    with sprite_processor(process_sprite) as submit:
        with click.progressbar(categories, label="Make sprites tasks") as progress:
            for category in progress:
                for mod, sprite_path in category.sprite_paths():
                    lua_path = f"__{mod.name}__/{sprite_path}"

                    if lua_path in marked_for_processing:
                        click.echo()
                        click.secho(
                            f"The sprite {lua_path} was included in processing "
                            f"from more than one category: \n"
                            f"    {str(category.source)}\n"
                            f"    {marked_for_processing[lua_path]}",
                            fg="red",
                        )
                        raise click.Abort()
                    marked_for_processing[lua_path] = str(category.source)

                    # We want lazy access to the file because contextmanager seralizes
                    # the file with pickel
                    submit(
                        lazy_source_file=mod.lazy_file(sprite_path),
                        target_file_path=target_dir / "data" / mod.name / sprite_path,
                        treatment=category.treatment,
                    )

    # inform lua which files need to be replaced
    with (target_dir / "config.lua").open("w") as file:
        file.write(
            """
return {
    is_vanilla = %s,
    resource_pack_name = "%s",
    updated_assets = {
"""
            % (str(is_vanilla).lower(), pack_name)
        )

        for asset in sorted(marked_for_processing.keys()):
            file.write('["%s"]=1,\n' % asset)

        file.write("    },\n")
        file.write("}\n")


if __name__ == "__main__":
    cli()
