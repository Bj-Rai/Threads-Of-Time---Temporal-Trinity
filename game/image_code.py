import os

import pygame

from .resource_paths import GAME_IMAGE_DIR, LEGACY_IMAGE_DIR


def load_certificate_image(image_name="Threads of Time exploration certificate.png"):
    image_paths = [
        os.path.join(GAME_IMAGE_DIR, image_name),
        os.path.join(LEGACY_IMAGE_DIR, image_name),
    ]
    for image_path in image_paths:
        try:
            if os.path.exists(image_path):
                return pygame.image.load(image_path).convert()
        except (pygame.error, OSError):
            continue
    return None
