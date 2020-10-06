"""Mod function for """
import shutil
from pathlib import Path

VANILLA_MODS = {"core", "base"}


def prepare_vanilla_mod(factorio_data: Path, mod: str, target_dir: Path):
    """Prepare a Vanilla mod in the given target_dir."""
    target_dir = target_dir / "data" / mod / "graphics"
    shutil.copytree(
        factorio_data / mod / "graphics",
        target_dir,
        dirs_exist_ok=True,
    )