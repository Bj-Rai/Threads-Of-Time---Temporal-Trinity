import os
import sys
from pathlib import Path


def resource_path(*parts):
    """Resolve a bundled resource from the project root or PyInstaller bundle."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is None:
        bundle_root = Path(__file__).resolve().parents[1]
    return os.path.join(os.fspath(bundle_root), *(os.fspath(part) for part in parts))


PROJECT_ROOT = resource_path()
ASSET_DIR = resource_path("assets")
IMAGE_DIR = resource_path("assets", "images")
SOUND_DIR = resource_path("assets", "sounds")
OTHER_ASSET_DIR = resource_path("assets", "other")
GAME_IMAGE_DIR = resource_path("assets", "images", "game")
SCENE_IMAGE_DIR = resource_path("assets", "images", "scenes")
LANDMARK_IMAGE_DIR = resource_path("assets", "images", "landmarks")
SACRED_SITE_IMAGE_DIR = resource_path("assets", "images", "sacred_sites")
ICON_IMAGE_DIR = resource_path("assets", "images", "icons")
LEGACY_IMAGE_DIR = resource_path("assets", "images", "root_legacy")
MISC_IMAGE_DIR = resource_path("assets", "images", "misc")
CAPTURED_PHOTO_DIR = resource_path("assets", "images", "captured_photos")


def image_path(*parts):
    return resource_path("assets", "images", *parts)


def sound_path(*parts):
    return resource_path("assets", "sounds", *parts)