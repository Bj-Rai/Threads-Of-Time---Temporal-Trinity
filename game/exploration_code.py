WALK_SPEED_MULTIPLIER = 1.5


def move_explorer(explorer, keys):
    explorer.move(
        keys,
        [],
        exploration_mode=True,
        terrain_modifier=WALK_SPEED_MULTIPLIER,
    )
