CHARACTER_CLASSES = {
    "Custom Explorer": {"description": "A one-of-a-kind traveler", "color": (140, 90, 255), "hat": "custom", "style": "custom", "sprite": "custom_explorer.png"},
    "Horse": {"description": "A swift Bhutanese mount", "color": (150, 100, 65), "hat": "none", "style": "horse", "sprite": "manycharacter.png.jpg"},
    "Mountain Monk": {"description": "Wise & meditative", "color": (200, 150, 50), "hat": "monk", "style": "monk", "sprite": "mountain_monk.png"},
    "Royal Explorer": {"description": "Noble & bold", "color": (255, 215, 0), "hat": "royal", "style": "royal", "sprite": "royal_explorer.png"},
    "Forest Ranger": {"description": "Quick in the wild", "color": (34, 139, 34), "hat": "adventurer", "style": "ranger", "sprite": "forest_ranger.png"},
    "River Guide": {"description": "Master of waterways", "color": (0, 100, 220), "hat": "traditional", "style": "river", "sprite": "river_guide.png"},
    "Village Elder": {"description": "Keeper of tales", "color": (180, 100, 40), "hat": "traditional", "style": "elder", "sprite": "village_elder.png"},
    "Shadow Scout": {"description": "Swift & stealthy", "color": (60, 60, 80), "hat": "adventurer", "style": "scout", "sprite": "shadow_scout.png"},
    "Fire Dancer": {"description": "Energetic & fearless", "color": (220, 80, 20), "hat": "traditional", "style": "dancer", "sprite": "fire_dancer.png"},
    "Star Shaman": {"description": "Mystical & wise", "color": (128, 0, 200), "hat": "monk", "style": "shaman", "sprite": "star_shaman.png"},
}

CHARACTER_CLASS_COSTS = {
    "Custom Explorer": 0,
    "Horse": 350,
    "Mountain Monk": 100,
    "Royal Explorer": 200,
    "Forest Ranger": 150,
    "River Guide": 175,
    "Village Elder": 125,
    "Shadow Scout": 250,
    "Fire Dancer": 225,
    "Star Shaman": 300,
}


def character_class_data(class_name):
    return CHARACTER_CLASSES.get(class_name, CHARACTER_CLASSES["Forest Ranger"])
