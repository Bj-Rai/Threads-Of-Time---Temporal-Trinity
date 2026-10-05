import pygame
import sys
import math
import random
import json
import os
from enum import Enum
from typing import cast

from game.certificate_code import show_completion_certificate as render_completion_certificate
from game.character_code import CHARACTER_CLASSES, CHARACTER_CLASS_COSTS, character_class_data
from game.exploration_code import WALK_SPEED_MULTIPLIER, move_explorer
from game.image_code import load_certificate_image
from game.quiz_data import CULTURAL_QUIZ_DATA
from game.resource_paths import (
    GAME_IMAGE_DIR,
    LANDMARK_IMAGE_DIR,
    LEGACY_IMAGE_DIR,
    MISC_IMAGE_DIR,
    SACRED_SITE_IMAGE_DIR,
    SCENE_IMAGE_DIR,
    sound_path,
)
from game.systems import PhotoJournal, Reputation, Skill, SkillType

_FONT_CACHE = {}


def cached_font(size):
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
WORLD_WIDTH = SCREEN_WIDTH * 4
WORLD_HEIGHT = SCREEN_HEIGHT * 4
GAME_TITLE = "THREADS OF TIME"
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
LIGHT_BLUE = (173, 216, 230)
DARK_GREEN = (0, 150, 0)
GOLD = (255, 215, 0)
BROWN = (139, 69, 19)
DARK_RED = (139, 0, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
DARK_BLUE = (0, 0, 139)
LIGHT_GREEN = (144, 238, 144)
WHEAT = (245, 222, 179)
DARK_ORANGE = (255, 140, 0)
LIGHT_BROWN = (200, 150, 100)
DARK_BROWN = (100, 70, 40)
STONE = (128, 128, 128)
SAND = (238, 214, 175)
FOREST_GREEN = (34, 139, 34)
DEEP_FOREST = (20, 90, 20)

# Terrain Types
class TerrainType(Enum):
    FOREST_PATH = "forest_path"
    MOUNTAIN_TRAIL = "mountain_trail"
    MOUNTAIN_PASS = "mountain_pass"   # high-altitude pass terrain
    RIVER_CROSSING = "river_crossing"
    TEMPLE_GROUNDS = "temple_grounds"
    VILLAGE_PATH = "village_path"
    VALLEY_MEADOW = "valley_meadow"

    @property
    def speed_modifier(self):
        modifiers = {
            TerrainType.FOREST_PATH: 0.8,
            TerrainType.MOUNTAIN_TRAIL: 0.5,
            TerrainType.MOUNTAIN_PASS: 0.45,
            TerrainType.RIVER_CROSSING: 0.4,
            TerrainType.TEMPLE_GROUNDS: 1.0,
            TerrainType.VILLAGE_PATH: 1.2,
            TerrainType.VALLEY_MEADOW: 0.9
        }
        return modifiers.get(self, 0.8)

    @property
    def color(self):
        colors = {
            TerrainType.FOREST_PATH: (0, 180, 0),
            TerrainType.MOUNTAIN_TRAIL: (0, 160, 0),
            TerrainType.MOUNTAIN_PASS: (140, 140, 100),
            TerrainType.RIVER_CROSSING: (0, 200, 50),
            TerrainType.TEMPLE_GROUNDS: (0, 210, 0),
            TerrainType.VILLAGE_PATH: (50, 220, 50),
            TerrainType.VALLEY_MEADOW: (0, 230, 0)
        }
        return colors.get(self, (0, 180, 0))

# Time of Day
class TimeOfDay(Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"

    @property
    def visibility_radius(self):
        radii = {TimeOfDay.DAWN: 300, TimeOfDay.DAY: 600, TimeOfDay.DUSK: 250, TimeOfDay.NIGHT: 120}
        return radii[self]

    @property
    def ambient_color(self):
        colors = {TimeOfDay.DAWN: (255, 200, 150), TimeOfDay.DAY: (255, 255, 245), 
                  TimeOfDay.DUSK: (180, 120, 80), TimeOfDay.NIGHT: (50, 50, 80)}
        return colors[self]

# Particle System
class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, screen, camera_x, camera_y):
        alpha = self.lifetime / self.max_lifetime
        color = tuple(int(c * alpha) for c in self.color)
        pygame.draw.circle(screen, color, (int(self.x - camera_x), int(self.y - camera_y)), 2)

# Wildlife Class
class Wildlife:
    def __init__(self, x, y, animal_type):
        self.x = x
        self.y = y
        self.animal_type = animal_type
        self.animation_offset = random.uniform(0, 2 * math.pi)
        self.active = True
        self.move_pattern = random.choice(["circle", "zigzag", "still"])
        self.move_x = random.uniform(-0.5, 0.5)
        self.move_y = random.uniform(-0.5, 0.5)
        
    def update(self):
        if self.move_pattern == "circle":
            self.animation_offset += 0.03
            self.x += math.sin(self.animation_offset) * 1
            self.y += math.cos(self.animation_offset * 0.7) * 1
        elif self.move_pattern == "zigzag":
            self.animation_offset += 0.05
            self.x += math.sin(self.animation_offset) * 1.5
            self.y += self.move_y
        else:
            self.x += self.move_x
            self.y += self.move_y
            
        if self.x < 0 or self.x > WORLD_WIDTH or self.y < 0 or self.y > WORLD_HEIGHT:
            self.active = False
            
    def draw(self, screen, camera_x, camera_y):
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        float_y = math.sin(self.animation_offset * 2) * 3
        
        if self.animal_type == "bird":
            points = [
                (draw_x, draw_y + float_y),
                (draw_x - 8, draw_y - 5 + float_y),
                (draw_x - 3, draw_y + float_y),
                (draw_x + 3, draw_y + float_y),
                (draw_x + 8, draw_y - 5 + float_y),
                (draw_x, draw_y + float_y)
            ]
            pygame.draw.lines(screen, BLACK, False, points, 2)
        elif self.animal_type == "deer":
            pygame.draw.ellipse(screen, BROWN, (draw_x - 8, draw_y - 5, 16, 12))
            pygame.draw.circle(screen, BROWN, (draw_x - 6, draw_y - 8), 4)
            pygame.draw.line(screen, BROWN, (draw_x - 4, draw_y - 12), (draw_x - 6, draw_y - 18), 2)
            pygame.draw.line(screen, BROWN, (draw_x - 1, draw_y - 12), (draw_x, draw_y - 18), 2)
        else:
            angle1 = math.sin(self.animation_offset) * 30
            angle2 = math.cos(self.animation_offset) * 30
            pygame.draw.polygon(screen, (255, 150, 50), [(draw_x, draw_y), (draw_x - 8 + math.sin(angle1), draw_y - 5), (draw_x, draw_y)])
            pygame.draw.polygon(screen, (255, 150, 50), [(draw_x, draw_y), (draw_x + 8 + math.cos(angle2), draw_y - 5), (draw_x, draw_y)])

# Game States
class GameState(Enum):
    INTRO = 0
    MAIN_MENU = 1
    CHARACTER_CUSTOMIZATION = 2
    SONG_SHOP = 3
    LEVEL_SELECT = 4
    DISTRICT_INFO = 5
    EXPLORATION = 6
    CULTURAL_CHALLENGE = 7
    GAME_OVER = 8
    VICTORY = 9
    BHUTAN_MAP = 10
    RAID = 11

def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
    if not text:
        return []
    
    # Convert to string if needed
    text = str(text)
    
    # Handle short texts
    if font.render(text, True, WHITE).get_width() <= max_width:
        return [text]
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        test_surface = font.render(test_line, True, WHITE)
        if test_surface.get_width() <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

# ============================================
# ALL 20 DZONGKHAGS — COMPLETE DATA
# ============================================

sample_sacred_sites = [
    {"name": "Tashichho Dzong", "description": "Fortress of Glorious Religion", "history": "Built in 1641, rebuilt in 1960s.", "significance": "Summer residence of the Central Monk Body", "fun_fact": "Only dzong with electric lighting", "legend": "Built on the site where a powerful demon was subdued"},
    {"name": "Memorial Chorten", "description": "Tibetan-style stupa", "history": "Built in 1974 in memory of the Third Druk Gyalpo.", "significance": "Dedicated to world peace", "fun_fact": "Open 24/7 for prayers", "legend": "The Third King's spirit protects all who pray here."},
    {"name": "Buddha Dordenma", "description": "Giant Buddha statue", "history": "Completed in 2015", "significance": "Granting blessings of peace", "fun_fact": "Contains 125,000 smaller Buddha statues", "legend": "Fulfills an ancient prophecy"},
    {"name": "Tango Monastery", "description": "Buddhist university", "history": "Founded in the 12th century", "significance": "Center for Buddhist studies", "fun_fact": "Offers stunning views", "legend": "The site was blessed by Guru Rinpoche"},
    {"name": "Changangkha Lhakhang", "description": "Ancient temple", "history": "Built in the 15th century", "significance": "Protects the children of Thimphu", "fun_fact": "Located on a ridge", "legend": "Blessed by a great Buddhist master"}
]

bhutan_districts = [
    # ── 1. THIMPHU (original data preserved) ──────────────────────────────────
    {
        "name": "Thimphu",
        "icon": "🏛️",
        "region": "Western",
        "region_color": (0, 100, 255),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Thimphu Dzongkhag",
        "population": "138,000",
        "main_ethnic_groups": "Ngalop, Lhotshampa",
        "traditional_occupations": "Government service, tourism, handicrafts",
        "famous_personalities": "King Jigme Dorji Wangchuck",
        "historical_significance": "Thimphu became the capital of Bhutan in 1961.",
        "religious_importance": "Home to Tashichho Dzong, Memorial Chorten, and Buddha Dordenma.",
        "sacred_sites": sample_sacred_sites,
        "cultural_practices": {
            "festivals": [{"name": "Thimphu Tsechu", "months": "September/October", "highlights": "Mask dances"}],
            "arts": ["Traditional weaving", "Thangka painting", "Wood carving"],
            "cuisine": ["Ema Datshi", "Momos", "Jasha Maroo"],
            "etiquette_tips": ["Walk clockwise around chortens", "Remove shoes before entering dzongs"]
        },
        "local_stories": ["A master weaver named Aum Pema has been creating traditional patterns for over 40 years."],
        "wisdom_quotes": ["'True development is measured by happiness, not wealth.'"],
        "unique_facts": ["Only capital city without traffic lights", "Traffic police use elaborate hand signals"],
        "completion_reward": "Thimphu Culture Expert",
        "required_knowledge": 70,
        "tour_narration": "Welcome to Thimphu, the modern heart of Bhutan!",
        "cultural_challenge": {"question": "What is the capital of Bhutan?", "options": ["Paro", "Punakha", "Thimphu", "Trashigang"], "answer": "Thimphu"},
        "hidden_secrets": [
            {"name": "Ancient Prayer Wheel", "xp": 50, "description": "A hidden 500-year-old prayer wheel"},
            {"name": "Royal Photograph", "xp": 30, "description": "A rare photo of the Third King"},
            {"name": "Secret Garden", "xp": 45, "description": "A hidden garden with rare Himalayan flowers"}
        ],
        "terrain_type": TerrainType.VILLAGE_PATH.name
    },
    # ── 2. PARO ───────────────────────────────────────────────────────────────
    {
        "name": "Paro",
        "icon": "🏯",
        "region": "Western",
        "region_color": (0, 120, 220),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Paro Dzongkhag",
        "population": "43,000",
        "main_ethnic_groups": "Ngalop",
        "traditional_occupations": "Farming, apple orchards, tourism",
        "famous_personalities": "Pema Lingpa (treasure discoverer)",
        "historical_significance": "Paro is home to Bhutan's only international airport and the famous Tiger's Nest monastery.",
        "religious_importance": "Taktsang Palphug Monastery (Tiger's Nest) is Bhutan's most sacred site.",
        "sacred_sites": [
            {"name": "Taktsang Monastery", "description": "Tiger's Nest perched on a cliff", "history": "Guru Rinpoche meditated here in the 8th century", "significance": "Most sacred site in Bhutan", "fun_fact": "Clings to a 900 m cliff face", "legend": "Guru Rinpoche flew here on a tigress"},
            {"name": "Ta Dzong", "description": "Historic watchtower overlooking the Paro valley", "history": "Built as a watchtower to defend the Paro valley", "significance": "Preserves Paro's military and cultural heritage", "fun_fact": "It now houses the National Museum of Bhutan", "legend": "The tower is said to watch over the valley like a guardian"},
            {"name": "Drukgyel Dzong", "description": "Ruined victory fortress", "history": "Built in 1649 to commemorate victory over Tibetan invaders", "significance": "Symbol of Bhutanese military strength", "fun_fact": "Destroyed by fire in 1951", "legend": "Soldiers' spirits still guard the ruins"},
            {"name": "Kyichu Lhakhang", "description": "One of the oldest temples in Bhutan", "history": "Built in the 7th century by Tibetan King Songtsen Gampo", "significance": "Pins down a demoness's left foot", "fun_fact": "Contains a 7th-century orange tree that never dies", "legend": "The orange tree is protected by divine blessings"},
            {"name": "Rinpung Dzong", "description": "Fortress of the Heap of Jewels", "history": "Founded in 1644", "significance": "Houses monks and the district administration", "fun_fact": "Connected to town by a traditional cantilever bridge", "legend": "Built over a serpent spirit's home"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Paro Tsechu", "months": "March/April", "highlights": "Giant thangka unfurling and cham dances"}],
            "arts": ["Thangka painting", "Bronze casting", "Weaving"],
            "cuisine": ["Ema Datshi", "Red rice", "Buckwheat pancakes"],
            "etiquette_tips": ["Dress modestly near monasteries", "Ask permission before photographing monks"]
        },
        "local_stories": ["Farmers say apple orchards were blessed by Guru Rinpoche himself."],
        "wisdom_quotes": ["'Even the highest mountain was once a valley.'"],
        "unique_facts": ["Only international airport in Bhutan", "One of the world's most challenging airports to land at"],
        "completion_reward": "Tiger's Nest Pilgrim",
        "required_knowledge": 65,
        "tour_narration": "Welcome to Paro, valley of legends and breathtaking cliffs!",
        "cultural_challenge": {"question": "What is the local name for Tiger's Nest monastery?", "options": ["Rinpung Dzong", "Kyichu Lhakhang", "Taktsang Palphug", "Drukgyel Dzong"], "answer": "Taktsang Palphug"},
        "hidden_secrets": [
            {"name": "Ancient Butter Lamp", "xp": 55, "description": "A 700-year-old lamp still burning in Kyichu"},
            {"name": "Tiger Paw Print", "xp": 40, "description": "Stone imprint said to be from Guru's tigress"},
            {"name": "Hidden Cave Shrine", "xp": 60, "description": "A tiny cave shrine above the main trail"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 3. PUNAKHA ────────────────────────────────────────────────────────────
    {
        "name": "Punakha",
        "icon": "🌸",
        "region": "Western",
        "region_color": (50, 150, 80),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Punakha Dzongkhag",
        "population": "28,000",
        "main_ethnic_groups": "Ngalop",
        "traditional_occupations": "Rice farming, weaving, beekeeping",
        "famous_personalities": "Zhabdrung Ngawang Namgyal (founder of modern Bhutan)",
        "historical_significance": "Punakha served as Bhutan's capital until 1955.",
        "religious_importance": "Punakha Dzong houses the sacred relic of Zhabdrung Ngawang Namgyal.",
        "sacred_sites": [
            {"name": "Punakha Dzong", "description": "Palace of Great Happiness", "history": "Built in 1637 at the confluence of two rivers", "significance": "Religious and administrative capital until 1955", "fun_fact": "Hosts royal weddings", "legend": "A saint predicted a palace would be built where two rivers meet"},
            {"name": "Chimi Lhakhang", "description": "Temple of the Divine Madman", "history": "Built in 1499 by the nephew of Drukpa Kunley", "significance": "Fertility temple, visited by childless couples", "fun_fact": "Phallus symbols decorate the walls", "legend": "Drukpa Kunley subdued a demon here"},
            {"name": "Khamsum Yulley Namgyal Chorten", "description": "Four-story stupa on a hilltop", "history": "Completed in 1999", "significance": "Built to promote peace and harmony", "fun_fact": "Commands panoramic views of Punakha valley", "legend": "Protects the valley from evil spirits"},
            {"name": "Nalanda Buddhist College", "description": "Centre for advanced Buddhist studies", "history": "Established in the 20th century", "significance": "Trains monks in philosophy and arts", "fun_fact": "Named after the ancient Indian university", "legend": "Scholars say wisdom flows through its halls like the Mo Chhu river"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Punakha Drubchen", "months": "February/March", "highlights": "Re-enactment of a 17th-century battle"}],
            "arts": ["Silk weaving", "Bamboo craft", "Mask making"],
            "cuisine": ["River fish curry", "Red rice", "Hoentoe dumplings"],
            "etiquette_tips": ["Always walk clockwise around the dzong", "Speak quietly near the sanctuary"]
        },
        "local_stories": ["Farmers plant rice to the rhythm of ancient songs to ensure good harvests."],
        "wisdom_quotes": ["'Where two rivers meet, blessings multiply.'"],
        "unique_facts": ["Warmest valley in Bhutan, known as the Rice Bowl", "Royal wedding of King Jigme Khesar held here in 2011"],
        "completion_reward": "Valley of Happiness Keeper",
        "required_knowledge": 65,
        "tour_narration": "Welcome to Punakha, the fertile valley where rivers and history merge!",
        "cultural_challenge": {"question": "At which confluence is Punakha Dzong built?", "options": ["Pho Chhu & Mo Chhu", "Wang Chhu & Paro Chhu", "Manas & Chamkhar", "Drangme & Kuri"], "answer": "Pho Chhu & Mo Chhu"},
        "hidden_secrets": [
            {"name": "Silver Reliquary", "xp": 65, "description": "A small silver box containing sacred relics"},
            {"name": "Ancient Battle Map", "xp": 35, "description": "A faded map of the 1639 victory"},
            {"name": "Fertile Spring", "xp": 50, "description": "A hidden spring said to grant fertility"}
        ],
        "terrain_type": TerrainType.RIVER_CROSSING.name
    },
    # ── 4. BUMTHANG ───────────────────────────────────────────────────────────
    {
        "name": "Bumthang",
        "icon": "🕌",
        "region": "Central",
        "region_color": (180, 100, 30),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Bumthang Dzongkhag",
        "population": "17,000",
        "main_ethnic_groups": "Bumthap, Kheng",
        "traditional_occupations": "Yak herding, weaving, apple farming, honey",
        "famous_personalities": "Pema Lingpa (15th-century treasure revealer)",
        "historical_significance": "Bumthang is the spiritual heartland of Bhutan with over 60 monasteries.",
        "religious_importance": "Jampa Lhakhang is one of Bhutan's most ancient temples, built in the 7th century.",
        "sacred_sites": [
            {"name": "Jakar Dzong", "description": "Castle of the White Bird", "history": "Founded in 1549", "significance": "Administrative seat and major monastery", "fun_fact": "Largest dzong in Bhutan", "legend": "A white bird circled the site, guiding its location"},
            {"name": "Jampa Lhakhang", "description": "One of Bhutan's oldest temples", "history": "Built in 659 AD by Tibetan king Songtsen Gampo", "significance": "Pins a demoness's left knee", "fun_fact": "One of 108 temples built in a single day", "legend": "Built to subdue a giant demoness across the Himalayas"},
            {"name": "Kurjey Lhakhang", "description": "Temple of the Body Print", "history": "Guru Rinpoche meditated here in the 8th century", "significance": "Rock bears the body print of Guru Rinpoche", "fun_fact": "Three temples built across three centuries", "legend": "Guru Rinpoche left his body imprint on the rock"},
            {"name": "Tamshing Lhakhang", "description": "Temple of Good Message", "history": "Founded by Pema Lingpa in 1501", "significance": "Contains Pema Lingpa's own chain-mail shirt", "fun_fact": "Pilgrims carry the chain-mail for good luck", "legend": "Wearing the chain-mail cures illness"},
            {"name": "Membartsho", "description": "Burning Lake", "history": "Pema Lingpa revealed hidden treasures here", "significance": "Sacred pond where treasures were revealed", "fun_fact": "Name means 'flaming lake'", "legend": "Pema Lingpa swam into the lake with a lamp that burned even underwater"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Jambay Lhakhang Drup", "months": "October/November", "highlights": "Fire ceremony and naked dance at midnight"}],
            "arts": ["Kishuthara silk weaving", "Yathra wool weaving", "Incense making"],
            "cuisine": ["Buckwheat pancakes", "Bumthang cheese", "Ara (local spirit)", "Buckwheat noodles"],
            "etiquette_tips": ["Never disturb meditating monks", "Offer juniper incense at shrines"]
        },
        "local_stories": ["Pema Lingpa is said to have discovered 27 terma (hidden treasures) from lakes and rocks."],
        "wisdom_quotes": ["'The flame that burns underwater cannot be extinguished by doubt.'"],
        "unique_facts": ["Known as the Switzerland of Bhutan for its alpine meadows", "Produces Bhutan's best honey and buckwheat"],
        "completion_reward": "Spiritual Heartland Guardian",
        "required_knowledge": 75,
        "tour_narration": "Welcome to Bumthang, the sacred valley where saints walked and miracles happened!",
        "cultural_challenge": {"question": "Who founded Tamshing Lhakhang in 1501?", "options": ["Guru Rinpoche", "Pema Lingpa", "Zhabdrung", "Songtsen Gampo"], "answer": "Pema Lingpa"},
        "hidden_secrets": [
            {"name": "Burning Lake Pearl", "xp": 70, "description": "A smooth stone from Membartsho said to glow at night"},
            {"name": "Pema Lingpa's Scroll", "xp": 55, "description": "A fragment of an ancient terma revelation text"},
            {"name": "Sacred Honey Cache", "xp": 40, "description": "Wild honey from hives on ancient monastery walls"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 5. WANGDUE PHODRANG ───────────────────────────────────────────────────
    {
        "name": "Wangdue Phodrang",
        "icon": "🌊",
        "region": "Central",
        "region_color": (30, 120, 160),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Wangdue Phodrang Dzongkhag",
        "population": "35,000",
        "main_ethnic_groups": "Ngalop, Nyamkap",
        "traditional_occupations": "Slate and slate carving, bamboo weaving, farming",
        "famous_personalities": "Wangdi Phodrang (noble commander after whom the district is named)",
        "historical_significance": "Wangdue Phodrang controls the route between western and central Bhutan.",
        "religious_importance": "Gangtey Monastery is a major centre for the Nyingma school of Buddhism.",
        "sacred_sites": [
            {"name": "Wangdue Phodrang Dzong", "description": "Strategic fortress at a river confluence", "history": "Built in 1638 by Zhabdrung Ngawang Namgyal", "significance": "Controls passage to central and southern Bhutan", "fun_fact": "Partially rebuilt after a 2012 fire", "legend": "A child playing with a raven chose the site"},
            {"name": "Gangtey Monastery", "description": "Ancient Nyingma monastery on a hill", "history": "Founded in the 17th century by Gyalse Pema Thinley", "significance": "Seat of the Gangtey Tulku lineage", "fun_fact": "Surrounded by the Phobjikha Valley wetlands", "legend": "The valley was chosen because cranes arrive each winter as a divine sign"},
            {"name": "Phobjikha Valley", "description": "Glacial valley wintering ground for black-necked cranes", "history": "Protected since 1993", "significance": "Critical habitat for endangered cranes", "fun_fact": "Cranes arrive on the same day each year", "legend": "Cranes circle Gangtey Monastery three times before landing"},
            {"name": "Rinchengang Village", "description": "Ancient fortress village on a cliff", "history": "Centuries-old community of craftsmen", "significance": "Famous for slate carving and weaving", "fun_fact": "Residents must climb a steep path to reach it", "legend": "The village was built by a clan of stonemasons with divine gifts"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Gangtey Tsechu", "months": "September/October", "highlights": "Cham dances at Gangtey Monastery"}],
            "arts": ["Slate carving", "Bamboo weaving", "Woollen textiles"],
            "cuisine": ["Phaksha Paa (pork with chilli)", "Red rice", "Nakey (fern fronds)"],
            "etiquette_tips": ["Stay on designated crane-watching paths", "Do not disturb crane roosting areas"]
        },
        "local_stories": ["Villagers say the cranes bring luck, and years without cranes bring poor harvests."],
        "wisdom_quotes": ["'The crane returns each winter to remind us that beauty is worth protecting.'"],
        "unique_facts": ["Black-necked cranes winter exclusively in Phobjikha Valley in Bhutan", "Slate carvers here have supplied dzongs across the country"],
        "completion_reward": "Crane Valley Warden",
        "required_knowledge": 70,
        "tour_narration": "Welcome to Wangdue Phodrang, where cranes dance and rivers carve ancient paths!",
        "cultural_challenge": {"question": "Which endangered bird winters in Phobjikha Valley?", "options": ["Snow Leopard", "Black-necked Crane", "Red Panda", "Takin"], "answer": "Black-necked Crane"},
        "hidden_secrets": [
            {"name": "Crane Feather Talisman", "xp": 55, "description": "A sacred feather left behind by migrating cranes"},
            {"name": "Ancient Slate Carving", "xp": 45, "description": "A centuries-old carved prayer on a cliff face"},
            {"name": "Hidden Wetland Spring", "xp": 40, "description": "A secret freshwater spring used by the cranes"}
        ],
        "terrain_type": TerrainType.RIVER_CROSSING.name
    },
    # ── 6. TRONGSA ────────────────────────────────────────────────────────────
    {
        "name": "Trongsa",
        "icon": "🏰",
        "region": "Central",
        "region_color": (120, 60, 20),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Trongsa Dzongkhag",
        "population": "18,000",
        "main_ethnic_groups": "Ngalop, Kheng",
        "traditional_occupations": "Cattle herding, weaving, orange farming",
        "famous_personalities": "Ugyen Wangchuck (first King of Bhutan)",
        "historical_significance": "All kings of Bhutan have served as Trongsa Penlop (governor) before ascending the throne.",
        "religious_importance": "Trongsa Dzong is the ancestral home of the Wangchuck dynasty.",
        "sacred_sites": [
            {"name": "Trongsa Dzong", "description": "Ancestral seat of Bhutan's royal family", "history": "Built in 1648, expanded over centuries", "significance": "Whoever controls Trongsa controls Bhutan", "fun_fact": "Over 25 temples within its walls", "legend": "Built on a ridge chosen by a monk who heard divine music"},
            {"name": "Ta Dzong (Tower of Trongsa)", "description": "Watchtower converted to a royal museum", "history": "Built in 1652 as a defence tower", "significance": "Now houses royal artefacts and regalia", "fun_fact": "Contains the coronation robes of all five kings", "legend": "Soldiers stationed here never lost a battle"},
            {"name": "Kuenga Rabten Palace", "description": "Winter retreat of the second king", "history": "Built in the 1930s", "significance": "A rare example of traditional Bhutanese palace architecture", "fun_fact": "Largely preserved in its original state", "legend": "The second king chose this spot after meditating for three days"},
            {"name": "Chendebji Chorten", "description": "Tibetan-style stupa in a river valley", "history": "Built in the 18th century", "significance": "Built to subdue an evil spirit", "fun_fact": "Modelled after Swayambhunath in Nepal", "legend": "A demon was trapped beneath the stupa's foundation"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Trongsa Tsechu", "months": "December/January", "highlights": "Rare winter tsechu with thangka display"}],
            "arts": ["Kishuthara silk weaving", "Red clay pottery", "Lacquerware"],
            "cuisine": ["Orange (fresh and dried)", "Ezay (chilli sauce)", "Beef with red rice"],
            "etiquette_tips": ["Bow your head when passing monks", "Offer small gifts to monastery caretakers"]
        },
        "local_stories": ["People say whoever sees Trongsa Dzong from the road is blessed with good fortune for the journey."],
        "wisdom_quotes": ["'The road to kingship passes through service to the people.'"],
        "unique_facts": ["Only place you can see two waterfalls from a single dzong", "Annual orange festival draws visitors from across Bhutan"],
        "completion_reward": "Royal Ancestral Guardian",
        "required_knowledge": 72,
        "tour_narration": "Welcome to Trongsa, the royal heartland where kings are made!",
        "cultural_challenge": {"question": "What title must a future king of Bhutan hold before coronation?", "options": ["Desi", "Trongsa Penlop", "Druk Gyalpo", "Dasho"], "answer": "Trongsa Penlop"},
        "hidden_secrets": [
            {"name": "Royal Seal Fragment", "xp": 60, "description": "A fragment of an ancient royal wax seal"},
            {"name": "Coronation Robe Thread", "xp": 50, "description": "A golden thread from a historic coronation robe"},
            {"name": "Hidden Watchtower Room", "xp": 45, "description": "A secret chamber in the old fortress wall"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 7. TRASHIGANG ─────────────────────────────────────────────────────────
    {
        "name": "Trashigang",
        "icon": "🌄",
        "region": "Eastern",
        "region_color": (200, 80, 20),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Trashigang Dzongkhag",
        "population": "110,000",
        "main_ethnic_groups": "Sharchop, Brokpa",
        "traditional_occupations": "Weaving, orange farming, areca nut cultivation",
        "famous_personalities": "Desi Tenzin Rabgye (17th-century administrator)",
        "historical_significance": "Trashigang is Bhutan's largest dzongkhag and eastern trade gateway.",
        "religious_importance": "Trashigang Dzong overlooks the confluence of the Gamri and Drangme rivers.",
        "sacred_sites": [
            {"name": "Trashigang Dzong", "description": "Auspicious Mountain Fortress", "history": "Built in 1659 atop a cliff", "significance": "Administrative and cultural centre of eastern Bhutan", "fun_fact": "No road reached it until 1965", "legend": "Built where an eagle dropped a sacred object"},
            {"name": "Gom Kora", "description": "Sacred meditation site by the river", "history": "Guru Rinpoche meditated in a rock hollow here", "significance": "Annual festival draws thousands of pilgrims", "fun_fact": "Pilgrims circumambulate the rock at night", "legend": "Guru Rinpoche wrestled a demon into the rock"},
            {"name": "Drametse Monastery", "description": "Home of the famous drum dance", "history": "Founded in the 16th century", "significance": "Birthplace of Drametse Ngacham drum dance (UNESCO heritage)", "fun_fact": "16 musicians perform the drum dance", "legend": "The dance was revealed in a divine vision"},
            {"name": "Merak Sakteng Wildlife Sanctuary", "description": "Remote sanctuary of the Brokpa people", "history": "Protected since 1993", "significance": "Habitat of takin and snow leopard", "fun_fact": "Brokpa people wear hats made of yak hair", "legend": "The yeti is said to roam these forests"},
            {"name": "Bartsham Lhakhang", "description": "Ancient temple above the Gamri River", "history": "Founded in the 15th century", "significance": "Houses rare thangkas and statues", "fun_fact": "Accessed via a rope-bridge", "legend": "A saint tamed a water demon here and built the temple"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Gom Kora Festival", "months": "March", "highlights": "Night-time pilgrimage around the sacred rock"}],
            "arts": ["Kishuthara silk weaving", "Cane and bamboo craft", "Drum making"],
            "cuisine": ["Chilli beef", "Wild mushroom soup", "Areca nut with betel leaf"],
            "etiquette_tips": ["Always greet elders with 'Kuzu Zangpo La'", "Do not point at sacred rocks or trees"]
        },
        "local_stories": ["The Brokpa nomads say the yeti once guided a lost herder home during a snowstorm."],
        "wisdom_quotes": ["'A journey to the east is a journey into the roots of Bhutan.'"],
        "unique_facts": ["Largest dzongkhag by area in Bhutan", "UNESCO-inscribed Drametse drum dance originated here"],
        "completion_reward": "Eastern Gateway Master",
        "required_knowledge": 80,
        "tour_narration": "Welcome to Trashigang, the vast eastern frontier of Bhutan!",
        "cultural_challenge": {"question": "Which UNESCO Intangible Heritage dance originated in Trashigang?", "options": ["Cham Dance", "Drametse Ngacham", "Tercham", "Zhungdra"], "answer": "Drametse Ngacham"},
        "hidden_secrets": [
            {"name": "Brokpa Yak-Hair Hat", "xp": 50, "description": "A traditional hat worn by nomadic Brokpa people"},
            {"name": "Gom Kora Stone Imprint", "xp": 65, "description": "A handprint said to be Guru Rinpoche's"},
            {"name": "Ancient Trade Coin", "xp": 40, "description": "An old coin from the eastern trade route era"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 8. MONGAR ─────────────────────────────────────────────────────────────
    {
        "name": "Mongar",
        "icon": "🌲",
        "region": "Eastern",
        "region_color": (60, 160, 60),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Mongar Dzongkhag",
        "population": "42,000",
        "main_ethnic_groups": "Sharchop, Kheng",
        "traditional_occupations": "Weaving, maize farming, cardamom cultivation",
        "famous_personalities": "Lam Nado (revered local saint)",
        "historical_significance": "Mongar is a key junction on the eastern highway, connecting central and far-east Bhutan.",
        "religious_importance": "Mongar Dzong presides over the administrative and spiritual life of the region.",
        "sacred_sites": [
            {"name": "Mongar Dzong", "description": "Modern dzong built in traditional style", "history": "Built in the 1930s, expanded in the 1990s", "significance": "Administrative and religious centre", "fun_fact": "One of the few dzongs built in the 20th century", "legend": "Site blessed by a visiting lama who cured the land of plague"},
            {"name": "Ngatshang Gonpa", "description": "Perched monastery above Kuri Chhu", "history": "Founded in the 15th century", "significance": "Major pilgrimage site in eastern Bhutan", "fun_fact": "Reached by a steep two-hour hike", "legend": "A meditating monk was protected by a snow lion here"},
            {"name": "Lhungtenzampa Bridge", "description": "Traditional cantilever bridge", "history": "Built using ancient carpentry techniques", "significance": "Links remote villages across the Kuri Chhu", "fun_fact": "No nails used in construction", "legend": "Carpenters prayed for three days before beginning work"},
            {"name": "Bumdeling Wildlife Sanctuary", "description": "Northern sanctuary bordering Tibet", "history": "Declared a sanctuary in 2003", "significance": "Key habitat for takin, leopard, and migratory birds", "fun_fact": "Name means 'the place of a hundred monasteries'", "legend": "Ancient prophecy says the sanctuary hides a sacred valley (beyul)"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Mongar Tsechu", "months": "October/November", "highlights": "Traditional cham dances and archery"}],
            "arts": ["Raw silk weaving", "Cane basketry", "Paper making from Daphne bark"],
            "cuisine": ["Cardamom tea", "Maize porridge", "Dried beef with chilli"],
            "etiquette_tips": ["Offer tea to elders before speaking", "Always accept food with both hands"]
        },
        "local_stories": ["Weavers say the finest silk patterns are dreamed, not designed."],
        "wisdom_quotes": ["'The forest gives, but only to those who also give back.'"],
        "unique_facts": ["Cardamom grown here flavours tea across South Asia", "One of Bhutan's most biodiverse eastern districts"],
        "completion_reward": "Eastern Forest Sage",
        "required_knowledge": 75,
        "tour_narration": "Welcome to Mongar, where forests whisper ancient secrets!",
        "cultural_challenge": {"question": "What craft is Mongar especially famous for?", "options": ["Bronze casting", "Raw silk weaving", "Stone carving", "Pottery"], "answer": "Raw silk weaving"},
        "hidden_secrets": [
            {"name": "Wild Cardamom Pod", "xp": 35, "description": "A rare giant cardamom found deep in the forest"},
            {"name": "Silk Loom Token", "xp": 45, "description": "A carved wooden token from an heirloom loom"},
            {"name": "Monastery Bell Fragment", "xp": 55, "description": "A bronze shard from a bell said to ward off storms"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 9. LHUENTSE ───────────────────────────────────────────────────────────
    {
        "name": "Lhuentse",
        "icon": "👑",
        "region": "Eastern",
        "region_color": (180, 150, 20),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Lhuentse Dzongkhag",
        "population": "14,000",
        "main_ethnic_groups": "Kurtoep",
        "traditional_occupations": "Weaving (Kishuthara), rice and maize farming",
        "famous_personalities": "Gongzim Ugyen Dorji (grandfather of the first king)",
        "historical_significance": "Lhuentse is the ancestral homeland of Bhutan's royal Wangchuck family.",
        "religious_importance": "Lhuentse Dzong stands high above the Kuri Chhu river as a sacred royal site.",
        "sacred_sites": [
            {"name": "Lhuentse Dzong", "description": "Ancestral fortress of the Wangchuck dynasty", "history": "Built in the 17th century on a rocky promontory", "significance": "Royal ancestral seat; pilgrimage destination", "fun_fact": "Accessible only by a steep 30-minute climb", "legend": "Built where a dakini (sky dancer) left her footprint"},
            {"name": "Tangmachu Lhakhang", "description": "Remote monastery overlooking Lhuentse valley", "history": "Founded in the 12th century", "significance": "Contains rare ancient paintings", "fun_fact": "Pilgrims walk for two days to reach it", "legend": "A rainbow permanently hovers over the temple on clear days"},
            {"name": "Khoma Village", "description": "Village of master weavers", "history": "Weaving tradition dates back centuries", "significance": "Produces the finest Kishuthara silk in Bhutan", "fun_fact": "A single cloth can take months to complete", "legend": "The village was blessed by a silk-weaving goddess"},
            {"name": "Gangzur Village", "description": "Remote highland village", "history": "Settled by Tibetan migrants centuries ago", "significance": "Preserves ancient Kurtoep culture and dialect", "fun_fact": "Reachable only on foot or horseback", "legend": "Villagers say the mountains speak to those who listen in winter"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Lhuentse Tsechu", "months": "January", "highlights": "Rare winter cham dances and religious ceremonies"}],
            "arts": ["Kishuthara silk weaving", "Handmade paper", "Wood carving"],
            "cuisine": ["Wild honey", "Buckwheat bread", "Yak butter tea"],
            "etiquette_tips": ["Do not photograph the dzong without permission", "Greet elders by bowing your head"]
        },
        "local_stories": ["The Khoma weavers say each pattern in Kishuthara silk tells the story of a river, mountain, or flower."],
        "wisdom_quotes": ["'Royal blood flows from humble valleys, not golden palaces.'"],
        "unique_facts": ["Most remote dzongkhag in western Bhutan", "Kishuthara silk from Khoma is the most expensive textile in Bhutan"],
        "completion_reward": "Royal Ancestry Seeker",
        "required_knowledge": 78,
        "tour_narration": "Welcome to Lhuentse, the ancestral cradle of Bhutan's royal dynasty!",
        "cultural_challenge": {"question": "What is Lhuentse most famous for producing?", "options": ["Bronze statues", "Kishuthara silk", "Incense sticks", "Rice wine"], "answer": "Kishuthara silk"},
        "hidden_secrets": [
            {"name": "Royal Genealogy Scroll", "xp": 70, "description": "A scroll tracing the Wangchuck lineage"},
            {"name": "Dakini Footprint Stone", "xp": 60, "description": "A rock with an imprint said to belong to a sky dancer"},
            {"name": "Khoma Silk Thread", "xp": 45, "description": "A thread of the rarest Kishuthara pattern ever woven"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 10. TRASHI YANGTSE ────────────────────────────────────────────────────
    {
        "name": "Trashi Yangtse",
        "icon": "🦅",
        "region": "Eastern",
        "region_color": (80, 40, 140),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Trashi Yangtse Dzongkhag",
        "population": "17,000",
        "main_ethnic_groups": "Sharchop, Brokpa",
        "traditional_occupations": "Wood turning, weaving, yak herding",
        "famous_personalities": "Rigdzin Jigme Lingpa (18th-century saint)",
        "historical_significance": "Trashi Yangtse is home to Chorten Kora, modelled after Boudhanath in Nepal.",
        "religious_importance": "Chorten Kora is a major pilgrimage site drawing people from across eastern Bhutan and Arunachal Pradesh.",
        "sacred_sites": [
            {"name": "Chorten Kora", "description": "Large white stupa modelled on Boudhanath", "history": "Built in 1740 by Zhabdrung Ngagi Wangchuck", "significance": "Major pilgrimage stupa of eastern Bhutan", "fun_fact": "Annual circumambulation festival draws 10,000 pilgrims", "legend": "A young girl from Arunachal was entombed within to consecrate it"},
            {"name": "Trashi Yangtse Dzong", "description": "New dzong built in the 1990s", "history": "Completed 1997; replaced older structures", "significance": "Administrative seat of Trashi Yangtse district", "fun_fact": "Built entirely with traditional techniques", "legend": "Site chosen after a monk had a vision of a lotus flower"},
            {"name": "Rigsum Gonpa", "description": "Monastery on a ridge above the valley", "history": "Founded in the 17th century", "significance": "Contains three main shrines to Manjushri, Chenrezig, and Vajrapani", "fun_fact": "Offers panoramic views to Tibet on clear days", "legend": "Three saints meditated simultaneously here and left their handprints"},
            {"name": "Bumdeling Valley", "description": "Wide valley known for black-necked cranes", "history": "Recorded as a crane wintering site since the 18th century", "significance": "Second wintering ground for black-necked cranes in Bhutan", "fun_fact": "Cranes are seen as reincarnated lamas by locals", "legend": "A monk once transformed into a crane to protect the valley"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Chorten Kora Circumambulation", "months": "February/March", "highlights": "Thousands of pilgrims walking around the stupa for three days"}],
            "arts": ["Wood turning (bowls, cups)", "Cane basketry", "Lacquerware"],
            "cuisine": ["Churpi (hard yak cheese)", "Suja (butter tea)", "Corn on the cob"],
            "etiquette_tips": ["Walk clockwise around Chorten Kora", "Remove hats when entering the stupa compound"]
        },
        "local_stories": ["Wood turners say the bowls carved here hold blessings that cannot be washed away."],
        "wisdom_quotes": ["'The crane carries the prayers of the valley on its wings.'"],
        "unique_facts": ["Bhutan's second home for black-necked cranes", "Famous for turned wooden bowls used in royal households"],
        "completion_reward": "Far Eastern Pilgrim",
        "required_knowledge": 78,
        "tour_narration": "Welcome to Trashi Yangtse, where pilgrims circle and cranes winter in peace!",
        "cultural_challenge": {"question": "Which famous stupa in Nepal inspired Chorten Kora's design?", "options": ["Swayambhunath", "Pashupatinath", "Boudhanath", "Muktinath"], "answer": "Boudhanath"},
        "hidden_secrets": [
            {"name": "Consecrated Stupa Stone", "xp": 60, "description": "A stone from the original foundation of Chorten Kora"},
            {"name": "Crane Calling Stone", "xp": 55, "description": "A flat rock used by herders to call cranes to land"},
            {"name": "Turned Wooden Prayer Bowl", "xp": 40, "description": "A hand-turned bowl blessed by the local lama"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 11. SAMDRUP JONGKHAR ──────────────────────────────────────────────────
    {
        "name": "Samdrup Jongkhar",
        "icon": "🌿",
        "region": "Eastern",
        "region_color": (10, 140, 70),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Samdrup Jongkhar Dzongkhag",
        "population": "36,000",
        "main_ethnic_groups": "Sharchop, Lhotshampa",
        "traditional_occupations": "Trade, agriculture, timber industry",
        "famous_personalities": "U Ugyen (trader who helped open eastern trade routes)",
        "historical_significance": "Samdrup Jongkhar is Bhutan's eastern border town and a major trade gateway with India.",
        "religious_importance": "Zangtopelri Temple in Samdrup Jongkhar is a replica of Guru Rinpoche's paradise.",
        "sacred_sites": [
            {"name": "Zangtopelri Temple", "description": "Replica of Guru Rinpoche's Copper-Coloured Mountain paradise", "history": "Built in 1992", "significance": "Spiritual landmark at the eastern gateway", "fun_fact": "Three-storey structure with elaborate murals", "legend": "Visiting this temple is said to be equivalent to visiting Guru Rinpoche's paradise"},
            {"name": "Samdrup Jongkhar Dzong", "description": "Modern dzong serving as administrative hub", "history": "Built in the 20th century", "significance": "Gateway dzong between Bhutan and India", "fun_fact": "Marks the end of the east-west highway", "legend": "A protective deity guards the border crossing"},
            {"name": "Daifam Wildlife Sanctuary", "description": "Tropical forest sanctuary", "history": "Established in the 1990s", "significance": "Habitat for elephants, tigers, and gaur", "fun_fact": "Wild elephants occasionally enter the town", "legend": "A white elephant is said to guard the forest's heart"},
            {"name": "Gomtu Trade Market", "description": "Historic cross-border market", "history": "Active since the 18th century", "significance": "Cultural exchange point between Bhutan and Assam", "fun_fact": "Traders from both sides exchange goods every Thursday", "legend": "The first traders here sealed deals with a shared meal of rice and fish"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Samdrup Jongkhar Tsechu", "months": "November", "highlights": "Cham dances and border community gatherings"}],
            "arts": ["Cane and bamboo weaving", "Thangka painting", "Woodblock printing"],
            "cuisine": ["Dal bhat (Indian influence)", "Chilli pork", "Banana leaf rice"],
            "etiquette_tips": ["Border crossing requires permits — always carry ID", "Respect both Bhutanese and Indian cultural norms here"]
        },
        "local_stories": ["Traders say a white elephant once led a caravan safely through the jungle to this market."],
        "wisdom_quotes": ["'At every border, a new friendship waits to be made.'"],
        "unique_facts": ["The only eastern border crossing open to foreigners", "Elephants from Daifam sanctuary sometimes wander into town at night"],
        "completion_reward": "Eastern Gateway Trader",
        "required_knowledge": 68,
        "tour_narration": "Welcome to Samdrup Jongkhar, where Bhutan meets the wider world!",
        "cultural_challenge": {"question": "What does Zangtopelri Temple represent?", "options": ["A royal palace replica", "Guru Rinpoche's paradise", "The first dzong of Bhutan", "A meditation retreat"], "answer": "Guru Rinpoche's paradise"},
        "hidden_secrets": [
            {"name": "Elephant Footprint", "xp": 45, "description": "A giant footprint from a wild elephant found near the sanctuary"},
            {"name": "Old Trade Ledger Page", "xp": 35, "description": "A page from an 18th-century cross-border trade record"},
            {"name": "Jungle Orchid", "xp": 50, "description": "A rare orchid found only in the Daifam forest floor"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 12. PEMAGATSHEL ───────────────────────────────────────────────────────
    {
        "name": "Pemagatshel",
        "icon": "🌺",
        "region": "Eastern",
        "region_color": (200, 50, 100),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Pemagatshel Dzongkhag",
        "population": "23,000",
        "main_ethnic_groups": "Sharchop",
        "traditional_occupations": "Cardamom and ginger farming, weaving",
        "famous_personalities": "Khenpo Yeshe Chhokey (revered monk teacher)",
        "historical_significance": "Pemagatshel is known for its remote location and strong traditional culture.",
        "religious_importance": "Yongla Monastery is a major spiritual centre for the eastern highlands.",
        "sacred_sites": [
            {"name": "Yongla Gonpa", "description": "Ancient monastery on a mountain ridge", "history": "Founded in the 8th century, attributed to Guru Rinpoche", "significance": "Major pilgrimage site in eastern Bhutan", "fun_fact": "Monks perform fire pujas every full moon", "legend": "Guru Rinpoche turned a demon into a stone guardian here"},
            {"name": "Pemagatshel Dzong", "description": "Small traditional dzong", "history": "Built in the early 20th century", "significance": "Administrative and religious hub", "fun_fact": "Only accessible via a winding mountain road", "legend": "A rainbow appeared when the first stone was laid"},
            {"name": "Khar Monastery", "description": "Remote hermitage in the forest", "history": "Founded by a wandering lama in the 14th century", "significance": "Site of intensive meditation retreats", "fun_fact": "Monks here observe three-year silent retreats", "legend": "Those who complete a retreat here gain the ability to read minds"},
            {"name": "Chaling Village", "description": "Remote village preserving ancient customs", "history": "Settled over 500 years ago", "significance": "Maintains distinct Sharchop cultural practices", "fun_fact": "Every household owns a handloom", "legend": "Ancestors of the village were blessed by a passing saint who gave each family a different weaving pattern"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Pemagatshel Tsechu", "months": "October", "highlights": "Traditional dances in a remote highland setting"}],
            "arts": ["Sharchop weaving", "Cardamom wreath making", "Bamboo crafts"],
            "cuisine": ["Ginger tea", "Cardamom rice", "Fermented bamboo shoot curry"],
            "etiquette_tips": ["Always accept tea offered by hosts", "Do not refuse food at festivals"]
        },
        "local_stories": ["Weavers say the pattern of rain on a banana leaf inspired the finest Sharchop designs."],
        "wisdom_quotes": ["'The most remote places hold the most unbroken wisdom.'"],
        "unique_facts": ["One of the least visited dzongkhags in Bhutan", "Produces the most cardamom per household in eastern Bhutan"],
        "completion_reward": "Hidden Eastern Hermit",
        "required_knowledge": 80,
        "tour_narration": "Welcome to Pemagatshel, the hidden jewel of the eastern highlands!",
        "cultural_challenge": {"question": "What spice is Pemagatshel especially known for growing?", "options": ["Turmeric", "Cinnamon", "Cardamom", "Saffron"], "answer": "Cardamom"},
        "hidden_secrets": [
            {"name": "Rare Cardamom Seed Pouch", "xp": 40, "description": "A pouch of heirloom cardamom seeds from a 200-year-old plant"},
            {"name": "Meditator's Prayer Bead", "xp": 55, "description": "A single bead from a monk's rosary left after a 3-year retreat"},
            {"name": "Woven Sacred Cloth", "xp": 60, "description": "A cloth woven with prayers instead of a visible pattern"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 13. CHUKHA ────────────────────────────────────────────────────────────
    {
        "name": "Chukha",
        "icon": "⚡",
        "region": "Western",
        "region_color": (30, 60, 180),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Chukha Dzongkhag",
        "population": "74,000",
        "main_ethnic_groups": "Ngalop, Lhotshampa",
        "traditional_occupations": "Hydropower, trade, farming",
        "famous_personalities": "Engineers who built the Chukha Hydropower Project",
        "historical_significance": "Chukha hosts the Chukha Hydropower Dam, which powers much of Bhutan's electricity exports.",
        "religious_importance": "Rinchending Goenpa overlooks the Wang Chhu river gorge.",
        "sacred_sites": [
            {"name": "Chukha Dzong", "description": "Fortress overlooking the Wang Chhu gorge", "history": "Built in the 17th century", "significance": "Guardian dzong of the western trade route", "fun_fact": "Perched above a 300 m gorge", "legend": "A serpent spirit guards the river below"},
            {"name": "Rinchending Goenpa", "description": "Hilltop monastery above the dam", "history": "Founded in the 16th century", "significance": "Offers blessings for travellers entering Bhutan", "fun_fact": "First monastery seen when entering Bhutan from India", "legend": "A saint built it after a dream of a white snake"},
            {"name": "Chukha Hydropower Dam", "description": "Bhutan's first large hydropower project", "history": "Completed in 1988", "significance": "Symbol of Bhutan's development and energy exports", "fun_fact": "Exports electricity worth billions to India", "legend": "Workers say a water dragon blessed the dam's construction"},
            {"name": "Phuntsholing Market", "description": "Bustling border market town", "history": "Grew as a trade hub in the 19th century", "significance": "Bhutan's largest commercial centre and border crossing", "fun_fact": "Open to Indian nationals without a visa", "legend": "An Indian merchant's generosity is said to have founded the first stall here"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Chukha Tsechu", "months": "August/September", "highlights": "River blessing ceremonies and traditional dances"}],
            "arts": ["Thangka painting", "Mandala making", "Stone carving"],
            "cuisine": ["Phuntsholing street food", "Dal Bhat", "Momos with Indian spices"],
            "etiquette_tips": ["Carry your visitor permit when near the border", "Respect both Bhutanese and Indian traders"]
        },
        "local_stories": ["Engineers say the dam hums with a sound that resembles the ancient chant of the local deity."],
        "wisdom_quotes": ["'Water that flows becomes power; power that serves becomes blessing.'"],
        "unique_facts": ["Exports more electricity per capita than almost any country", "Phuntsholing is Bhutan's most cosmopolitan border town"],
        "completion_reward": "Western Frontier Engineer",
        "required_knowledge": 65,
        "tour_narration": "Welcome to Chukha, where Bhutan harnesses rivers to power its future!",
        "cultural_challenge": {"question": "What major resource does Chukha export to India?", "options": ["Coal", "Timber", "Hydroelectricity", "Cardamom"], "answer": "Hydroelectricity"},
        "hidden_secrets": [
            {"name": "River Dragon Scale", "xp": 45, "description": "A shimmering stone said to be from the river dragon"},
            {"name": "First Dam Blueprint", "xp": 50, "description": "A page from the original Chukha dam engineering plan"},
            {"name": "Border Merchant's Ledger", "xp": 35, "description": "A 100-year-old trade ledger from Phuntsholing's first market"}
        ],
        "terrain_type": TerrainType.RIVER_CROSSING.name
    },
    # ── 14. HAA ───────────────────────────────────────────────────────────────
    {
        "name": "Haa",
        "icon": "❄️",
        "region": "Western",
        "region_color": (100, 180, 220),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Haa Dzongkhag",
        "population": "12,000",
        "main_ethnic_groups": "Haap (Ngalop)",
        "traditional_occupations": "Cattle herding, potato and barley farming",
        "famous_personalities": "Kila Nunnery founder Ani Choying",
        "historical_significance": "Haa is one of Bhutan's most isolated and least-visited valleys, long closed to tourists.",
        "religious_importance": "Lhakhang Karpo (White Temple) and Lhakhang Nagpo (Black Temple) are twin sacred sites.",
        "sacred_sites": [
            {"name": "Lhakhang Karpo", "description": "White Temple associated with peace", "history": "Built in the 7th century by Songtsen Gampo", "significance": "One of the oldest temples in Bhutan", "fun_fact": "Always has white prayer flags", "legend": "Built to mark where peace descended from the sky"},
            {"name": "Lhakhang Nagpo", "description": "Black Temple associated with fierce protective deities", "history": "Built alongside Lhakhang Karpo in the 7th century", "significance": "Houses wrathful protective deities", "fun_fact": "Black prayer flags surround the temple", "legend": "A demon was tamed and became the temple's guardian"},
            {"name": "Kila Nunnery", "description": "Remote nunnery high in the mountains", "history": "Founded in the 9th century", "significance": "One of the oldest nunneries in Bhutan", "fun_fact": "Accessible only by a steep three-hour hike", "legend": "A female saint meditated here for 20 years without food"},
            {"name": "Haa Summer Festival Grounds", "description": "Open ground for the annual nomad festival", "history": "Festival tradition dates back centuries", "significance": "Celebrates Haap nomadic culture and identity", "fun_fact": "Features yak racing and nomad games", "legend": "The first festival was held to welcome the valley's protective deity"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Haa Summer Festival", "months": "July", "highlights": "Yak racing, archery, and traditional Haap dances"}],
            "arts": ["Yak-hair weaving", "Potato sack embroidery", "Felt making"],
            "cuisine": ["Potato dishes (boiled, fried, mashed)", "Yak butter tea", "Buckwheat soup"],
            "etiquette_tips": ["Ask before photographing nomadic families", "Bring warm clothes — even summers are cold"],
        },
        "local_stories": ["Haap people say the valley was sealed by the gods and only opened when the right king arrived."],
        "wisdom_quotes": ["'The coldest valleys produce the warmest hospitality.'"],
        "unique_facts": ["Only opened to tourists in 2002", "Has more prayer flags per person than any other district"],
        "completion_reward": "Secluded Valley Explorer",
        "required_knowledge": 72,
        "tour_narration": "Welcome to Haa, the mysterious valley that long hid from the world!",
        "cultural_challenge": {"question": "What are the twin temples of Haa called?", "options": ["Red & Blue", "Old & New", "White & Black", "Sun & Moon"], "answer": "White & Black"},
        "hidden_secrets": [
            {"name": "Yak Hair Talisman", "xp": 45, "description": "A braided charm made from sacred yak hair"},
            {"name": "Ancient White Prayer Flag", "xp": 40, "description": "A tattered flag from Lhakhang Karpo said to grant peace"},
            {"name": "Nomad Star Map", "xp": 55, "description": "A cloth with star positions used by Haap herders for navigation"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 15. GASA ──────────────────────────────────────────────────────────────
    {
        "name": "Gasa",
        "icon": "♨️",
        "region": "Northern",
        "region_color": (160, 60, 160),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Gasa Dzongkhag",
        "population": "3,500",
        "main_ethnic_groups": "Laya, Lhop",
        "traditional_occupations": "Yak herding, trekking guide services, cordyceps collection",
        "famous_personalities": "Ashi Dorji Wangmo Wangchuck (patron of Layap people)",
        "historical_significance": "Gasa is Bhutan's northernmost district, bordering Tibet, and one of the least populous.",
        "religious_importance": "Gasa Dzong is a 17th-century fortress guarding the route to Tibet.",
        "sacred_sites": [
            {"name": "Gasa Dzong", "description": "Remote fortress bordering Tibet", "history": "Built in the 17th century by Zhabdrung", "significance": "Guards the northern frontier of Bhutan", "fun_fact": "Surrounded by snow peaks above 5,000 m", "legend": "The dzong glows at night according to local herders"},
            {"name": "Gasa Hot Springs", "description": "Natural hot springs at the foot of the dzong", "history": "Used for centuries by herders and pilgrims", "significance": "Believed to have curative properties", "fun_fact": "Temperature stays at 40°C year-round", "legend": "A snake goddess released the hot water to heal a dying lama"},
            {"name": "Laya Village", "description": "Highest inhabited village in Bhutan", "history": "Settled by Tibetan migrants over 1,000 years ago", "significance": "Preserves a unique language and bamboo-hat culture", "fun_fact": "Women wear distinctive cone-shaped bamboo hats", "legend": "The hats were designed after the shape of a divine crown seen in a vision"},
            {"name": "Snowman Trek Route", "description": "One of the world's most challenging treks", "history": "Opened to trekkers in the 1980s", "significance": "Passes through Gasa and connects 11 remote villages", "fun_fact": "Fewer people complete it than climb Everest each year", "legend": "The first trekker to complete it was guided by a snow leopard"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Gasa Tsechu", "months": "March", "highlights": "Remote festival with traditional Layap dances"}],
            "arts": ["Yak-hair tent weaving", "Bamboo hat making", "Felted wool crafts"],
            "cuisine": ["Tsampa (roasted barley flour)", "Yak meat", "Butter tea with salt"],
            "etiquette_tips": ["Always bring gifts when visiting Layap homes", "Never take cordyceps without the community's permission"]
        },
        "local_stories": ["Layap herders say the yaks follow invisible paths laid by mountain deities."],
        "wisdom_quotes": ["'At the roof of the world, every breath is a blessing.'"],
        "unique_facts": ["Sparsest population of any dzongkhag in Bhutan", "Cordyceps fungus collected here is among the world's most valuable"],
        "completion_reward": "Snowman Trail Pioneer",
        "required_knowledge": 82,
        "tour_narration": "Welcome to Gasa, the rooftop district where sky meets earth!",
        "cultural_challenge": {"question": "What do Laya women wear as a distinctive cultural symbol?", "options": ["Silver nose rings", "Cone-shaped bamboo hats", "Red silk scarves", "Feathered headbands"], "answer": "Cone-shaped bamboo hats"},
        "hidden_secrets": [
            {"name": "Cordyceps Fungus Sample", "xp": 70, "description": "A rare specimen of the golden cordyceps mushroom"},
            {"name": "Snow Leopard Track", "xp": 65, "description": "A plaster cast of a snow leopard's paw print"},
            {"name": "Hot Spring Healing Stone", "xp": 50, "description": "A river stone soaked in the hot springs for 100 years"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 16. SARPANG ───────────────────────────────────────────────────────────
    {
        "name": "Sarpang",
        "icon": "🦋",
        "region": "Southern Central",
        "region_color": (40, 160, 80),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Sarpang Dzongkhag",
        "population": "40,000",
        "main_ethnic_groups": "Lhotshampa, Ngalop",
        "traditional_occupations": "Timber, farming, beekeeping",
        "famous_personalities": "Dasho Kinley Dorji (conservationist)",
        "historical_significance": "Sarpang is an important southern district with significant biodiversity in its subtropical forests.",
        "religious_importance": "Gelephu has growing importance as a spiritual and economic hub in southern Bhutan.",
        "sacred_sites": [
            {"name": "Sarpang Dzong", "description": "Southern district dzong", "history": "Modern dzong built in the 20th century", "significance": "Administrative seat of the district", "fun_fact": "Surrounded by subtropical jungle", "legend": "Built where a hermit once saw a naga (serpent deity) emerge from the ground"},
            {"name": "Gelephu Mindfulness City Site", "description": "Planned holistic urban project", "history": "Announced by King Jigme Khesar Namgyel Wangchuck in 2023", "significance": "A model for sustainable development globally", "fun_fact": "Designed with Buddhist philosophy at its core", "legend": "The site was chosen after the king received guidance during meditation"},
            {"name": "Royal Manas National Park", "description": "Tropical and subtropical forest reserve", "history": "Established in 1966", "significance": "UNESCO World Heritage Site; habitat for tigers and elephants", "fun_fact": "Shares a border with India's Manas Tiger Reserve", "legend": "A guardian tiger is said to protect the forest's sacred centre"},
            {"name": "Tingtibi Village", "description": "Village famous for weaving and honey", "history": "Settled by Ngalop families in the 17th century", "significance": "Preserves rare southern weaving patterns", "fun_fact": "Produces multiflora honey from 200 species of flowers", "legend": "Bees here are said to collect pollen blessed by the forest deity"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Sarpang Tsechu", "months": "February", "highlights": "Subtropical monsoon festival with forest dance rituals"}],
            "arts": ["Lhotshampa weaving", "Beekeeping and honey craft", "Bamboo basketry"],
            "cuisine": ["Tropical fruit curries", "Fish from the Manas River", "Honey cake"],
            "etiquette_tips": ["Respect wildlife corridors near the national park", "Never take forest products without permission"]
        },
        "local_stories": ["Honey collectors say the bees dance a different pattern in years when the harvest will be large."],
        "wisdom_quotes": ["'The forest asks nothing, but gives everything.'"],
        "unique_facts": ["Home to the planned Gelephu Mindfulness City", "Shares Manas National Park with India — a joint UNESCO site"],
        "completion_reward": "Southern Forest Guardian",
        "required_knowledge": 68,
        "tour_narration": "Welcome to Sarpang, where Bhutan's future and ancient forest meet!",
        "cultural_challenge": {"question": "What major international designation does Manas National Park hold?", "options": ["Ramsar Wetland", "UNESCO World Heritage Site", "Biosphere Reserve", "IUCN Category I"], "answer": "UNESCO World Heritage Site"},
        "hidden_secrets": [
            {"name": "Wild Tiger Pugmark", "xp": 65, "description": "A plaster cast of a tiger's paw from Manas forest"},
            {"name": "Rare Orchid Specimen", "xp": 50, "description": "A dried orchid from a species found only in Sarpang"},
            {"name": "Sacred Honey Comb", "xp": 45, "description": "A comb from bees that nest in a temple wall"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
    # ── 17. TSIRANG ───────────────────────────────────────────────────────────
    {
        "name": "Tsirang",
        "icon": "🌾",
        "region": "Southern",
        "region_color": (200, 160, 20),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Tsirang Dzongkhag",
        "population": "18,000",
        "main_ethnic_groups": "Lhotshampa, Ngalop",
        "traditional_occupations": "Orange farming, mandarin cultivation, weaving",
        "famous_personalities": "Pema Dhendup (pioneering citrus farmer)",
        "historical_significance": "Tsirang is known as Bhutan's citrus heartland, producing a third of the country's oranges.",
        "religious_importance": "Tsirang has small but significant lhakhangs serving the mixed religious communities of the south.",
        "sacred_sites": [
            {"name": "Damphu Dzong", "description": "Central dzong of Tsirang district", "history": "Built in the 20th century", "significance": "Administrative and cultural seat", "fun_fact": "Surrounded by orange groves", "legend": "Built on a site where a monk planted a citrus tree that bore fruit overnight"},
            {"name": "Tsirangtoe Monastery", "description": "Monastery above the citrus valleys", "history": "Founded in the 18th century", "significance": "Local pilgrimage site and community centre", "fun_fact": "Monks press fresh orange juice at the winter harvest", "legend": "A protective deity transformed into an orange tree to shield the monastery from invaders"},
            {"name": "Kikorthang Market", "description": "Historic trade market", "history": "Active since the 18th century", "significance": "Connects farmers from Tsirang with buyers from the west", "fun_fact": "Held every Tuesday; famous for fresh citrus and spices", "legend": "A talking parrot is said to have once directed traders to find this market"},
            {"name": "Patale Viewpoint", "description": "Mountain viewpoint overlooking the orange valleys", "history": "Used as a watchtower in ancient times", "significance": "Panoramic view of Tsirang's terraced orchards", "fun_fact": "On a clear day you can see both the plains of India and the Himalayan peaks", "legend": "A wandering saint left a staff here; it grew into a tree overnight"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Citrus Harvest Festival", "months": "November/December", "highlights": "Orange picking, juice pressing, and community feasts"}],
            "arts": ["Lhotshampa weaving", "Bamboo plaiting", "Citrus-leaf paper making"],
            "cuisine": ["Fresh mandarin oranges", "Citrus pickle", "Orange blossom tea", "Corn bread"],
            "etiquette_tips": ["Accept offered oranges graciously — it is a symbol of welcome", "Help carry baskets during harvest season if asked"]
        },
        "local_stories": ["Farmers say you can tell the quality of the next harvest by the colour of the blossom in spring."],
        "wisdom_quotes": ["'Sweet fruit grows from sour soil and patient hands.'"],
        "unique_facts": ["Produces approximately 30% of Bhutan's oranges", "Mandarin oranges are Bhutan's largest agricultural export"],
        "completion_reward": "Citrus Valley Harvester",
        "required_knowledge": 62,
        "tour_narration": "Welcome to Tsirang, Bhutan's sweetest valley of oranges and community spirit!",
        "cultural_challenge": {"question": "What is Tsirang's most important agricultural product?", "options": ["Rice", "Apples", "Oranges", "Cardamom"], "answer": "Oranges"},
        "hidden_secrets": [
            {"name": "Golden Orange Seed", "xp": 35, "description": "A seed from a 200-year-old mandarin tree in a monastery courtyard"},
            {"name": "Citrus Blossom Garland", "xp": 30, "description": "A dried garland offered at the harvest festival"},
            {"name": "Ancient Trade Basket", "xp": 40, "description": "A hand-woven bamboo basket used for centuries at Kikorthang Market"}
        ],
        "terrain_type": TerrainType.VILLAGE_PATH.name
    },
    # ── 18. DAGANA ────────────────────────────────────────────────────────────
    {
        "name": "Dagana",
        "icon": "🌀",
        "region": "Southern Western",
        "region_color": (80, 40, 120),
        "difficulty": "Medium",
        "difficulty_icon": "⛰️",
        "full_name": "Dagana Dzongkhag",
        "population": "21,000",
        "main_ethnic_groups": "Ngalop, Lhotshampa",
        "traditional_occupations": "Weaving, farming, stone quarrying",
        "famous_personalities": "Lam Neten (wandering healer saint of Dagana)",
        "historical_significance": "Dagana was historically important as a southern administrative centre with its own penlop (governor).",
        "religious_importance": "Dagana Dzong sits on a cliff above the Daga Chhu river and is a significant pilgrimage site.",
        "sacred_sites": [
            {"name": "Dagana Dzong", "description": "Remote cliff-top fortress", "history": "Built in the 17th century", "significance": "Was governed by a powerful penlop (governor)", "fun_fact": "Accessible only via a long mountain trek", "legend": "The dzong was built where a divine warrior rested on his way to defeat enemies in the south"},
            {"name": "Lawa Monastery", "description": "Hidden forest monastery", "history": "Founded in the 14th century", "significance": "Centre of Nyingma practice in Dagana", "fun_fact": "Monks here weave their own robes from nettle fibre", "legend": "A monk once fed a hungry tiger and it became the monastery's guardian"},
            {"name": "Khipisa Viewpoint", "description": "Mountain ridge with panoramic views", "history": "Used as a signal post in ancient times", "significance": "Commands views of both Bhutan and the Indian plains", "fun_fact": "You can see three provinces of India from this ridge", "legend": "A princess once watched for her returning husband from this very ridge for years"},
            {"name": "Jigme Singye Wangchuck National Park", "description": "Large central Bhutan protected area", "history": "Established in 2008", "significance": "Connects eastern and western Bhutan's forest corridors", "fun_fact": "Named after the fourth king of Bhutan", "legend": "A herd of takin emerging from the forest was seen as the park's founding blessing"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Dagana Tsechu", "months": "December", "highlights": "Small community tsechu with ancient mask dances"}],
            "arts": ["Nettle fibre weaving", "Stone carving", "Traditional thangka restoration"],
            "cuisine": ["Wild mushroom stew", "Millet beer", "Dried beef and spinach"],
            "etiquette_tips": ["Bring your own food and water on treks here", "Leave no trace in the national park"]
        },
        "local_stories": ["People say the stone walls of Dagana Dzong were built by giants, not men, because of how large the stones are."],
        "wisdom_quotes": ["'Every cliff hides a path for those with patient eyes.'"],
        "unique_facts": ["One of the most difficult dzongkhags to reach", "Dagana Dzong was never captured by any invader in its history"],
        "completion_reward": "Uncharted Cliff Walker",
        "required_knowledge": 72,
        "tour_narration": "Welcome to Dagana, the unconquered cliff-top kingdom of southern Bhutan!",
        "cultural_challenge": {"question": "What park named after Bhutan's fourth king lies partly within Dagana?", "options": ["Jigme Dorji National Park", "Royal Manas NP", "Jigme Singye Wangchuck NP", "Bumdeling WS"], "answer": "Jigme Singye Wangchuck NP"},
        "hidden_secrets": [
            {"name": "Fortress Foundation Stone", "xp": 55, "description": "A stone said to be from the original Dagana Dzong construction"},
            {"name": "Nettle Fibre Cloth", "xp": 45, "description": "A piece of cloth woven from wild nettle by a Lawa monk"},
            {"name": "Tiger Guardian Carving", "xp": 50, "description": "A carved wooden tiger from the Lawa Monastery entrance"}
        ],
        "terrain_type": TerrainType.MOUNTAIN_PASS.name
    },
    # ── 19. SAMTSE ────────────────────────────────────────────────────────────
    {
        "name": "Samtse",
        "icon": "🍵",
        "region": "Southern Western",
        "region_color": (20, 120, 50),
        "difficulty": "Easy",
        "difficulty_icon": "🌿",
        "full_name": "Samtse Dzongkhag",
        "population": "60,000",
        "main_ethnic_groups": "Lhotshampa, Ngalop",
        "traditional_occupations": "Tea cultivation, cardamom farming, lime quarrying",
        "famous_personalities": "Dasho Nado Rinchen (pioneer of southern education)",
        "historical_significance": "Samtse is Bhutan's southernmost district and one of its most diverse, bordering both West Bengal and Sikkim.",
        "religious_importance": "Several Hindu and Buddhist temples coexist in Samtse, reflecting its diverse southern population.",
        "sacred_sites": [
            {"name": "Samtse Dzong", "description": "Southern administrative fortress", "history": "Built in the 19th century", "significance": "Gateway dzong of southwestern Bhutan", "fun_fact": "Has the largest tea garden in Bhutan on its slopes", "legend": "A merchant offered the first harvest of tea to the dzong to receive a trading licence"},
            {"name": "Dorokha Village", "description": "Remote village near Sikkim border", "history": "Settled by early Ngalop farmers", "significance": "Maintains distinct weaving and festival traditions", "fun_fact": "Famous for a unique style of bamboo hat", "legend": "Villagers say their ancestors were blessed by a river deity when they first arrived here"},
            {"name": "Chargharey Lhakhang", "description": "Small but ancient temple", "history": "Founded in the 16th century", "significance": "Annual festival draws pilgrims from the border region", "fun_fact": "Uses natural forest pigments for all its murals", "legend": "A painter worked for 40 years without ever making a mistake"},
            {"name": "Samtse Tea Estate", "description": "Bhutan's main tea cultivation area", "history": "Tea farming introduced in the 19th century", "significance": "Produces organic tea exported under the Bhutan brand", "fun_fact": "Bhutan was one of the last countries to adopt tea farming", "legend": "A wandering monk from Darjeeling left tea seeds as a gift to a village elder"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Samtse Tsechu", "months": "October", "highlights": "Multi-ethnic festival blending Buddhist and Hindu traditions"}],
            "arts": ["Tea basket weaving", "Lhotshampa embroidery", "Lime carving (decorative)"],
            "cuisine": ["Bhutanese tea", "Cardamom milk tea", "Banana flower curry", "Rice with lime pickle"],
            "etiquette_tips": ["At Hindu temples, remove shoes and wash hands before entering", "Accept a cup of tea before beginning any conversation — it is custom"]
        },
        "local_stories": ["Tea pickers say the best tea is found on the bushes closest to where lightning struck the year before."],
        "wisdom_quotes": ["'A shared cup of tea dissolves the borders between people.'"],
        "unique_facts": ["Only district where Buddhist and Hindu festivals are officially celebrated together", "Produces Bhutan's only commercially exported tea"],
        "completion_reward": "Southern Tea Trail Walker",
        "required_knowledge": 63,
        "tour_narration": "Welcome to Samtse, where cultures and flavours blend at Bhutan's southern edge!",
        "cultural_challenge": {"question": "What beverage crop is Samtse famous for cultivating?", "options": ["Coffee", "Tea", "Cocoa", "Barley"], "answer": "Tea"},
        "hidden_secrets": [
            {"name": "First Tea Leaf Packet", "xp": 35, "description": "A sealed packet of leaves from the oldest tea bush in Bhutan"},
            {"name": "Wandering Monk's Tea Seed", "xp": 40, "description": "A seed from the legendary Darjeeling monk's original gift"},
            {"name": "Sacred Lime Stone", "xp": 30, "description": "A carved lime stone used in a border ceremony for 200 years"}
        ],
        "terrain_type": TerrainType.VILLAGE_PATH.name
    },
    # ── 20. ZHEMGANG ──────────────────────────────────────────────────────────
    {
        "name": "Zhemgang",
        "icon": "🦜",
        "region": "Central Southern",
        "region_color": (40, 120, 40),
        "difficulty": "Hard",
        "difficulty_icon": "🔥",
        "full_name": "Zhemgang Dzongkhag",
        "population": "16,000",
        "main_ethnic_groups": "Kheng, Brokpa",
        "traditional_occupations": "Weaving, yak herding, bamboo craft",
        "famous_personalities": "Dorji Wangchuk (environmental activist)",
        "historical_significance": "Zhemgang is one of Bhutan's most remote districts, preserving the ancient Kheng language and culture.",
        "religious_importance": "Zhemgang Dzong sits at the confluence of two rivers and is a regional pilgrimage centre.",
        "sacred_sites": [
            {"name": "Zhemgang Dzong", "description": "Remote river-confluence fortress", "history": "Built in the 17th century", "significance": "Guards the route to central Bhutan from the south", "fun_fact": "Only accessible via a two-day drive from Bumthang", "legend": "A saint dropped his rosary and where each bead landed became a sacred site — this was the first bead"},
            {"name": "Ngang Lhakhang", "description": "Swan Temple of Zhemgang", "history": "Founded in the 15th century", "significance": "Kheng community's most sacred temple", "fun_fact": "A pair of swans has nested on the temple lake for 300 years", "legend": "The swans are reincarnations of the temple's founding monks"},
            {"name": "Phumzur Village", "description": "Traditional Kheng village", "history": "Settled over 700 years ago", "significance": "Preserves the oldest surviving Kheng dialect", "fun_fact": "The village has no road; reached only by foot", "legend": "Villagers say time passes differently here — a week inside feels like a day to those outside"},
            {"name": "Kheng Heritage Trail", "description": "Forest trail through ancient Kheng settlements", "history": "Used by traders for centuries", "significance": "Connects 12 remote villages across the district", "fun_fact": "Wild orchids line the trail in spring", "legend": "Travellers who leave food on the trail's midpoint stone always arrive safely at their destination"}
        ],
        "cultural_practices": {
            "festivals": [{"name": "Zhemgang Tsechu", "months": "February", "highlights": "Rare Kheng cultural dances and bamboo pole ceremonies"}],
            "arts": ["Kheng bamboo weaving", "Bark cloth making", "Natural dye textile"],
            "cuisine": ["Bamboo shoot stew", "Wild fern salad", "Millet wine", "Dried river fish"],
            "etiquette_tips": ["Speak softly in the forest — the Kheng people believe trees hear human voices", "Never cut bamboo near a monastery without permission"]
        },
        "local_stories": ["The Kheng say a pair of swans at Ngang Lhakhang have not aged a single day in 300 years."],
        "wisdom_quotes": ["'The rarest things are not found in markets but in quiet forests.'"],
        "unique_facts": ["Home to the endangered Kheng language spoken by fewer than 10,000 people", "One of Bhutan's last districts without a paved approach road to all villages"],
        "completion_reward": "Ancient Kheng Culture Keeper",
        "required_knowledge": 80,
        "tour_narration": "Welcome to Zhemgang, where ancient Kheng wisdom still echoes through the bamboo forests!",
        "cultural_challenge": {"question": "What endangered language is preserved in Zhemgang?", "options": ["Tshangla", "Dzongkha", "Kheng", "Lhotsham"], "answer": "Kheng"},
        "hidden_secrets": [
            {"name": "Kheng Swan Feather", "xp": 65, "description": "A feather from the 300-year-old pair of swans at Ngang Lhakhang"},
            {"name": "Bark Cloth Fragment", "xp": 55, "description": "A piece of ancient bark cloth used in Kheng healing rituals"},
            {"name": "Forest Orchid Pressed Flower", "xp": 40, "description": "A pressed orchid from the heritage trail, said to grant safe passage"}
        ],
        "terrain_type": TerrainType.FOREST_PATH.name
    },
]

# Official places used as respectful points of interest for each listed district.
OFFICIAL_PLACE_NAMES = {
    "Thimphu": ["Tango Monastery", "Tashichho Dzong", "Buddha Point", "Changangkha Lhakhang", "Memorial Chorten"],
    "Paro": ["Kyichu Lhakhang", "Drukgyel Dzong", "Taktsang Monastery", "Ta Dzong", "Rinpung Dzong"],
    "Punakha": ["Khamsum Yulley Namgyel Chorten", "Punakha Dzong", "Chimi Lhakhang", "Nalanda Buddhist College"],
    "Bumthang": ["Jakar Dzong", "Kurjey Lhakhang", "Tamshing Lhakhang", "Jampa Lhakhang", "Membartsho"],
    "Wangdue Phodrang": ["Phobjikha Valley", "Wangdue Phodrang Dzong", "Gangtey Monastery", "Rinchen Gang Village"],
    "Trongsa": ["Trongsa Dzong", "Kuenga Rabten Palace", "Chendebji Chorten", "Ta Dzong (Power of Trongsa)"],
    "Trashigang": ["Trashigang Dzong", "Merak Sakteng", "Barstam Lhakhang"],
    "Mongar": ["Mongar Dzong", "Ngatsang Gonpa", "Zhongar Dzong Ruins"],
    "Lhuentse": ["Khoma Village", "Lhuentse Dzong", "Gangzur Village", "Tangmachu Lhakhang"],
    "Trashi Yangtse": ["Chorten Kora", "Rigsum Gonpa", "Trashiyangtse Dzong", "Bumdeling Valley"],
    "Samdrup Jongkhar": ["Daifam", "Samdrup Jongkhar Dzong", "Zangtho Pelri Lhakhang"],
    "Pemagatshel": ["Khar Monastery", "Yongla Gonpa", "Pema Gatsel Dzong"],
    "Chukha": ["Chukha Dzong", "Phuentsholing Market", "Rinchending Gonpa"],
    "Haa": ["Lhakhang Karpo", "Lhakhang Nagpo", "Haa Summer Festival Ground"],
    "Gasa": ["Laya Village", "Gasa Dzong", "Gasa Hotsprings"],
    "Sarpang": ["Sarpang Dzong", "Tali Dratshang", "Gelephu Mindfulness City"],
    "Tsirang": ["Damphu Dzong", "Kikorthang Market", "Tsirangtoe Monastery", "Patale Viewpoint"],
    "Dagana": ["Kipisa Viewpoint", "Dagana Dzong", "Sky Pillar Rock (Do Namkhai Kaw)", "Rock of Ancient Steps (Do Kelpai Genthey)"],
    "Samtse": ["Chargharey Lhakhang", "Samtse Dzong", "Samtse Tea Estate", "Dorokha Village"],
    "Zhemgang": ["Zhemgang Dzong", "Ngang Lhakhang", "Phumzur Village", "Kheng Heritage Trail"],
}


def _place_key(name):
    return "".join(character.lower() for character in name if character.isalnum())


def _apply_official_places():
    for district in bhutan_districts:
        unique_sites = []
        seen_places = set()
        for site in district.get("sacred_sites", []):
            place_key = _place_key(site["name"])
            if place_key not in seen_places:
                unique_sites.append(site)
                seen_places.add(place_key)
        district["sacred_sites"] = unique_sites


_apply_official_places()

ADDITIONAL_SITE_DETAILS = {
    "Tango Monastery": {
        "history": "Founded in the 13th century by Phajo Drugom Zhigpo and rebuilt in 1688 by Gyalse Tenzin Rabgye. Tango is associated with the Drukpa Kagyu school and the deity Hayagriva.",
        "significance": "A revered centre for Buddhist education, meditation, and spiritual practice, with temples, valuable statues, and Menlug-style murals.",
        "fun_fact": "Located about 14 km north of Thimphu and known for its mountain setting and traditional monastery architecture.",
    },
    "Buddha Point": {
        "description": "The Great Buddha Dordenma statue at Kuensel Phodrang in Thimphu.",
        "history": "Ancient prophecies foretold a large Buddha statue here. The project began in the 1990s, construction started in 2006, and consecration was completed in 2015.",
        "significance": "A major symbol of Buddhist faith, peace, and blessings in Bhutan.",
        "fun_fact": "The statue stands at Kuensel Phodrang above Thimphu and was initiated by Bhutan's Fourth King, Jigme Singye Wangchuck.",
    },
    "Changangkha Lhakhang": {
        "history": "Founded in the 13th century by Nyima, son of Phajo Drugom Zhigpo. The site was blessed by Guru Rinpoche and later renovated, including major work in 1998.",
        "significance": "One of Thimphu's oldest temples and an important Drukpa Kagyu spiritual site, especially associated with blessings for children.",
        "fun_fact": "The temple stands on a ridge above Thimphu and was used as a meditation place before the temple was built.",
    },
    "Memorial Chorten": {
        "history": "Built in 1974 in memory of Bhutan's Third King, Jigme Dorji Wangchuck, under the direction of Queen Ashi Phuntsho Choden Wangchuck.",
        "significance": "A landmark dedicated to world peace and prosperity, and a lasting symbol of the Third King's legacy.",
        "fun_fact": "It is one of Thimphu's most visited religious landmarks and is open around the clock for prayer.",
    },
    "Kyichu Lhakhang": {
        "history": "Built in the 7th century by Tibetan King Songtsen Gampo as one of the 108 temples established to promote Buddhism. Guru Padmasambhava visited it in the 8th century, and later Bhutanese rulers restored and expanded it.",
        "significance": "One of Bhutan's oldest and most sacred temples, preserving centuries of Buddhist devotion in Paro.",
        "fun_fact": "Two orange trees in the courtyard are traditionally believed to bear fruit throughout the year. A Guru Temple was added in 1971 by Queen Kesang Choden Wangchuck.",
    },
    "Drukgyel Dzong": {
        "history": "Built in 1649 by Zhabdrung Ngawang Namgyal after a victory over Tibetan forces. A fire damaged the fortress in 1951, leaving the historic ruins seen today.",
        "significance": "A national monument representing Bhutan's defensive history and religious heritage.",
        "fun_fact": "The ruined fortress commands views toward the mountains and was once used for both defense and religion.",
    },
    "Taktsang Monastery": {
        "history": "Built in 1692 around the cave where Guru Padmasambhava meditated in the 8th century. The monastery was restored after a serious fire in 1998.",
        "significance": "One of Bhutan's most sacred Buddhist sites and a major symbol of Bhutanese culture and spirituality.",
        "fun_fact": "Also called Tiger's Nest, it is perched high on a cliff in Paro and is reached by a mountain hike.",
    },
    "Rinpung Dzong": {
        "history": "Built by Zhabdrung Ngawang Namgyal in the 17th century and completed in 1646. Its name means 'Fortress on a Heap of Jewels.'",
        "significance": "A historic fortress-monastery that served defensive, religious, and administrative roles in Paro.",
        "fun_fact": "It is famous for traditional Bhutanese architecture and the annual Paro Tsechu festival.",
    },
    "Khamsum Yulley Namgyel Chorten": {
        "history": "A 30-metre, four-storey chorten built in 2004 by Ashi Tshering Yangdon Wangchuck to promote peace and harmony and protect Bhutan from negative forces.",
        "significance": "A sacred hilltop monument overlooking the Mo Chhu River and Punakha valley.",
        "fun_fact": "Visitors reach it by a short hike through the valley and surrounding farmland.",
    },
    "Punakha Dzong": {
        "history": "Built in 1637-38 by Zhabdrung Ngawang Namgyal at the meeting point of the Pho Chhu and Mo Chhu rivers. It remained Bhutan's government seat until 1955.",
        "significance": "A religious, administrative, and royal centre and one of the finest examples of Bhutanese architecture.",
        "fun_fact": "The dzong is known for its river confluence setting, sacred relics, and royal ceremonies.",
    },
    "Chimi Lhakhang": {
        "history": "Built in 1499 by Ngawang Choegyel and blessed by Drukpa Kunley, known as the Divine Madman.",
        "significance": "A famous fertility temple whose legends and blessings remain important to Bhutanese visitors.",
        "fun_fact": "The surrounding village is known for distinctive fertility symbols and stories connected with Drukpa Kunley's teachings.",
    },
    "Nalanda Buddhist College": {
        "history": "Named after Nalanda, the ancient Buddhist university founded around 427 CE by Emperor Kumaragupta I in Magadha, India. Nalanda was active for nearly a thousand years.",
        "significance": "A centre for advanced Buddhist learning, philosophy, arts, culture, and monastic education.",
        "fun_fact": "Its name connects Bhutanese Buddhist study with one of the ancient world's greatest centres of learning.",
    },
    "Jakar Dzong": {
        "history": "Founded in 1549 by Ngagi Wangchuk, a Tibetan lama, and rebuilt and expanded over time. It became the seat of Bhutan's first King in 1646; the present structure dates from major work in 1667.",
        "significance": "A fortress-monastery representing Bumthang's traditional union of religious and administrative life.",
        "fun_fact": "Jakar comes from bjakhab, meaning 'white bird', and the dzong remains the Bumthang district administrative centre and home of the district monastic body.",
    },
    "Kurjey Lhakhang": {
        "history": "Kurjey means 'body imprint'. Guru Padmasambhava is believed to have meditated here, subdued the local deity Shelging Karpo, and left his body imprint. The complex includes temples built in 1652, 1900, and 1990.",
        "significance": "One of Bhutan's most sacred pilgrimage sites and an important part of Bumthang's Buddhist heritage.",
        "fun_fact": "The complex includes 108 chortens, murals, a Wheel of Life, and is associated with Bhutan's first three kings.",
    },
    "Tamshing Lhakhang": {
        "history": "Founded in 1501 by the Bhutanese saint Pema Lingpa and preserved as an important Nyingma Buddhist temple.",
        "significance": "A centre for teaching Pema Lingpa's tradition and for preserving medieval Bhutanese art, architecture, and religious heritage.",
        "fun_fact": "It is famous for original early-16th-century wall paintings and murals and is on Bhutan's tentative UNESCO list.",
    },
    "Jampa Lhakhang": {
        "history": "Built in 659 CE by Songtsen Gampo, the 33rd Tibetan King, as one of the temples associated with overcoming obstacles to the spread of Buddhism. Guru Rinpoche visited in the 8th century.",
        "significance": "One of Bhutan's oldest and most sacred temples, dedicated to Jowo Jampa, the future Buddha.",
        "fun_fact": "The temple stands at about 2,630 metres and has been expanded and renewed by generations of rulers and religious figures.",
    },
    "Wangdue Phodrang Dzong": {
        "history": "Built in 1638 by Zhabdrung Ngawang Namgyal on a strategic ridge near the meeting point of the Dangchhu and Punatsangchhu rivers. It was expanded in 1683, damaged by fire in 1837 and an earthquake in 1897, destroyed by fire in 2012, and rebuilt in 2022.",
        "significance": "A fortress, administrative centre, and religious landmark symbolizing Bhutanese history, culture, and unity.",
        "fun_fact": "The dzong's ridge position made it an important defensive site overlooking two river valleys.",
    },
    "Gangtey Monastery": {
        "history": "Founded in 1613 by Gyalse Pema Thinley, grandson of Pema Lingpa, to fulfil a prophecy associated with the great treasure revealer.",
        "significance": "An important Nyingmapa Buddhist monastery and spiritual centre of Phobjikha Valley.",
        "fun_fact": "The monastery is closely associated with the endangered black-necked cranes that visit the valley each year.",
    },
    "Phobjikha Valley": {
        "history": "A glacial valley known for Gangtey Monastery and the annual arrival of endangered black-necked cranes. Conservation and low-impact tourism protect its natural and cultural heritage.",
        "significance": "A major ecological, religious, and cultural landscape in central Bhutan.",
        "fun_fact": "The valley's cranes are a celebrated seasonal sign and an important focus of local conservation.",
    },
    "Rinchengang Village": {
        "history": "One of Bhutan's oldest continuously inhabited villages, established in the early 17th century by skilled stonemasons from Cooch Bihar brought by Zhabdrung Ngawang Namgyal.",
        "significance": "A living heritage village preserving traditional mud-and-stone houses, clustered settlement patterns, and craft traditions.",
        "fun_fact": "The village was historically an important trading centre between Tibet and India and is now being developed as an Innovative Model Village.",
    },
    "Trongsa Dzong": {
        "history": "It began as a small temple founded in 1543 by Ngagi Wangchuk and was expanded in 1644 by Zhabdrung Ngawang Namgyal and Chhogyal Mingyur Tenpa.",
        "significance": "One of Bhutan's largest dzongs, serving as a fortress, administrative centre, and religious landmark on a ridge above the Mangde Chhu River.",
        "fun_fact": "Future Wangchuck kings traditionally served as Trongsa Penlop before becoming king.",
    },
    "Kuenga Rabten Palace": {
        "history": "Built in the early 20th century as the winter residence of Bhutan's Second King, Jigme Wangchuck.",
        "significance": "A preserved example of royal Bhutanese architecture and a museum of the country's royal history.",
        "fun_fact": "The three floors held storage and a garrison below, with royal rooms, an audience hall, guestrooms, and Sangye Lhakhang above.",
    },
    "Chendebji Chorten": {
        "history": "Built in the 18th century by Lama Shida, a Tibetan lama, and inspired by Boudhanath Stupa in Kathmandu.",
        "significance": "A sacred place for prayer, meditation, and pilgrimage, traditionally built to subdue an evil spirit.",
        "fun_fact": "The stupa remains an important Buddhist monument on the route through Trongsa.",
    },
    "Trashigang Dzong": {
        "history": "Built in 1659 by Chhogyal Minjur Tempa on a cliff overlooking the Drangme Chhu and Gamri Chhu rivers. It was expanded between 1680 and 1694 and restored in later years, including major work in 2009.",
        "significance": "The administrative headquarters and monastic centre of Trashigang, hosting the annual Trashigang Tshechu.",
        "fun_fact": "Its name means 'Fortress of the Auspicious Hill', and its traditional architecture includes white walls, red roofs, and golden details.",
    },
    "Merak Sakteng Wildlife Sanctuary": {
        "history": "Merak and Sakteng are highland villages of the Brokpa people, whose traditions are said to reach back to the 13th century. The area became open to tourism in 2009.",
        "significance": "A protected cultural and natural landscape preserving Brokpa language, dress, yak herding, and highland life.",
        "fun_fact": "The villages are associated with Ama Jomo and Lam Jarepa and lie within Sakteng Wildlife Sanctuary.",
    },
    "Bartsham Lhakhang": {
        "history": "The original temple dates to the 12th century. The present Bartsham Chador Lhakhang was founded by Lama Pema Wangchen in 1977 and completed in 1986.",
        "significance": "An important pilgrimage temple where visitors come for prayer and blessings.",
        "fun_fact": "It is known for a small replica of the Chador statue discovered from Yuetsho Lake.",
    },
    "Mongar Dzong": {
        "history": "Built in 1930 by Jigme Wangchuck, the Second King, to replace the older Zhongar Dzong.",
        "significance": "The administrative and religious centre of Mongar and the setting for the annual Mongar Tshechu.",
        "fun_fact": "It was built with wood, stone, and clay without nails, drawing design inspiration from Lamai Goenpa and royal architecture.",
    },
    "Khoma Village": {
        "history": "A historic Lhuentse village associated with Guru Rinpoche, sacred caves, and stories of Khandro Yeshey Tshogyal and Tashi Khedon.",
        "significance": "A living cultural heritage site famous for traditional clustered settlement and Kishu Thara textile weaving.",
        "fun_fact": "Local tradition says Guru Rinpoche hid sacred treasures in nearby caves, later discovered by Terton Ratna Lingpa.",
    },
    "Lhuentse Dzong": {
        "history": "Built in 1654 by Minjur Tempa under the guidance of Zhabdrung Ngawang Namgyal above the Kuri Chhu River. The site was first used by Ngagi Wangchuk in 1543.",
        "significance": "The ancestral home of Bhutan's Wangchuck royal family and the administrative and religious centre of Lhuentse.",
        "fun_fact": "The dzong contains sacred relics including a statue of Tshepamey and hosts the Tshempay Tshechu festival.",
    },
    "Chorten Kora": {
        "history": "Built in 1740 by Lama Ngawang Lodro in memory of Lam Jangchub Gyeltshen and to subdue a harmful demon. It was modeled after Boudhanath Stupa in Nepal and consecrated after twelve years of construction.",
        "significance": "A major pilgrimage site representing spiritual devotion, Bhutanese culture, and friendship with Tawang in India.",
        "fun_fact": "It hosts the Dakpa Kora and Drukpa Kora festivals, when pilgrims circumambulate the stupa.",
    },
    "Rigsum Gonpa": {
        "history": "Founded in the 18th century by Lama Tshering Gyamtsho, a disciple of the 9th Je Khenpo Shacha Rinchhen, in Bumdeling Gewog.",
        "significance": "A pilgrimage and Buddhist learning centre believed to protect Bhutan from external threats.",
        "fun_fact": "It houses a sacred Jowo Shakyamuni statue and a religious school for monks on a ridge above the valley.",
    },
    "Bumdeling Wildlife Sanctuary": {
        "history": "Planned in 1995 and established in 1998, the sanctuary covers about 1,520 square kilometres across northeastern Bhutan.",
        "significance": "An important conservation and cultural landscape containing alpine lakes, forests, wildlife, and communities.",
        "fun_fact": "It is an Important Bird Area and wintering ground for black-necked cranes, and is home to Ludlow's Bhutan swallowtail.",
    },
    "Zangtho Pelri Lhakhang": {
        "history": "Built in the early 1990s in Phuentsholing as a representation of Guru Rinpoche's celestial abode, following descriptions in Buddhist texts.",
        "significance": "A spiritual and cultural landmark combining traditional Bhutanese architecture with Buddhist symbolism.",
        "fun_fact": "The temple was built as a tribute to Dasho Aku Tongmi and attracts visitors for prayer, blessings, and reflection.",
    },
    "Samdrup Jongkhar Dzong": {
        "history": "Built in the late 20th century as Samdrup Jongkhar developed into an administrative centre and eastern gateway.",
        "significance": "An administrative and monastic centre housing district offices and supporting the region's religious life.",
        "fun_fact": "Samdrup Jongkhar is an important commercial and transport hub on Bhutan's border with India; its name means 'palace of the wish-fulfilling jewel'.",
    },
    "Daifam": {
        "history": "Daifam became known for dairy production in the 1950s and 1960s, producing milk, curd, cheese, and butter. Its name developed from 'Dairy Farm'.",
        "significance": "A southern Bhutanese agricultural area whose history reflects local farming and dairy development.",
        "fun_fact": "Government-backed agricultural initiatives continue to shape Daifam's development.",
    },
    "Yongla Gonpa": {
        "history": "Founded in 1736 by Kheydrup Jigme Kuendrel in a place shaped like a phurba ritual dagger. The monastery was reconstructed after the 2009 earthquake, with work completed in 2019.",
        "significance": "One of eastern Bhutan's oldest respected monasteries and a centre associated with Jigme Lingpa's teachings.",
        "fun_fact": "It is traditionally believed to guard Bhutan from the south, while Rigsum Gonpa guards it from the north.",
    },
    "Pema Gatsel Dzong": {
        "history": "Located at Denchi, Pema Gatshel Dzong is the administrative and monastic hub of the district, designed to replace older administrative structures.",
        "significance": "A modern dzong combining traditional Bhutanese woodwork and stone craftsmanship with district administration and monastic life.",
        "fun_fact": "Its design reflects the district's continuing development while retaining Bhutanese architectural traditions.",
    },
    "Chukha Dzong": {
        "history": "A historic fortress built in the 17th century on a hilltop above the Wang Chhu gorge.",
        "significance": "An important example of Bhutanese craftsmanship and a guardian of the western trade route.",
        "fun_fact": "The dzong's hilltop position gives it wide views across the Chukha landscape.",
    },
    "Phuentsholing Market": {
        "history": "The market grew with Phuentsholing as Bhutan's commercial gateway to Jaigaon, India, especially after the country opened more widely in the 1960s and developed tourism in the 1970s.",
        "significance": "A living cultural site where trade, local produce, textiles, handicrafts, and daily Bhutanese life meet.",
        "fun_fact": "The market sits near Bhutan Gate and the Amo Chhu Crocodile Breeding Center.",
    },
    "Rinchending Gonpa": {
        "history": "Also known as Kharbandi Monastery, it was established in 1967 by Ashi Phuntsho Choden, grandmother of Bhutan's Fourth King.",
        "significance": "A spiritual sanctuary for travellers entering Bhutan and an important landmark for local prayer and pilgrimage.",
        "fun_fact": "Its murals and statues include Shakyamuni Buddha, Guru Rinpoche, and Avalokiteshvara.",
    },
    "Haa Summer Festival Ground": {
        "history": "The Haa Summer Festival was established in 2012 to promote cultural tourism and celebrate the nomadic herding traditions of the Haa people.",
        "significance": "A living cultural gathering place for local food, yak herding, traditional customs, and religious practices.",
        "fun_fact": "Haa was once a restricted military border area and opened fully to tourism in 2002.",
    },
    "Lhakhang Karpo": {
        "history": "Founded in the 7th century during the reign of Tibetan King Songtsen Gampo. Legend says one of two sacred pigeons chose this site for the White Temple.",
        "significance": "One of the oldest sacred temples in Haa Valley, visited for prayer and blessings.",
        "fun_fact": "Its name means 'White Temple' and it is surrounded by farmland and traditional houses.",
    },
    "Lhakhang Nagpo": {
        "history": "Founded in 659 CE by King Songtsen Gampo as one of 108 temples built to help spread Buddhism and overcome obstacles to its teachings.",
        "significance": "A sacred place for prayer and meditation in Haa Valley.",
        "fun_fact": "The temple stands at about 3,366 metres near the Meri Puensum Mountains and contains traditional murals and sacred statues.",
    },
    "Gasa Hotsprings": {
        "history": "Gasa Tshachu are natural thermal springs associated with the 13th-century saint Drubthob Terkhungpa and with Zhabdrung Ngawang Namgyal. Flooding damaged the complex in 2021; it reopened after reconstruction in October 2023.",
        "significance": "A place of traditional healing, relaxation, pilgrimage, and tourism in Gasa Dzongkhag.",
        "fun_fact": "Visitors have used the warm waters for generations as part of local healing traditions.",
    },
    "Laya Village": {
        "history": "Laya is home to the indigenous Layap people, who have preserved a semi-nomadic lifestyle connected with nature and yak herding. It was once an important trading hub between Bhutan and Tibet.",
        "significance": "A highland cultural community preserving Layap language, traditions, and way of life.",
        "fun_fact": "The village hosts the Royal Highland Festival each October.",
    },
    "Sarpang Dzong": {
        "history": "Built in 1919 during the reign of the Second King, Jigme Wangchuck, to protect Bhutan's southern frontier.",
        "significance": "A religious and administrative centre where monks perform rituals and the district hosts Tshechu celebrations.",
        "fun_fact": "The dzong is set among the forests and mountains of southern Bhutan.",
    },
    "Gelephu Mindfulness City": {
        "history": "Gelephu has long been shaped by indigenous communities, agriculture, and trade. Mindfulness City was announced by King Jigme Khesar Namgyel Wangchuck on 17 December 2023 and received its Royal Charter on 13 February 2024.",
        "significance": "A planned sustainable city combining Bhutanese culture, spirituality, technology, green development, and Gross National Happiness.",
        "fun_fact": "The masterplan includes 11 mandala-inspired neighbourhoods, green spaces, walkways, cycling routes, and environmentally friendly buildings.",
    },
    "Tsirangtoe Monastery": {
        "history": "The monastery's roots reach back to the 8th century and local traditions associated with Guru Rinpoche, who is credited with bringing Buddhism to Bhutan.",
        "significance": "A local pilgrimage and community centre preserving religious traditions in Tsirang.",
        "fun_fact": "It stands above Tsirang's citrus valleys and remains connected with living local stories.",
    },
    "Dagana Dzong": {
        "history": "Built in 1651 under Zhabdrung Ngawang Namgyal by Dronyer Druk Namgyel and rebuilt in the early 19th century after severe damage.",
        "significance": "A historic fortress and religious centre representing Bhutanese sovereignty and southern defense.",
        "fun_fact": "The dzong sits above the Daga Chhu river and is reached through a remote mountain landscape.",
    },
    "Sky Pillar Rock (Do Namkhai Kaw)": {
        "history": "A sacred rock in Dagana believed to have flown from Bodh Gaya, India, and associated with Guru Rinpoche.",
        "significance": "A highly revered site believed to contain the Thousand Buddha Statues and connected with sacred footprints and ritual practice.",
        "fun_fact": "The rock is about 20 metres high and has a Dakini footprint and a sacred ritual bell.",
    },
    "Rock of Ancient Steps (Do Kelpai Genthey)": {
        "history": "One of three ancient stone megaliths linked by legend to the construction of Daga Trashiyangtse Dzong in 1651.",
        "significance": "A cultural landmark representing ancient wisdom and the spiritual beliefs surrounding Dagana Dzong.",
        "fun_fact": "Legend says the stones warned that the dzong would collapse if built higher than its present height.",
    },
    "Samtse Dzong": {
        "history": "Established in the 1970s as the administrative and cultural centre of Samtse, after the district headquarters developed in the mid-20th century.",
        "significance": "A centre for government, religion, festivals, and community life in southwestern Bhutan.",
        "fun_fact": "Samtse's foothills are known for tea, cardamom, and mandarin cultivation.",
    },
    "Samtse Tea Estate": {
        "history": "Samtse's fertile foothills support tea gardens, large cardamom, and mandarin orchards that sustain local farmers and trade.",
        "significance": "A living agricultural heritage site showcasing southern Bhutanese farming traditions.",
        "fun_fact": "Visitors can learn about tea picking, cardamom drying, and seasonal farm work.",
    },
}

for district in bhutan_districts:
    for site in district.get("sacred_sites", []):
        details = ADDITIONAL_SITE_DETAILS.get(site["name"])
        if details:
            site.update(details)

SAVE_FILE = "game_save.json"

def clean_sprite_frame(frame):
    background = frame.get_at((0, 0))[:3]
    width, height = frame.get_size()
    foreground = set()

    for y in range(height):
        for x in range(width):
            color = frame.get_at((x, y))[:3]
            if max(abs(color[index] - background[index]) for index in range(3)) > 8:
                foreground.add((x, y))

    components = []
    while foreground:
        start = foreground.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in foreground:
                    foreground.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        components.append(component)

    keep = max(components, key=len) if components else set()
    keep_colors = {(x, y): frame.get_at((x, y)) for x, y in keep}
    frame.fill(background)
    for (x, y), color in keep_colors.items():
        frame.set_at((x, y), color)
    frame.set_colorkey(background)
    return frame


def draw_pixel_explorer(screen, x, y, accent_color=(140, 90, 255), facing="front", scale=3):
    palette = {
        ".": None,
        "H": (24, 24, 28),
        "S": (242, 208, 176),
        "A": accent_color,
        "C": (54, 66, 88),
        "D": (30, 36, 48),
        "T": (45, 52, 68),
        "L": (205, 162, 102),
        "B": (33, 27, 24),
        "G": (240, 206, 94),
        "W": (236, 236, 240),
        "M": (120, 94, 60),
        "R": (168, 58, 42),
    }

    sprite_map = {
        "front": [
            "....HHHH....",
            "...HSSSSH...",
            "..HSSSSSSHH.",
            "..HSMMMMSH..",
            "...HAAAAH...",
            "..HAA..AAH..",
            "..HACCCCAH..",
            "..HAAA AAH..",
            "..HAGGGAH...",
            "...HDDDH....",
            "..HDDDDDH...",
            "..HD..D..H..",
            "...D....D...",
            "...D....D...",
            "............",
        ],
        "back": [
            "....HHHH....",
            "...HSSSSH...",
            "..HSSSSSSHH.",
            "..HSMMMMSH..",
            "...HAAAAH...",
            "..HAA..AAH..",
            "..HACCCCAH..",
            "..HAAA AAH..",
            "..HAGGGAH...",
            "...HDDDH....",
            "..HDDDDDH...",
            "..HD..D..H..",
            "...D....D...",
            "...D....D...",
            "............",
        ],
        "left": [
            "....HHHH....",
            "...HSSSSH...",
            "..HSSSSSSHH.",
            "..HSMMMMSH..",
            "...HAAAAH...",
            "..HAA..AAH..",
            "..HACCCCAH..",
            "..HAAA AAH..",
            "..HAGGGAH...",
            "...HDDDH....",
            "..HDDDDDH...",
            "..HD..D..H..",
            "...D....D...",
            "...D....D...",
            "............",
        ],
        "right": [
            "....HHHH....",
            "...HSSSSH...",
            "..HSSSSSSHH.",
            "..HSMMMMSH..",
            "...HAAAAH...",
            "..HAA..AAH..",
            "..HACCCCAH..",
            "..HAAA AAH..",
            "..HAGGGAH...",
            "...HDDDH....",
            "..HDDDDDH...",
            "..HD..D..H..",
            "...D....D...",
            "...D....D...",
            "............",
        ],
    }

    sprite = sprite_map.get(facing, sprite_map["front"])
    cell = max(1, int(scale))
    for row_index, row in enumerate(sprite):
        for col_index, ch in enumerate(row):
            if ch == ' ':
                continue
            color = palette.get(ch)
            if color is None:
                continue
            px = x + col_index * cell
            py = y + row_index * cell
            pygame.draw.rect(screen, color, (px, py, cell, cell))


def load_preview_sprite():
    sprite_path = os.path.join(GAME_IMAGE_DIR, "hero_spritesheet.png")
    if not os.path.exists(sprite_path):
        return None
    try:
        sheet = pygame.image.load(sprite_path).convert()
        frame_width = sheet.get_width() // 4
        frame_height = sheet.get_height() // 4
        frame = sheet.subsurface((0, 0, frame_width, frame_height)).copy()
        return clean_sprite_frame(frame)
    except pygame.error:
        return None


def load_horse_sprite():
    sprite_path = os.path.join(GAME_IMAGE_DIR, "manycharacter.png.jpg")
    if not os.path.exists(sprite_path):
        return None
    try:
        sheet = pygame.image.load(sprite_path).convert()
        frame_width = sheet.get_width() // 4
        frame_height = sheet.get_height() // 4
        horse_frame = sheet.subsurface((0, 0, frame_width, frame_height)).copy()
        horse_frame = clean_sprite_frame(horse_frame)
        content = horse_frame.get_bounding_rect()
        if not content.width or not content.height:
            return None
        horse_frame = horse_frame.subsurface(content)
        target_height = 110
        target_width = max(1, int(horse_frame.get_width() * target_height / horse_frame.get_height()))
        return pygame.transform.scale(horse_frame, (target_width, target_height))
    except (pygame.error, ValueError):
        return None


def load_talking_sprite():
    sprite_paths = [
        os.path.join(GAME_IMAGE_DIR, "talking.png"),
        os.path.join(SCENE_IMAGE_DIR, "talking.png"),
    ]
    for sprite_path in sprite_paths:
        if not os.path.exists(sprite_path):
            continue
        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()
            return pygame.transform.scale(sprite, (100, 100))
        except pygame.error:
            return None
    return None

# ============================================
# EXPLORER CLASS
# ============================================
class Explorer:
    def __init__(self, x, y, color=BLUE, name="Explorer", hat_type="traditional", class_name="Forest Ranger"):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 3
        self.color = color
        self.name = name
        self.hat_type = hat_type
        self.class_name = class_name
        self.class_data = character_class_data(class_name)
        self.horse_sprite = load_horse_sprite() if class_name == "Horse" else None
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.knowledge = 0
        self.wisdom = 0
        self.compassion = 0
        self.completed_districts = []
        self.collectibles = []
        self.sites_visited = []
        self.animation_offset = 0
        self.sprite_frames = self._load_sprite_frames()
        self.rendered_sprite_frames = self._prepare_sprite_frames()
        self.facing = "front"
        self.sprite_frame_index = 0

    def _load_sprite_frames(self):
        sprite_paths = [
            os.path.join(GAME_IMAGE_DIR, "hero_spritesheet.png"),
            os.path.join(GAME_IMAGE_DIR, "character_spritesheet.png"),
            os.path.join(GAME_IMAGE_DIR, "character_spritesheet.jpg"),
            os.path.join(GAME_IMAGE_DIR, "character.png"),
            os.path.join(GAME_IMAGE_DIR, "character.jpg"),
        ]
        for sprite_path in sprite_paths:
            if not os.path.exists(sprite_path):
                continue
            try:
                sheet = pygame.image.load(sprite_path).convert()
                frame_width = sheet.get_width() // 4
                frame_height = sheet.get_height() // 4
                frames = {}
                direction_rows = {"front": 0, "right": 1, "left": 2, "back": 3}
                for direction, row in direction_rows.items():
                    frames[direction] = []
                    for column in range(4):
                        frame = sheet.subsurface((column * frame_width, row * frame_height, frame_width, frame_height)).copy()
                        frames[direction].append(clean_sprite_frame(frame))
                return frames
            except (pygame.error, ValueError):
                return None
        return None

    def _prepare_sprite_frames(self):
        rendered_frames = {}
        for direction, frames in (self.sprite_frames or {}).items():
            rendered_frames[direction] = []
            for frame in frames:
                content_rect = frame.get_bounding_rect()
                if not content_rect.width or not content_rect.height:
                    rendered_frames[direction].append(frame)
                    continue
                frame = frame.subsurface(content_rect)
                target_height = 64
                target_width = max(1, int(frame.get_width() * target_height / frame.get_height()))
                rendered_frames[direction].append(pygame.transform.scale(frame, (target_width, target_height)))
        return rendered_frames
        
    def add_xp(self, amount):
        earned_xp = max(1, int(amount * 0.5))
        self.xp += earned_xp
        self.knowledge += earned_xp // 2
        if self.xp >= self.xp_to_next_level:
            self.level_up()
            
    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = int(self.xp_to_next_level * 1.2)
        self.speed += 0.5
        
    def move(self, keys, obstacles, exploration_mode=False, terrain_modifier=1.0):
        self.vel_x = 0
        self.vel_y = 0
        
        current_speed = self.speed * terrain_modifier
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vel_y = -current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vel_y = current_speed

        if self.vel_y < 0:
            self.facing = "back"
        elif self.vel_y > 0:
            self.facing = "front"
        elif self.vel_x < 0:
            self.facing = "left"
        elif self.vel_x > 0:
            self.facing = "right"
            
        self.animation_offset += 0.1
        if self.vel_x or self.vel_y:
            self.sprite_frame_index = int(self.animation_offset * 6) % 4
            
        new_x = self.x + self.vel_x
        new_y = self.y + self.vel_y
        
        temp_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        
        collision = False
        for obstacle in obstacles:
            if temp_rect.colliderect(obstacle.rect):
                collision = True
                break
                
        if not collision:
            self.x = new_x
            self.y = new_y
            
        if exploration_mode:
            self.x = max(50, min(self.x, WORLD_WIDTH - self.width - 50))
            self.y = max(50, min(self.y, WORLD_HEIGHT - self.height - 50))
        else:
            self.x = max(0, min(self.x, SCREEN_WIDTH - self.width))
            self.y = max(0, min(self.y, SCREEN_HEIGHT - self.height))
    
    def draw(self, screen, camera_x=0, camera_y=0):
        walking = self.vel_x or self.vel_y
        bob_y = math.sin(self.animation_offset * 2) * (3 if walking else 1)
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y + bob_y

        self._draw_class_appearance(screen, draw_x, draw_y)

        font = cached_font(20)
        name_text = font.render(self.name[:15], True, WHITE)
        name_rect = name_text.get_rect(center=(draw_x + self.width // 2, draw_y - 22))
        bg_rect = name_rect.inflate(12, 4)
        pygame.draw.rect(screen, BLACK, bg_rect, border_radius=4)
        screen.blit(name_text, name_rect)
        return

    def _draw_class_appearance(self, screen, draw_x, draw_y, scale=1):
        if self.horse_sprite:
            horse_rect = self.horse_sprite.get_rect(
                midbottom=(draw_x + self.width // 2, draw_y + self.height + 4)
            )
            screen.blit(self.horse_sprite, horse_rect)
            return

        frames = self.rendered_sprite_frames.get(self.facing) if self.rendered_sprite_frames else None
        if frames:
            frame = frames[self.sprite_frame_index]
            foot_offset = 3 if self.sprite_frame_index in (0, 2) and (self.vel_x or self.vel_y) else 0
            frame_rect = frame.get_rect(
                midbottom=(draw_x + self.width // 2 + foot_offset, draw_y + self.height + 4)
            )
            screen.blit(frame, frame_rect)

        # Level badge
        level_badge = pygame.Rect(draw_x + self.width - 12, draw_y - 8, 18, 18)
        pygame.draw.rect(screen, (255, 210, 70), level_badge, border_radius=9)
        level_font = cached_font(14)
        level_text = level_font.render(str(self.level), True, BLACK)
        level_rect = level_text.get_rect(center=level_badge.center)
        screen.blit(level_text, level_rect)
        
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def add_collectible(self, collectible):
        self.collectibles.append({"name": collectible.name, "description": collectible.description[:50], "district": collectible.district})
        self.add_xp(collectible.xp_reward)

# ============================================
# POINT OF INTEREST CLASS
# ============================================
class PointOfInterest:
    def __init__(self, x, y, district_data, site_index=0):
        self.x = x
        self.y = y
        self.site_index = site_index
        self.visited = False
        self.animation_offset = random.uniform(0, 2 * math.pi)
        
        if site_index < len(district_data.get("sacred_sites", [])):
            site = district_data["sacred_sites"][site_index]
            self.landmark_name = site["name"][:25]
            self.historical_fact = site.get("history", "A sacred site")
            self.cultural_significance = site.get("significance", "Deeply revered")
            self.did_you_know = site.get("fun_fact", "Attracts pilgrims")
            self.legend = site.get("legend", "Ancient stories surround this place")
            self.full_description = site.get("description", "")
        else:
            self.landmark_name = f"{district_data['name'][:15]} Landmark"
            self.historical_fact = district_data["historical_significance"]
            self.cultural_significance = district_data["religious_importance"]
            self.did_you_know = "This location holds deep spiritual meaning"
            self.legend = "Ancient stories are whispered here"
            self.full_description = ""
        
        self.knowledge_reward = 25
        self.wisdom_reward = 10
        self.icon = "🏛️"
        self.rect = pygame.Rect(x - 25, y - 25, 50, 50)
        
    def draw(self, screen, camera_x=0, camera_y=0):
        self.animation_offset += 0.05
        float_y = math.sin(self.animation_offset * 2) * 3
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        if not self.visited:
            for i in range(2):
                radius = 25 + i * 5
                pygame.draw.circle(screen, GOLD, (draw_x, draw_y), radius, 2)
            
            font = cached_font(40)
            icon_text = font.render(self.icon, True, GOLD)
            icon_rect = icon_text.get_rect(center=(draw_x, draw_y + float_y))
            screen.blit(icon_text, icon_rect)
            
            font = cached_font(18)
            name_text = font.render(self.landmark_name, True, WHITE)
            name_rect = name_text.get_rect(center=(draw_x, draw_y + 35))
            pygame.draw.rect(screen, BLACK, name_rect.inflate(10, 5))
            pygame.draw.rect(screen, GOLD, name_rect.inflate(10, 5), 1)
            screen.blit(name_text, name_rect)
        else:
            pygame.draw.circle(screen, GREEN, (draw_x, draw_y), 20)
            font = cached_font(30)
            check = font.render("✓", True, WHITE)
            check_rect = check.get_rect(center=(draw_x, draw_y))
            screen.blit(check, check_rect)
    
    def check_collision(self, player_rect):
        return self.rect.colliderect(player_rect) and not self.visited

# ============================================
# ENEMY CLASS
# ============================================
class RaiderEnemy:
    def __init__(self, x, y, image=None):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x - 18, y - 25, 36, 50)
        self.animation_offset = random.uniform(0, 2 * math.pi)
        self.image = image
        self.walk_phase = random.uniform(0, 2 * math.pi)
        self.walk_frame_index = 0
        self.facing_right = True
        self.is_walking = False

    def move_toward(self, target_x, target_y, speed=3.5):
        distance = math.hypot(target_x - self.x, target_y - self.y)
        if distance > speed:
            self.facing_right = target_x >= self.x
            self.x += (target_x - self.x) / distance * speed
            self.y += (target_y - self.y) / distance * speed
            self.rect.center = (int(self.x), int(self.y))
            self.walk_phase += 0.1
            self.walk_frame_index = int(self.walk_phase * 6) % 4
            self.is_walking = True
        else:
            self.is_walking = False

    def draw(self, screen, camera_x=0, camera_y=0):
        self.animation_offset += 0.05
        draw_x = int(self.x - camera_x)
        draw_y = int(self.y - camera_y + math.sin(self.animation_offset) * 2)

        if self.image:
            frame = self.image
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)
            step_offset = (3, 0, -3, 0)[self.walk_frame_index] if self.is_walking else 0
            image_rect = frame.get_rect(midbottom=(draw_x + step_offset, draw_y + 25))
            screen.blit(frame, image_rect)
            return

        pygame.draw.circle(screen, DARK_RED, (draw_x, draw_y - 18), 13)
        pygame.draw.rect(screen, DARK_RED, (draw_x - 15, draw_y - 5, 30, 30), border_radius=6)
        pygame.draw.line(screen, BLACK, (draw_x - 8, draw_y - 21), (draw_x - 3, draw_y - 19), 2)
        pygame.draw.line(screen, BLACK, (draw_x + 3, draw_y - 19), (draw_x + 8, draw_y - 21), 2)
        pygame.draw.line(screen, GRAY, (draw_x + 14, draw_y + 8), (draw_x + 29, draw_y - 12), 4)
        pygame.draw.line(screen, GOLD, (draw_x + 10, draw_y + 3), (draw_x + 18, draw_y + 9), 3)

        label_font = cached_font(20)
        label = label_font.render("RAIDER", True, RED)
        label_rect = label.get_rect(center=(draw_x, draw_y + 42))
        pygame.draw.rect(screen, BLACK, label_rect.inflate(8, 4), border_radius=3)
        screen.blit(label, label_rect)


# ============================================
# MONK NPC CLASS
# ============================================
class MonkNPC:
    def __init__(self, x, y, district_data):
        self.x = x
        self.y = y
        self.name = random.choice(["Lopen Dorji", "Khenpo Tenzin", "Forest Monk", "Elder Wangdi"])
        self.district_data = district_data
        self.interacted = False
        self.rect = pygame.Rect(x - 17, y - 22, 35, 45)
        self.animation_offset = random.uniform(0, 2 * math.pi)
        self.talking_sprite = load_talking_sprite()
        
    def draw(self, screen, camera_x=0, camera_y=0):
        self.animation_offset += 0.05
        float_y = math.sin(self.animation_offset) * 2
        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        
        pygame.draw.ellipse(screen, (50, 50, 50), (draw_x - 15, draw_y + 20, 30, 10))
        pygame.draw.rect(screen, (180, 70, 40), (draw_x - 15, draw_y - 30 + float_y, 30, 45), border_radius=8)
        pygame.draw.circle(screen, (255, 200, 150), (draw_x, draw_y - 35 + float_y), 12)
        pygame.draw.circle(screen, BLACK, (draw_x - 4, draw_y - 38 + float_y), 2)
        pygame.draw.circle(screen, BLACK, (draw_x + 4, draw_y - 38 + float_y), 2)
        pygame.draw.arc(screen, BLACK, (draw_x - 5, draw_y - 35 + float_y, 10, 8), math.pi, 2 * math.pi, 1)
        pygame.draw.circle(screen, (235, 125, 110), (draw_x - 8, draw_y - 34 + float_y), 1)
        pygame.draw.circle(screen, (235, 125, 110), (draw_x + 8, draw_y - 34 + float_y), 1)
        
        if not self.interacted:
            font = cached_font(16)
            bubble_text = font.render("💬 Talk", True, WHITE)
            bubble_rect = bubble_text.get_rect(center=(draw_x, draw_y - 55 + float_y))
            pygame.draw.rect(screen, BLACK, bubble_rect.inflate(10, 5), border_radius=10)
            pygame.draw.rect(screen, WHITE, bubble_rect.inflate(10, 5), 1, border_radius=10)
            screen.blit(bubble_text, bubble_rect)
    
    def check_collision(self, player_rect):
        return self.rect.colliderect(player_rect) and not self.interacted
    
    def interact(self, explorer, reputation_level):
        self.interacted = True
        explorer.add_xp(20)
        
        stories = [
            f"Greetings, {explorer.name}! Welcome to {self.district_data['name']}. May your journey bring you wisdom in this sacred land.",
            f"The people of {self.district_data['name']} welcome you with open hearts. Here is a blessing for your journey.",
            f"I see great potential in you, traveler. The spirits of this land smile upon those who seek knowledge."
        ]
        return random.choice(stories)

# ============================================
# KNOWLEDGE SCROLL CLASS
# ============================================
class KnowledgeScroll:
    def __init__(self, x, y, knowledge_type, content):
        self.x = x
        self.y = y
        self.type = knowledge_type
        self.content = content[:60]
        self.collected = False
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        self.float_offset = 0
        self.value = 10
        
        type_colors = {
            "history": (100, 150, 200),
            "culture": (200, 150, 100),
            "spiritual": (150, 100, 200),
            "nature": (100, 200, 100)
        }
        self.color = type_colors.get(knowledge_type, GOLD)
        
    def draw(self, screen, camera_x=0, camera_y=0):
        if not self.collected:
            self.float_offset = (self.float_offset + 0.05) % (2 * math.pi)
            float_y = math.sin(self.float_offset) * 3
            draw_x = self.x - camera_x
            draw_y = self.y - camera_y
            
            pygame.draw.rect(screen, GOLD, (draw_x - 12, draw_y - 8 + float_y, 24, 16), border_radius=3)
            pygame.draw.line(screen, self.color, (draw_x, draw_y - 5 + float_y), (draw_x, draw_y + 5 + float_y), 2)
    
    def check_collision(self, player_rect):
        return self.rect.colliderect(player_rect) and not self.collected
    
    def collect(self, explorer):
        self.collected = True
        explorer.add_xp(self.value)
        return f"Gained {self.value} {self.type} knowledge!"

# ============================================
# XP HEART CLASS
# ============================================
class ExpHeart:
    def __init__(self, x, y, value=15):
        self.x = x
        self.y = y
        self.value = value
        self.collected = False
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.animation_offset = random.uniform(0, 2 * math.pi)

    def draw(self, screen, camera_x=0, camera_y=0):
        if self.collected:
            return

        self.animation_offset = (self.animation_offset + 0.06) % (2 * math.pi)
        float_y = math.sin(self.animation_offset) * 3
        draw_x = int(self.x - camera_x)
        draw_y = int(self.y - camera_y + float_y)
        heart_points = [
            (draw_x, draw_y + 12),
            (draw_x - 14, draw_y - 2),
            (draw_x - 13, draw_y - 9),
            (draw_x - 7, draw_y - 14),
            (draw_x, draw_y - 8),
            (draw_x + 7, draw_y - 14),
            (draw_x + 13, draw_y - 9),
            (draw_x + 14, draw_y - 2),
        ]
        pygame.draw.polygon(screen, (235, 45, 75), heart_points)
        pygame.draw.polygon(screen, (255, 170, 185), heart_points, 2)
        pygame.draw.circle(screen, WHITE, (draw_x - 6, draw_y - 7), 2)

    def check_collision(self, player_rect):
        return self.rect.colliderect(player_rect) and not self.collected

    def collect(self, explorer):
        self.collected = True
        explorer.add_xp(self.value)
        return f"Heart collected! +{self.value} XP"

# ============================================
# HIDDEN DISCOVERY CLASS
# ============================================
class HiddenDiscovery:
    def __init__(self, x, y, secret_data, district_name):
        self.x = x
        self.y = y
        self.name = secret_data["name"][:25]
        self.description = secret_data["description"][:60]
        self.xp_reward = secret_data["xp"]
        self.district = district_name
        self.discovered = False
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)
        self.animation_offset = 0
        
    def draw(self, screen, camera_x=0, camera_y=0):
        if not self.discovered:
            self.animation_offset += 0.05
            float_y = math.sin(self.animation_offset) * 3
            draw_x = self.x - camera_x
            draw_y = self.y - camera_y
            
            pygame.draw.circle(screen, (GOLD[0], GOLD[1], GOLD[2], 100), (draw_x, draw_y + float_y), 20, 2)
            font = cached_font(36)
            q_mark = font.render("?", True, YELLOW)
            q_rect = q_mark.get_rect(center=(draw_x, draw_y + float_y))
            screen.blit(q_mark, q_rect)
    
    def check_collision(self, player_rect):
        return self.rect.colliderect(player_rect) and not self.discovered
    
    def discover(self, explorer):
        self.discovered = True
        explorer.add_collectible(self)
        return f"DISCOVERY: {self.name}! +{self.xp_reward} XP"

# ============================================
# OBSTACLE CLASS
# ============================================
class Obstacle:
    def __init__(self, x, y, width, height, color=GRAY):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        
    def draw(self, screen, camera_x=0, camera_y=0):
        draw_rect = pygame.Rect(self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, self.color, draw_rect, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 100), draw_rect, 2, border_radius=5)

# ============================================
# LEVEL SELECT CARD CLASS
# ============================================
class LevelSelectCard:
    def __init__(self, district_data, x, y, width, height, is_completed=False):
        self.district_data = district_data
        self.district_name = district_data["name"]
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_completed = is_completed
        self.rect = pygame.Rect(x, y, width, height)
        self.hover_animation = 0
        
    def draw(self, screen, mouse_pos=None):
        if self.rect.collidepoint(mouse_pos) if mouse_pos else False:
            self.hover_animation = min(1.0, self.hover_animation + 0.1)
        else:
            self.hover_animation = max(0, self.hover_animation - 0.1)
            
        if self.is_completed:
            base_color = GOLD
        else:
            base_color = DARK_GREEN
            
        if self.hover_animation > 0:
            color = tuple(min(255, c + int(50 * self.hover_animation)) for c in base_color)
        else:
            color = base_color
            
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 3, border_radius=10)
        
        font = cached_font(40)
        icon = font.render(self.district_data["icon"], True, WHITE)
        icon_rect = icon.get_rect(center=(self.x + self.width//2, self.y + 45))
        screen.blit(icon, icon_rect)
        
        name_font = cached_font(20)
        name = self.district_name
        if len(name) > 15:
            name = name[:13] + "..."
        name_surface = name_font.render(name, True, WHITE)
        screen.blit(name_surface, (self.x + self.width//2 - name_surface.get_width()//2, self.y + 95))
        
        diff_color = GREEN if self.district_data["difficulty"] == "Easy" else (YELLOW if self.district_data["difficulty"] == "Medium" else (ORANGE if self.district_data["difficulty"] == "Hard" else RED))
        diff_font = cached_font(14)
        diff_text = diff_font.render(f"{self.district_data['difficulty_icon']} {self.district_data['difficulty']}", True, diff_color)
        screen.blit(diff_text, (self.x + self.width//2 - diff_text.get_width()//2, self.y + 140))
        
        if self.is_completed:
            check_font = cached_font(30)
            check = check_font.render("✓", True, GREEN)
            screen.blit(check, (self.x + self.width - 25, self.y + 5))
            
    def handle_click(self, pos):
        return self.rect.collidepoint(pos)

# ============================================
# OPENING CINEMATIC
# ============================================
class IntroSequence:
    SCENES = [
        (4.5, "A strong warrior and his army explored distant forests and unfamiliar lands."),
        (4.5, "On their return to base, a powerful storm darkened the sky."),
        (4.5, "Wind and heavy rain scattered the army, leaving everyone unconscious."),
        (4.5, "When the storm passed, the warrior awoke in a silent and unfamiliar land."),
        (4.5, "A traveler told him that this beautiful place was called Bhutan."),
        (5.0, "Fascinated and curious, he began to explore its history, people, and culture."),
        (4.5, "THREADS OF TIME|Journey Through Bhutan"),
    ]

    def __init__(self, screen, finish):
        self.screen = screen
        self.finish = finish
        self.width, self.height = screen.get_size()
        self.started = False
        self.elapsed = 0.0
        self.scene_start = 0.0
        self.scene_index = 0
        self.last_time = pygame.time.get_ticks() / 1000.0
        self.story_font = pygame.font.Font(None, 30)
        self.prompt_font = pygame.font.Font(None, 34)
        self.title_font = pygame.font.Font(None, 78)
        self.rain = [(random.randrange(self.width), random.randrange(self.height), random.randrange(12, 28)) for _ in range(140)]
        self.character_image = None
        self.warrior_scene_image = None
        self.walking_scene_image = None
        self.finated_scene_image = None
        self.mantalking_scene_image = None
        self.exploring_scene_image = None
        self.couris_scene_image = None
        self.thinking_scene_image = None
        self.leader_image: pygame.Surface = cast(pygame.Surface, None)
        couris_paths = [
            os.path.join(SCENE_IMAGE_DIR, "couris.png.png"),
            os.path.join(LEGACY_IMAGE_DIR, "couris.png.png"),
        ]
        for couris_path in couris_paths:
            try:
                if os.path.exists(couris_path):
                    self.couris_scene_image = pygame.image.load(couris_path).convert()
                    break
            except (pygame.error, OSError):
                continue
        exploring_paths = [
            os.path.join(GAME_IMAGE_DIR, "exploringplace.png.png"),
            os.path.join(LEGACY_IMAGE_DIR, "exploringplace.png.png"),
        ]
        for exploring_path in exploring_paths:
            try:
                if os.path.exists(exploring_path):
                    self.exploring_scene_image = pygame.image.load(exploring_path).convert()
                    break
            except (pygame.error, OSError):
                continue
        fallback_scene_paths = [
            os.path.join(GAME_IMAGE_DIR, "mantalking.png"),
            os.path.join(LEGACY_IMAGE_DIR, "mantalking.png"),
        ]
        for mantalking_path in fallback_scene_paths:
            try:
                if os.path.exists(mantalking_path):
                    self.mantalking_scene_image = pygame.image.load(mantalking_path).convert()
                    break
            except (pygame.error, OSError):
                continue
        thinking_paths = [
            os.path.join(GAME_IMAGE_DIR, "thinking.png.jpg"),
            os.path.join(GAME_IMAGE_DIR, "thinking.png"),
            os.path.join(SCENE_IMAGE_DIR, "thinking.png"),
            os.path.join(MISC_IMAGE_DIR, "thinking.png"),
        ]
        for thinking_path in thinking_paths:
            try:
                self.thinking_scene_image = pygame.image.load(thinking_path).convert()
                break
            except (pygame.error, OSError):
                continue
        walking_path = os.path.join(GAME_IMAGE_DIR, "walking.png")
        try:
            self.walking_scene_image = pygame.image.load(walking_path).convert()
        except (pygame.error, OSError):
            pass
        finated_path = os.path.join(GAME_IMAGE_DIR, "finated.png")
        try:
            self.finated_scene_image = pygame.image.load(finated_path).convert()
        except (pygame.error, OSError):
            pass
        character_paths = [
            os.path.join(GAME_IMAGE_DIR, "warrior.png"),
            os.path.join(GAME_IMAGE_DIR, "character.png"),
        ]
        for character_path in character_paths:
            try:
                self.character_image = pygame.image.load(character_path).convert()
                if os.path.basename(character_path).lower() == "warrior.png":
                    self.warrior_scene_image = self.character_image
                break
            except (pygame.error, OSError):
                continue
        leader_path = os.path.join(GAME_IMAGE_DIR, "character.png")
        try:
            leader_sheet = pygame.image.load(leader_path).convert()
            leader_rect = pygame.Rect(490, 20, 205, 365)
            if leader_rect.right <= leader_sheet.get_width() and leader_rect.bottom <= leader_sheet.get_height():
                self.leader_image = leader_sheet.subsurface(leader_rect).copy()
                self._remove_leader_background()
        except (pygame.error, OSError):
            pass
        self.character_frame: pygame.Surface = cast(pygame.Surface, None)
        if self.character_image is not None:
            if self.warrior_scene_image is not None:
                self.character_frame = self.character_image
            else:
                source_rect = pygame.Rect(490, 20, 205, 365)
                if source_rect.right <= self.character_image.get_width() and source_rect.bottom <= self.character_image.get_height():
                    self.character_frame = self.character_image.subsurface(source_rect).copy()
                    self._remove_character_background()

    def _remove_character_background(self):
        if self.character_frame is None:
            return
        background = self.character_frame.convert_alpha()
        width, height = background.get_size()
        background_color = background.get_at((0, 0))[:3]
        pending = [(0, 0)]
        visited = set()
        while pending:
            x, y = pending.pop()
            if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
                continue
            visited.add((x, y))
            color = background.get_at((x, y))[:3]
            if max(abs(color[index] - background_color[index]) for index in range(3)) > 14:
                continue
            background.set_at((x, y), (color[0], color[1], color[2], 0))
            pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
        self.character_frame = background

    def handle(self):
        now = pygame.time.get_ticks() / 1000.0
        delta = min(0.05, max(0.0, now - self.last_time))
        self.last_time = now
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not self.started and (event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN):
                self.started = True
                self.last_time = now
            elif self.started and event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.finish()
                return
        if not self.started:
            self.screen.fill((3, 5, 9))
            text = self.prompt_font.render("Press anywhere to start", True, WHITE)
            self.screen.blit(text, text.get_rect(center=(self.width // 2, self.height // 2)))
            pygame.display.flip()
            return
        self.elapsed += delta
        duration, story = self.SCENES[self.scene_index]
        scene_time = self.elapsed - self.scene_start
        if scene_time >= duration:
            self.scene_index += 1
            self.scene_start = self.elapsed
            if self.scene_index >= len(self.SCENES):
                self.finish()
                return
            duration, story = self.SCENES[self.scene_index]
            scene_time = 0.0
        self._draw_scene(self.scene_index, scene_time)
        self._draw_story(story, scene_time)
        fade = max(0.0, 0.75 - scene_time) / 0.75
        fade = max(fade, max(0.0, scene_time - duration + 0.75) / 0.75)
        if fade:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(min(1.0, fade) * 255)))
            self.screen.blit(overlay, (0, 0))
        pygame.display.flip()

    def _draw_scene(self, scene, scene_time):
        storm = scene in (1, 2)
        if scene == 2 and self.finated_scene_image is not None:
            self._draw_warrior_scene_image(scene_time, self.finated_scene_image)
            self._draw_storm_overlay(scene_time, True)
            if math.sin(scene_time * 9) > 0.94:
                flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                flash.fill((220, 235, 255, 150))
                self.screen.blit(flash, (0, 0))
            return
        if scene in (0, 1, 2) and (self.walking_scene_image is not None or self.warrior_scene_image is not None):
            scene_image = self.warrior_scene_image if scene == 0 else self.walking_scene_image
            if scene_image is None:
                scene_image = self.walking_scene_image
                if scene_image is None:
                    scene_image = self.warrior_scene_image
            self._draw_warrior_scene_image(scene_time, scene_image)
            if scene in (1, 2):
                self._draw_storm_overlay(scene_time, scene == 2)
        elif scene <= 2:
            self._draw_forest(storm)
            for index in range(7):
                running_x = 130 + index * 145
                if storm:
                    running_x += int(scene_time * 120) % (self.width + 180) - 90
                self._draw_warrior(
                    running_x,
                    self.height - 190 + index % 2 * 8,
                    0.75 if index else 1.0,
                    running=storm,
                    run_phase=scene_time * 14 + index,
                )
        elif scene == 3 and self.thinking_scene_image is not None:
            self._draw_full_scene_image(self.thinking_scene_image)
        elif scene == 4 and self.mantalking_scene_image is not None:
            self._draw_full_scene_image(self.mantalking_scene_image)
        elif scene == 5 and self.exploring_scene_image is not None:
            self._draw_full_scene_image(self.exploring_scene_image)
        elif scene in (3, 4):
            self._draw_forest(False)
            self._draw_character_image(scene_time, self.width // 2)
        elif scene == 6 and self.couris_scene_image is not None:
            self._draw_warrior_scene_image(scene_time, self.couris_scene_image)
        else:
            self._draw_landscape()
            self._draw_character_image(scene_time, self.width // 2 - 140)
        if scene == 2 and math.sin(scene_time * 9) > 0.94:
            flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash.fill((220, 235, 255, 150))
            self.screen.blit(flash, (0, 0))

    def _draw_warrior_scene_image(self, scene_time, scene_image):
        scale = max(
            self.width / scene_image.get_width(),
            self.height / scene_image.get_height(),
        )
        scale *= 1.0 + 0.035 * min(1.0, scene_time / 4.5)
        scaled_size = (
            int(scene_image.get_width() * scale),
            int(scene_image.get_height() * scale),
        )
        scaled_image = pygame.transform.smoothscale(scene_image, scaled_size)
        max_crop_x = max(0, scaled_image.get_width() - self.width)
        max_crop_y = max(0, scaled_image.get_height() - self.height)
        crop_x = int(max_crop_x / 2 + math.sin(scene_time * 0.45) * 24)
        crop_x = max(0, min(crop_x, max_crop_x))
        crop_y = max_crop_y // 2
        crop_rect = pygame.Rect(
            crop_x,
            crop_y,
            self.width,
            self.height,
        )
        image = scaled_image.subsurface(crop_rect).copy()
        image.set_alpha(min(255, int(scene_time * 255)))
        self.screen.fill((8, 12, 18))
        self.screen.blit(image, (0, 0))

    def _draw_full_scene_image(self, scene_image):
        # Create gradient background for better presentation
        gradient_surface = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            color_intensity = int(8 + (y / self.height) * 15)
            pygame.draw.line(gradient_surface, (color_intensity, color_intensity + 4, color_intensity + 9), (0, y), (self.width, y))
        self.screen.blit(gradient_surface, (0, 0))
        
        # Calculate proportional scaling to maintain aspect ratio
        img_width, img_height = scene_image.get_size()
        padding = 60  # Padding from edges
        max_width = self.width - (padding * 2)
        max_height = self.height - (padding * 2)
        
        # Scale maintaining aspect ratio
        scale = min(max_width / img_width, max_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Scale and center the image
        scaled_image = pygame.transform.smoothscale(scene_image, (new_width, new_height))
        image_x = (self.width - new_width) // 2
        image_y = (self.height - new_height) // 2
        
        # Add subtle border around image
        border_color = (50, 80, 120)
        pygame.draw.rect(self.screen, border_color, (image_x - 4, image_y - 4, new_width + 8, new_height + 8), 4)
        
        # Blit the image
        self.screen.blit(scaled_image, (image_x, image_y))

    def _draw_two_images_horizontal(self, image_left, image_right):
        # Create gradient background for better presentation
        gradient_surface = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            color_intensity = int(8 + (y / self.height) * 15)
            pygame.draw.line(gradient_surface, (color_intensity, color_intensity + 4, color_intensity + 9), (0, y), (self.width, y))
        self.screen.blit(gradient_surface, (0, 0))
        
        # Parameters for layout
        padding = 30  # Padding from edges
        gap = 25  # Gap between images
        max_width_per_image = (self.width - (padding * 2) - gap) // 2
        max_height = self.height - (padding * 2)
        
        # Scale left image (thinking.png - vertical image)
        img_left_width, img_left_height = image_left.get_size()
        scale_left = min(max_width_per_image / img_left_width, max_height / img_left_height)
        left_width = int(img_left_width * scale_left)
        left_height = int(img_left_height * scale_left)
        scaled_left = pygame.transform.smoothscale(image_left, (left_width, left_height))
        left_x = padding
        left_y = (self.height - left_height) // 2
        
        # Scale right image (mantalking.png - vertical image)
        img_right_width, img_right_height = image_right.get_size()
        scale_right = min(max_width_per_image / img_right_width, max_height / img_right_height)
        right_width = int(img_right_width * scale_right)
        right_height = int(img_right_height * scale_right)
        scaled_right = pygame.transform.smoothscale(image_right, (right_width, right_height))
        right_x = self.width - padding - right_width
        right_y = (self.height - right_height) // 2
        
        # Draw elegant borders around images
        border_color = (50, 80, 120)
        border_width = 5
        
        # Left image border
        pygame.draw.rect(self.screen, border_color, (left_x - border_width, left_y - border_width, left_width + border_width * 2, left_height + border_width * 2), border_width)
        # Inner highlight for depth
        pygame.draw.rect(self.screen, (80, 120, 160), (left_x - border_width, left_y - border_width, left_width + border_width * 2, left_height + border_width * 2), 1)
        
        # Right image border
        pygame.draw.rect(self.screen, border_color, (right_x - border_width, right_y - border_width, right_width + border_width * 2, right_height + border_width * 2), border_width)
        # Inner highlight for depth
        pygame.draw.rect(self.screen, (80, 120, 160), (right_x - border_width, right_y - border_width, right_width + border_width * 2, right_height + border_width * 2), 1)
        
        # Blit both images
        self.screen.blit(scaled_left, (left_x, left_y))
        self.screen.blit(scaled_right, (right_x, right_y))

    def _draw_storm_overlay(self, scene_time, lightning=False):
        storm_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        storm_overlay.fill((5, 12, 27, 105))
        for x in range(-80, self.width, 150):
            pygame.draw.ellipse(storm_overlay, (10, 16, 30, 155), (x, 35 + (x % 25), 210, 90))
        self.screen.blit(storm_overlay, (0, 0))
        for x, y, length in self.rain:
            moving_y = (y + scene_time * 180) % self.height
            moving_x = (x - scene_time * 25) % self.width
            pygame.draw.line(
                self.screen,
                (125, 165, 205),
                (moving_x, moving_y),
                (moving_x - 10, (moving_y + length) % self.height),
                1,
            )
        if lightning and math.sin(scene_time * 9) > 0.94:
            flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash.fill((220, 235, 255, 150))
            self.screen.blit(flash, (0, 0))

    def _draw_forest(self, storm):
        top = (12, 19, 34) if storm else (35, 70, 92)
        bottom = (9, 23, 22) if storm else (25, 70, 43)
        for y in range(self.height):
            ratio = y / self.height
            color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
            pygame.draw.line(self.screen, color, (0, y), (self.width, y))
        ground = int(self.height * 0.7)
        pygame.draw.rect(self.screen, bottom, (0, ground, self.width, self.height - ground))
        for x in range(-30, self.width + 40, 60):
            height = 105 + (x * 5 % 70)
            pygame.draw.polygon(self.screen, (7, 30, 25), [(x, ground + 18), (x + 30, ground - height), (x + 62, ground + 18)])
        if storm:
            for x, y, length in self.rain:
                pygame.draw.line(self.screen, (125, 165, 205), (x, y), (x - 9, (y + length) % self.height), 1)

    def _draw_warrior(self, x, y, scale, running=False, run_phase=0.0):
        color = (12, 14, 20)
        body = max(8, int(28 * scale))
        pygame.draw.ellipse(self.screen, (5, 7, 10), (x - body // 2 - 8, y + 55, body + 16, 12))
        pygame.draw.circle(self.screen, color, (int(x), int(y)), max(8, int(14 * scale)))
        pygame.draw.polygon(self.screen, color, [(x - body // 2, y + 12), (x + body // 2, y + 12), (x + body // 2 + 8, y + 62), (x - body // 2 - 8, y + 62)])
        leg_swing = math.sin(run_phase) * 18 if running else 0
        pygame.draw.line(self.screen, color, (x - 8, y + 25), (x - 25 + leg_swing, y + 60), max(2, int(7 * scale)))
        pygame.draw.line(self.screen, color, (x + 8, y + 25), (x + 25 - leg_swing, y + 60), max(2, int(7 * scale)))
        pygame.draw.line(self.screen, GOLD, (x + 20, y + 18), (x + 40, y - 38), 3)

    def _draw_landscape(self):
        for y in range(self.height):
            ratio = y / self.height
            pygame.draw.line(self.screen, (int(110 - ratio * 65), int(180 - ratio * 80), int(215 - ratio * 80)), (0, y), (self.width, y))
        pygame.draw.polygon(self.screen, (65, 94, 110), [(0, 450), (180, 190), (340, 390), (540, 110), (760, 390), (970, 170), (self.width, 400), (self.width, self.height), (0, self.height)])
        pygame.draw.polygon(self.screen, (29, 83, 53), [(0, 540), (220, 350), (450, 535), (700, 330), (self.width, 500), (self.width, self.height), (0, self.height)])
        pygame.draw.polygon(self.screen, (30, 105, 145), [(0, self.height - 40), (300, self.height - 80), (560, self.height - 20), (800, self.height - 100), (self.width, self.height - 35), (self.width, self.height), (0, self.height)])

    def _draw_character_image(self, scene_time, center_x):
        if self.leader_image is None:
            return
        image_height = min(390, self.height - 150)
        image_width = int(self.leader_image.get_width() * image_height / self.leader_image.get_height())
        image = pygame.transform.smoothscale(self.leader_image, (image_width, image_height))
        image.set_alpha(min(235, int(scene_time * 255)))
        image_rect = image.get_rect(midbottom=(center_x, self.height - 35))
        self.screen.blit(image, image_rect)

    def _remove_leader_background(self):
        if self.leader_image is None:
            return
        background = self.leader_image.convert_alpha()
        width, height = background.get_size()
        background_color = background.get_at((0, 0))[:3]
        pending = [(0, 0)]
        visited = set()
        while pending:
            x, y = pending.pop()
            if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
                continue
            visited.add((x, y))
            color = background.get_at((x, y))[:3]
            if max(abs(color[index] - background_color[index]) for index in range(3)) > 14:
                continue
            background.set_at((x, y), (color[0], color[1], color[2], 0))
            pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
        self.leader_image = background

    def _draw_story(self, story, scene_time):
        shown = story[:max(0, min(len(story), int((scene_time - 0.35) * 34)))]
        if not shown:
            return
        if "|" in shown:
            title, subtitle = shown.split("|", 1)
            self.screen.blit(self.title_font.render(title, True, GOLD), (self.width // 2 - 260, self.height // 2 - 55))
            self.screen.blit(self.story_font.render(subtitle, True, WHITE), (self.width // 2 - 125, self.height // 2 + 35))
            return
        panel = pygame.Surface((self.width - 120, 90), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 165))
        self.screen.blit(panel, (60, self.height - 125))
        for index, line in enumerate(wrap_text(shown, self.story_font, self.width - 170)[:2]):
            rendered = self.story_font.render(line, True, WHITE)
            self.screen.blit(rendered, rendered.get_rect(center=(self.width // 2, self.height - 92 + index * 30)))

# ============================================
# GAME CLASS
# ============================================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.INTRO
        self.intro = IntroSequence(self.screen, self.finish_intro)
        self.show_menu_guide = False
        self.show_pause_menu = False
        self.sound_muted = False

        self.background_music_path = self.find_background_music()
        self.play_background_music()
        self.song_catalog = {
            "folk_90s": {
                "title": "Bhutanese Folk Tunes",
                "filename": "Bhutanese Traditional folk musical InstrumentalTunes of 90's [D9Uagz2EmaE].mp3",
                "cost": 0,
            },
            "world_music_day": {
                "title": "World Music Day",
                "filename": "Bhutanese Instrumental _ World Music Day Celebrations 2024 [aGH3AEgb7UE].mp3",
                "cost": 0,
            },
            "ling_sho_ray": {
                "title": "Ling Sho Ray",
                "filename": "Bhutanese song on traditional instruments-Ling Sho ray [yEznZxD4-I8].mp3",
                "cost": 150,
            },
        }
        self.owned_songs = {"folk_90s"}
        self.selected_song = "folk_90s"
        
        self.explorer: Explorer = cast(Explorer, None)
        self.current_district: dict = cast(dict, None)
        self.completed_districts = []
        self.points_of_interest = []
        self.enemies = []
        self.monks = []
        self.knowledge_scrolls = []
        self.exp_hearts = []
        self.hidden_discoveries = []
        self.current_cultural_quiz: dict = cast(dict, None)
        self.cultural_quiz_questions = []
        self.cultural_quiz_index = 0
        self.cultural_quiz_score = 0
        self.raid_enemy_health = 1
        self.raid_feedback = ""
        self.raid_feedback_color = WHITE
        self.raid_feedback_timer = 0
        
        self.exploration_complete = False
        self.exploration_narration_text = ""
        self.exploration_narration_timer = 0
        
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 72)
        self.big_font = pygame.font.Font(None, 48)
        self.preview_sprite = load_preview_sprite()
        self.horse_preview_sprite = load_horse_sprite()
        self.menu_background = self.load_menu_background()

        self.map_image = self.load_bhutan_map()
        self.exploration_image = self.load_exploration_image()
        self.map_selected_district = None
        self.map_zoom = 1.0
        self.map_zoom_target = 1.0
        self.show_game_guide = True
        
        self.level_cards = []
        self.create_level_cards()
        
        self.selected_district_for_info = None
        self.scroll_y = 0
        self.scroll_speed = 0
        self.info_scroll_offset = 0
        self._last_content_height = 0
        
        # Load images
        self.landmark_images = {}
        self.load_landmark_images()
        self.enemy_image = self.load_enemy_image()
        self.certificate_image = self.load_certificate_image()
        
        # Adventure Systems
        self.time_of_day = TimeOfDay.DAY
        self.time_counter = 0
        self.day_duration = 6000
        
        self.camera_x: int = 0
        self.camera_y: int = 0

        self.terrain_grid = [[random.choice(list(TerrainType)) for _ in range(30)] for _ in range(30)]
        self.current_terrain = TerrainType.FOREST_PATH

        self.skills = {skill_type: Skill(skill_type) for skill_type in SkillType}
        self.reputation = Reputation()
        self.photo_journal = PhotoJournal()

        self.particles = []
        self.secrets_found = []
        self.encounter_cooldown = 0

        self.wildlife = []

        self.name_input = ""
        self.selected_class = "Custom Explorer"
        self.unlocked_classes = {"Custom Explorer"}
        self.selected_color = CHARACTER_CLASSES[self.selected_class]["color"]
        self.selected_hat = CHARACTER_CLASSES[self.selected_class]["hat"]
        self.input_active = True
        self.show_error = False
        self.error_timer = 0

        self.saved_explorer_data = None
        self.load_game()

    def find_background_music(self):
        candidates = [
            "Bhutanese Traditional folk musical InstrumentalTunes of 90's [D9Uagz2EmaE].mp3",
            "Bhutanese Instrumental _ World Music Day Celebrations 2024 [aGH3AEgb7UE].mp3",
            "Bhutanese song on traditional instruments-Ling Sho ray [yEznZxD4-I8].mp3",
        ]

        for name in candidates:
            possible = sound_path(name)
            if os.path.exists(possible):
                return possible

        return None

    def play_background_music(self):
        if not self.background_music_path:
            return

        try:
            pygame.mixer.music.load(self.background_music_path)
            pygame.mixer.music.set_volume(0.0 if self.sound_muted else 1.0)
            pygame.mixer.music.play(-1)
        except pygame.error as exc:
            print(f"Background music could not be loaded: {exc}")

    def get_song_path(self, song_key):
        song = self.song_catalog.get(song_key)
        if not song:
            return None
        path = sound_path(song["filename"])
        if os.path.exists(path):
            return path
        return None

    def play_song(self, song_key):
        path = self.get_song_path(song_key)
        if not path:
            return False
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.0 if self.sound_muted else 1.0)
            pygame.mixer.music.play(-1)
            self.selected_song = song_key
            self.background_music_path = path
            return True
        except pygame.error as exc:
            print(f"Song could not be loaded: {exc}")
            return False

    def available_song_xp(self):
        if self.explorer:
            return self.explorer.xp
        if self.saved_explorer_data:
            return self.saved_explorer_data.get("xp", 0)
        return 0

    def buy_song(self, song_key):
        song = self.song_catalog.get(song_key)
        if not song or song_key in self.owned_songs:
            return "already_owned"
        if self.available_song_xp() < song["cost"]:
            return "not_enough_xp"
        if self.explorer:
            self.explorer.xp -= song["cost"]
        elif self.saved_explorer_data:
            self.saved_explorer_data["xp"] -= song["cost"]
        self.owned_songs.add(song_key)
        self.play_song(song_key)
        if self.explorer:
            self.save_game()
        return "purchased"

    def load_enemy_image(self):
        image_paths = [
            os.path.join(GAME_IMAGE_DIR, "enemy.png"),
        ]
        for image_path in image_paths:
            try:
                image = pygame.image.load(image_path).convert_alpha()
                for x in range(image.get_width()):
                    for y in range(image.get_height()):
                        red, green, blue, alpha = image.get_at((x, y))
                        if min(red, green, blue) > 195 and max(red, green, blue) - min(red, green, blue) < 75:
                            image.set_at((x, y), (red, green, blue, 0))
                target_height = 100
                target_width = max(1, int(image.get_width() * target_height / image.get_height()))
                return pygame.transform.smoothscale(image, (target_width, target_height))
            except (pygame.error, OSError):
                continue
        return None

    def load_certificate_image(self):
        return load_certificate_image()

    def finish_intro(self):
        self.state = GameState.MAIN_MENU

    def load_menu_background(self):
        background_path = os.path.join(GAME_IMAGE_DIR, "lobby_image.png")
        try:
            background = pygame.image.load(background_path).convert()
            return pygame.transform.smoothscale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except (pygame.error, OSError):
            return None

    def load_exploration_image(self):
        image_paths = [
            os.path.join(GAME_IMAGE_DIR, "exploringplace.png.png"),
            os.path.join(LEGACY_IMAGE_DIR, "exploringplace.png.png"),
            os.path.join(SCENE_IMAGE_DIR, "couris.png.png"),
            os.path.join(LEGACY_IMAGE_DIR, "couris.png.png"),
            os.path.join(GAME_IMAGE_DIR, "mantalking.png"),
            os.path.join(LEGACY_IMAGE_DIR, "mantalking.png"),
            os.path.join(GAME_IMAGE_DIR, "exploring.png"),
        ]
        for image_path in image_paths:
            try:
                if os.path.exists(image_path):
                    image = pygame.image.load(image_path).convert()
                    return pygame.transform.smoothscale(image, (WORLD_WIDTH, WORLD_HEIGHT))
            except (pygame.error, OSError):
                continue
        return None

    def load_bhutan_map(self):
        map_paths = [
            os.path.join(LEGACY_IMAGE_DIR, "bhutan_map.png"),
            os.path.join(GAME_IMAGE_DIR, "bhutan_map.png"),
            os.path.join(GAME_IMAGE_DIR, "bhutan_map.jpg"),
        ]
        for map_path in map_paths:
            if not os.path.exists(map_path):
                continue
            try:
                map_image = pygame.image.load(map_path).convert()
                max_width = SCREEN_WIDTH - 120
                max_height = SCREEN_HEIGHT - 150
                scale = min(max_width / map_image.get_width(), max_height / map_image.get_height())
                map_size = (
                    int(map_image.get_width() * scale),
                    int(map_image.get_height() * scale),
                )
                return pygame.transform.smoothscale(map_image, map_size)
            except pygame.error:
                pass
        return None

    def _normalize_image_key(self, value):
        return "".join(character.lower() for character in value if character.isalnum())

    def _load_image_file(self, filepath):
        try:
            surface = pygame.image.load(filepath)
            return surface.convert_alpha() if surface.get_alpha() is not None else surface.convert()
        except pygame.error:
            try:
                from PIL import Image
                with Image.open(filepath) as image:
                    rgba_image = image.convert("RGBA")
                    return pygame.image.frombuffer(rgba_image.tobytes(), rgba_image.size, "RGBA")
            except Exception:
                return None

    def load_landmark_images(self):
        """Load landmark images from the bundled folders with flexible matching."""
        self.landmark_images = {}
        candidate_dirs = [
            LANDMARK_IMAGE_DIR,
            SACRED_SITE_IMAGE_DIR,
        ]
        supported_exts = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp"}

        alias_map = {
            "Phobjikha Valley": [
                "phobjikha-village-bhutan",
                "phobjikha village bhutan",
                "phobjikha valley",
            ],
        }

        for district in bhutan_districts:
            district_name = district["name"]
            for site in district.get("sacred_sites", []):
                site_name = site["name"]
                site_key = self._normalize_image_key(site_name)
                district_key = self._normalize_image_key(district_name)

                possible_names = {
                    site_key,
                    self._normalize_image_key(f"{district_name}_{site_name}"),
                    self._normalize_image_key(f"{district_name}-{site_name}"),
                    self._normalize_image_key(f"{district_name}_{site_name}".replace(" ", "_")),
                    self._normalize_image_key(site_name.replace(" ", "_")),
                    self._normalize_image_key(site_name.replace(" ", "-")),
                }
                for alias in alias_map.get(site_name, []):
                    possible_names.add(self._normalize_image_key(alias))

                image_path = None
                for folder in candidate_dirs:
                    if not os.path.isdir(folder):
                        continue
                    for file_name in os.listdir(folder):
                        base_name, ext = os.path.splitext(file_name)
                        if ext.lower() not in supported_exts:
                            continue
                        normalized = self._normalize_image_key(base_name)
                        if normalized in possible_names or self._normalize_image_key(file_name) in possible_names:
                            image_path = os.path.join(folder, file_name)
                            break
                    if image_path:
                        break

                if site_name == "Tashichho Dzong" and image_path is None:
                    image_path = os.path.join(GAME_IMAGE_DIR, "dzong.jpg")

                if image_path is None:
                    continue

                loaded = self._load_image_file(image_path)
                if loaded is not None:
                    loaded = pygame.transform.smoothscale(loaded, (280, 200))
                    self.landmark_images[site_name] = loaded

        print(f"Loaded {len(self.landmark_images)} landmark images from bundled folders")

    def create_level_cards(self):
        self.level_cards = []
        cols = 4
        card_width = 270
        card_height = 190
        spacing_x = 20
        spacing_y = 25
        total_width = cols * (card_width + spacing_x) - spacing_x
        start_x = (SCREEN_WIDTH - total_width) // 2
        start_y = 160
        
        for i, district in enumerate(bhutan_districts):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)
            is_completed = district["name"] in self.completed_districts
            card = LevelSelectCard(district, x, y, card_width, card_height, is_completed)
            self.level_cards.append(card)
            
    def update_completion_status(self):
        for card in self.level_cards:
            card.is_completed = card.district_name in self.completed_districts
            
    def get_terrain_from_district(self, district_data):
        terrain_name = district_data.get("terrain_type", TerrainType.FOREST_PATH.name)
        # Safe lookup — unknown names fall back to FOREST_PATH instead of crashing
        terrain = getattr(TerrainType, terrain_name, None)
        if terrain is None:
            try:
                terrain = TerrainType[terrain_name]
            except (KeyError, ValueError):
                import warnings
                warnings.warn(f"Unknown terrain '{terrain_name}', defaulting to FOREST_PATH")
                terrain = TerrainType.FOREST_PATH
        return terrain
            
    def generate_forest_environment(self):
        self.wildlife = []
        
        for _ in range(8):
            animal_x = random.randint(100, WORLD_WIDTH - 100)
            animal_y = random.randint(100, WORLD_HEIGHT - 100)
            animal_type = random.choice(["bird", "deer", "butterfly"])
            self.wildlife.append(Wildlife(animal_x, animal_y, animal_type))
            
    def generate_exploration_level(self, district_data):
        self.points_of_interest = []
        self.monks = []
        self.knowledge_scrolls = []
        self.exp_hearts = []
        self.hidden_discoveries = []
        
        if self.explorer:
            self.explorer.x = WORLD_WIDTH // 2
            self.explorer.y = WORLD_HEIGHT // 2
            self.camera_x = int(self.explorer.x - SCREEN_WIDTH // 2)
            self.camera_y = int(self.explorer.y - SCREEN_HEIGHT // 2)
        
        self.current_terrain = self.get_terrain_from_district(district_data)
        self.generate_forest_environment()
        
        # Generate 4-5 points of interest (sacred sites)
        num_pois = len(district_data.get("sacred_sites", []))
        for i in range(num_pois):
            x = y = 0
            for _ in range(100):
                candidate_x = random.randint(250, WORLD_WIDTH - 250)
                candidate_y = random.randint(250, WORLD_HEIGHT - 250)
                far_from_start = math.hypot(candidate_x - WORLD_WIDTH // 2, candidate_y - WORLD_HEIGHT // 2) >= 700
                far_from_sites = all(
                    math.hypot(candidate_x - site.x, candidate_y - site.y) >= 500
                    for site in self.points_of_interest
                )
                if far_from_start and far_from_sites:
                    x, y = candidate_x, candidate_y
                    break
            if not x:
                x = random.randint(250, WORLD_WIDTH - 250)
                y = random.randint(250, WORLD_HEIGHT - 250)
            self.points_of_interest.append(PointOfInterest(x, y, district_data, i))

        num_monks = random.randint(1, 2)
        for i in range(num_monks):
            angle = random.uniform(0, 2 * math.pi)
            radius = 350 + random.randint(-80, 80)
            x = WORLD_WIDTH // 2 + math.cos(angle) * radius
            y = WORLD_HEIGHT // 2 + math.sin(angle) * radius
            self.monks.append(MonkNPC(x, y, district_data))
            
        knowledge_types = ["history", "culture", "spiritual", "nature"]
        num_scrolls = random.randint(10, 15)
        for i in range(num_scrolls):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.randint(150, 450)
            x = WORLD_WIDTH // 2 + math.cos(angle) * radius
            y = WORLD_HEIGHT // 2 + math.sin(angle) * radius
            k_type = random.choice(knowledge_types)
            content = f"About {district_data['name']}"
            self.knowledge_scrolls.append(KnowledgeScroll(x, y, k_type, content))

        for _ in range(8):
            heart_x = random.randint(100, WORLD_WIDTH - 100)
            heart_y = random.randint(100, WORLD_HEIGHT - 100)
            self.exp_hearts.append(ExpHeart(heart_x, heart_y))
            
        for secret in district_data.get("hidden_secrets", [])[:3]:
            angle = random.uniform(0, 2 * math.pi)
            radius = random.randint(380, 520)
            x = WORLD_WIDTH // 2 + math.cos(angle) * radius
            y = WORLD_HEIGHT // 2 + math.sin(angle) * radius
            self.hidden_discoveries.append(HiddenDiscovery(x, y, secret, district_data["name"]))
            
        self.current_cultural_quiz = district_data.get("cultural_challenge")
        self.encounter_cooldown = 0

    def trigger_random_encounter(self):
        if self.explorer is None:
            return
        events = ["wildlife", "villager", "weather", "treasure"]
        event = random.choice(events)
        
        if event == "wildlife":
            self.show_notification("🐏 A rare Himalayan blue sheep appears! (+15 XP)", GOLD)
            self.skills[SkillType.NAVIGATION].add_xp(15)
            self.explorer.add_xp(15)
            self.add_particles(self.explorer.x, self.explorer.y, GOLD, 10)
        elif event == "villager":
            self.show_notification("👤 A villager offers you traditional snacks! (+10 Reputation)", GREEN)
            self.reputation.modify(10)
        elif event == "treasure":
            self.show_notification("💎 You find a hidden treasure! +40 XP", GOLD)
            self.explorer.add_xp(40)
            self.add_particles(self.explorer.x, self.explorer.y, GOLD, 20)
                
    def add_particles(self, x, y, color, count):
        for _ in range(count):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-2, 2)
            lifetime = random.randint(20, 60)
            self.particles.append(Particle(x, y, color, (vx, vy), lifetime))
            
    def update_time_of_day(self):
        self.time_counter += 1
        cycle_progress = (self.time_counter % self.day_duration) / self.day_duration
        
        if cycle_progress < 0.25:
            self.time_of_day = TimeOfDay.DAWN
        elif cycle_progress < 0.5:
            self.time_of_day = TimeOfDay.DAY
        elif cycle_progress < 0.75:
            self.time_of_day = TimeOfDay.DUSK
        else:
            self.time_of_day = TimeOfDay.NIGHT
            
    def draw_forest_background(self):
        # Solid bright green ground
        self.screen.fill((0, 200, 0))
            
    def draw_terrain_with_forest(self):
        if self.exploration_image:
            self.screen.blit(self.exploration_image, (-self.camera_x, -self.camera_y))
            return

        start_x = int(self.camera_x / 100) * 100
        start_y = int(self.camera_y / 100) * 100
        
        for x in range(start_x, start_x + SCREEN_WIDTH + 100, 100):
            for y in range(start_y, start_y + SCREEN_HEIGHT + 100, 100):
                grid_x = int(x / 100) % len(self.terrain_grid)
                grid_y = int(y / 100) % len(self.terrain_grid[0])
                terrain = self.terrain_grid[grid_x][grid_y]
                rect = pygame.Rect(x - self.camera_x, y - self.camera_y, 100, 100)
                pygame.draw.rect(self.screen, terrain.color, rect)

    def draw_visibility_overlay(self):
        if self.time_of_day != TimeOfDay.NIGHT or self.explorer is None:
            return
            
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(180)
        
        center = (self.explorer.x - self.camera_x, self.explorer.y - self.camera_y)
        radius = self.time_of_day.visibility_radius
        
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                dist = math.hypot(x - center[0], y - center[1])
                if dist < radius:
                    alpha = int(180 * (dist / radius))
                    if alpha < 0:
                        alpha = 0
                    overlay.set_at((x, y), (0, 0, 0, alpha))
                    
        self.screen.blit(overlay, (0, 0))
        
    def _draw_image_placeholder(self, rect):
        """Draw a placeholder for missing images"""
        # Draw a subtle background
        pygame.draw.rect(self.screen, (40, 40, 60), rect, border_radius=10)
        # Draw icon
        font = cached_font(60)
        icon_text = font.render("🏛️", True, (100, 100, 150))
        icon_rect = icon_text.get_rect(center=rect.center)
        self.screen.blit(icon_text, icon_rect)
        # Draw "No Image" text
        no_img_font = cached_font(16)
        no_img_text = no_img_font.render("Image not available", True, (100, 100, 150))
        no_img_rect = no_img_text.get_rect(center=(rect.centerx, rect.bottom - 15))
        self.screen.blit(no_img_text, no_img_rect)
        
    def show_detailed_landmark_info(self, poi):
        """Show COMPREHENSIVE information about a landmark with image"""
        if self.current_district is None or self.explorer is None:
            return
        
        # Find the full site data from the district
        site_data = None
        for site in self.current_district.get("sacred_sites", []):
            if site["name"] == poi.landmark_name:
                site_data = site
                break
        
        panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 500, SCREEN_HEIGHT//2 - 320, 1000, 640)
        
        # Prepare all information sections
        sections = []
        
        # District header
        sections.append(("DISTRICT", f"{self.current_district['full_name']} - {self.current_district['region']} Region"))
        
        # History section
        if site_data:
            sections.append(("HISTORY", site_data.get("history", poi.historical_fact)))
            sections.append(("SIGNIFICANCE", site_data.get("significance", poi.cultural_significance)))
            sections.append(("FUN FACT", site_data.get("fun_fact", poi.did_you_know)))
            sections.append(("LEGEND & MYTHOLOGY", site_data.get("legend", poi.legend)))
        else:
            sections.append(("HISTORICAL BACKGROUND", poi.historical_fact))
            sections.append(("CULTURAL SIGNIFICANCE", poi.cultural_significance))
            sections.append(("INTERESTING FACTS", poi.did_you_know))
        
        # Add district context
        sections.append(("DISTRICT CONTEXT", f"{self.current_district['name']} is known for: {self.current_district.get('historical_significance', 'Rich cultural heritage')}"))
        
        # Add cultural practices
        if "cultural_practices" in self.current_district:
            festivals = self.current_district["cultural_practices"].get("festivals", [])
            if festivals:
                fest_text = ", ".join([f.get("name", "") for f in festivals[:2]])
                sections.append(("FESTIVALS", f"Famous festivals include {fest_text}"))
        
        # Add local wisdom
        if "wisdom_quotes" in self.current_district and self.current_district["wisdom_quotes"]:
            sections.append(("LOCAL WISDOM", f"\"{self.current_district['wisdom_quotes'][0][:150]}\""))
        
        # Scroll position
        scroll_offset = 0
        line_height = 26
        header_height = 30
        content_y_start = panel_rect.y + 130
        
        # Calculate total content height (reduced because we have image)
        total_content_height = 0
        max_sections = 5
        for i, (section_title, section_content) in enumerate(sections[:max_sections]):
            total_content_height += header_height
            content_lines = wrap_text(section_content, self.small_font, panel_rect.width - 380)
            total_content_height += len(content_lines) * line_height
            total_content_height += 10
        
        max_scroll = max(0, total_content_height - (panel_rect.height - 180))
        
        # Main interaction loop
        viewing_info = True
        take_photo_btn = None
        continue_btn = None
        
        while viewing_info:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.MOUSEWHEEL:
                    scroll_offset -= event.y * 30
                    scroll_offset = max(0, min(scroll_offset, max_scroll))
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if take_photo_btn and take_photo_btn.collidepoint(mouse_pos):
                        if self.photo_journal.capture(self.current_district["name"], poi.landmark_name):
                            self.explorer.add_xp(self.photo_journal.bonus_xp_per_photo)
                            self.add_particles(self.explorer.x, self.explorer.y, GOLD, 25)
                            self.show_notification(f"📸 Photo captured! +{self.photo_journal.bonus_xp_per_photo} XP", GOLD)
                    elif continue_btn and continue_btn.collidepoint(mouse_pos):
                        viewing_info = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        viewing_info = False
                    elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        viewing_info = False
            
            # Draw background overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(210)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            
            # Draw main panel
            panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 500, SCREEN_HEIGHT//2 - 320, 1000, 640)
            pygame.draw.rect(self.screen, (30, 25, 18), panel_rect, border_radius=20)
            pygame.draw.rect(self.screen, GOLD, panel_rect, 3, border_radius=20)
            
            # Title
            title_font = cached_font(36)
            title_text = f"{self.current_district['icon']} {poi.landmark_name}"
            title = title_font.render(title_text, True, GOLD)
            title_rect = title.get_rect(center=(panel_rect.x + 200, panel_rect.y + 30))
            self.screen.blit(title, title_rect)
            
            # Subtitle
            subtitle_font = cached_font(20)
            subtitle_text = f"{self.current_district['full_name']} • {self.current_district['region']} Region"
            subtitle = subtitle_font.render(subtitle_text, True, WHEAT)
            subtitle_rect = subtitle.get_rect(center=(panel_rect.x + 200, panel_rect.y + 58))
            self.screen.blit(subtitle, subtitle_rect)
            
            # Draw image on the right side
            image_rect = pygame.Rect(panel_rect.x + panel_rect.width - 310, panel_rect.y + 20, 280, 200)
            pygame.draw.rect(self.screen, (20, 20, 30), image_rect, border_radius=10)
            pygame.draw.rect(self.screen, GOLD, image_rect, 2, border_radius=10)
            
            # Check if we have an image for this landmark
            image_key = poi.landmark_name
            if image_key in self.landmark_images:
                try:
                    img = self.landmark_images[image_key]
                    # Center the image in the rect
                    img_rect = img.get_rect(center=image_rect.center)
                    self.screen.blit(img, img_rect)
                except Exception as e:
                    self._draw_image_placeholder(image_rect)
            else:
                self._draw_image_placeholder(image_rect)
            
            # Add a small caption for the image
            caption_font = cached_font(14)
            caption_text = caption_font.render(f"{poi.landmark_name}, {self.current_district['name']}", True, GOLD)
            caption_rect = caption_text.get_rect(center=(image_rect.centerx, image_rect.bottom + 15))
            self.screen.blit(caption_text, caption_rect)
            
            # Draw decorative line
            pygame.draw.line(self.screen, GOLD, (panel_rect.x + 20, panel_rect.y + 85), 
                            (panel_rect.x + panel_rect.width - 320, panel_rect.y + 85), 2)
            
            # Draw scroll indicator
            if max_scroll > 0:
                scroll_bar_height = max(40, panel_rect.height - 220)
                scroll_percent = scroll_offset / max_scroll
                scroll_bar_y = panel_rect.y + 100 + (scroll_bar_height - 40) * scroll_percent
                pygame.draw.rect(self.screen, GRAY, (panel_rect.x + panel_rect.width - 315, panel_rect.y + 100, 8, scroll_bar_height), border_radius=4)
                pygame.draw.rect(self.screen, GOLD, (panel_rect.x + panel_rect.width - 315, scroll_bar_y, 8, 40), border_radius=4)
            
            # Draw scrollable content
            y_pos = content_y_start - scroll_offset
            small_font = self.small_font
            medium_font = cached_font(24)
            
            # Create clipping region for text
            clip_rect = pygame.Rect(panel_rect.x + 10, panel_rect.y + 95, panel_rect.width - 340, panel_rect.height - 170)
            old_clip = self.screen.get_clip()
            self.screen.set_clip(clip_rect)
            
            max_sections = 5
            for section_title, section_content in sections[:max_sections]:
                if panel_rect.y + 95 < y_pos + header_height < panel_rect.y + panel_rect.height - 80:
                    header = medium_font.render(section_title, True, CYAN)
                    self.screen.blit(header, (panel_rect.x + 20, y_pos))
                    y_pos += header_height
                    
                    content_lines = wrap_text(section_content, small_font, panel_rect.width - 380)
                    for line in content_lines[:5]:
                        if panel_rect.y + 95 < y_pos < panel_rect.y + panel_rect.height - 80:
                            content = small_font.render(line, True, WHEAT)
                            self.screen.blit(content, (panel_rect.x + 30, y_pos))
                            y_pos += line_height
                    y_pos += 8
                else:
                    y_pos += header_height
                    content_lines = wrap_text(section_content, small_font, panel_rect.width - 380)
                    y_pos += len(content_lines) * line_height + 8
            
            self.screen.set_clip(old_clip)
            
            # Buttons
            button_y = panel_rect.y + panel_rect.height - 55
            
            take_photo_btn = pygame.Rect(panel_rect.x + 20, button_y, 160, 40)
            pygame.draw.rect(self.screen, DARK_BLUE, take_photo_btn, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, take_photo_btn, 2, border_radius=10)
            photo_text = self.small_font.render("📷 TAKE PHOTO", True, WHITE)
            photo_rect = photo_text.get_rect(center=take_photo_btn.center)
            self.screen.blit(photo_text, photo_rect)
            
            # Photo count
            photo_count_text = self.small_font.render(f"Photos: {len(self.photo_journal.photos)}/{self.photo_journal.max_photos}", True, GRAY)
            photo_count_rect = photo_count_text.get_rect(topleft=(take_photo_btn.x, take_photo_btn.bottom + 5))
            self.screen.blit(photo_count_text, photo_count_rect)
            
            continue_btn = pygame.Rect(panel_rect.x + panel_rect.width - 180, button_y, 150, 40)
            pygame.draw.rect(self.screen, GOLD, continue_btn, 2, border_radius=10)
            continue_text = self.small_font.render("CONTINUE →", True, WHITE)
            continue_rect = continue_text.get_rect(center=continue_btn.center)
            self.screen.blit(continue_text, continue_rect)
            
            reward_text = self.small_font.render(f"+{poi.knowledge_reward} Knowledge  |  +{poi.wisdom_reward} Wisdom  |  +25 XP", True, GREEN)
            reward_rect = reward_text.get_rect(center=(panel_rect.centerx - 50, button_y + 65))
            self.screen.blit(reward_text, reward_rect)
            
            pygame.display.flip()
            self.clock.tick(60)
        
        self.explorer.add_xp(poi.knowledge_reward + poi.wisdom_reward)
        self.explorer.knowledge += poi.knowledge_reward
        self.explorer.wisdom += poi.wisdom_reward
        self.add_particles(self.explorer.x, self.explorer.y, GOLD, 30)
    
    def show_knowledge_panel(self, poi):
        self.show_detailed_landmark_info(poi)
    
    def show_monk_dialogue(self, monk, story):
        panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 350, SCREEN_HEIGHT//2 - 140, 700, 280)
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        pygame.draw.rect(self.screen, (40, 70, 40), panel_rect, border_radius=15)
        pygame.draw.rect(self.screen, GOLD, panel_rect, 3, border_radius=15)

        if monk.talking_sprite:
            talking_rect = monk.talking_sprite.get_rect(center=(panel_rect.x + 75, panel_rect.centery))
            self.screen.blit(monk.talking_sprite, talking_rect)
        
        name_text = self.big_font.render(monk.name, True, CYAN)
        text_center_x = panel_rect.centerx
        name_rect = name_text.get_rect(center=(text_center_x, panel_rect.y + 40))
        self.screen.blit(name_text, name_rect)
        
        story_lines = wrap_text(story, self.font, 500)
        y_offset = 80
        for line in story_lines:
            story_text = self.font.render(line, True, WHEAT)
            self.screen.blit(story_text, (text_center_x - story_text.get_width()//2, panel_rect.y + y_offset))
            y_offset += 32
        
        reward_text = self.small_font.render("+20 XP", True, GREEN)
        reward_rect = reward_text.get_rect(center=(text_center_x, panel_rect.bottom - 20))
        self.screen.blit(reward_text, reward_rect)
        
        continue_btn = pygame.Rect(text_center_x - 60, panel_rect.bottom - 78, 120, 35)
        continue_text = self.font.render("Continue", True, WHITE)
        continue_text_rect = continue_text.get_rect(center=continue_btn.center)
        self.screen.blit(continue_text, continue_text_rect)
        
        pygame.display.flip()
        
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if continue_btn.collidepoint(event.pos):
                        waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        waiting = False
                        
    def show_discovery_panel(self, discovery):
        panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2 - 100, 600, 180)
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        pygame.draw.rect(self.screen, GOLD, panel_rect, border_radius=15)
        pygame.draw.rect(self.screen, WHITE, panel_rect, 3, border_radius=15)
        
        title = self.big_font.render("✨ DISCOVERY! ✨", True, YELLOW)
        title_rect = title.get_rect(center=(panel_rect.centerx, panel_rect.y + 40))
        self.screen.blit(title, title_rect)
        
        name_text = self.font.render(discovery.name, True, DARK_RED)
        name_rect = name_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 95))
        self.screen.blit(name_text, name_rect)
        
        reward_text = self.small_font.render(f"+{discovery.xp_reward} XP", True, GREEN)
        reward_rect = reward_text.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 50))
        self.screen.blit(reward_text, reward_rect)
        
        continue_btn = pygame.Rect(panel_rect.centerx - 60, panel_rect.bottom - 80, 120, 35)
        continue_text = self.font.render("Continue", True, WHITE)
        continue_text_rect = continue_text.get_rect(center=continue_btn.center)
        self.screen.blit(continue_text, continue_text_rect)
        
        pygame.display.flip()
        
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if continue_btn.collidepoint(event.pos):
                        waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        waiting = False
                        
    def show_notification(self, message, color):
        notif_surface = self.small_font.render(message[:60], True, color)
        notif_rect = notif_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 80))
        self.screen.blit(notif_surface, notif_rect)
        pygame.display.flip()
        pygame.time.wait(800)

    def draw_scrollable_district_info(self, district, panel_x, panel_y, panel_width, panel_height):
        """Draw district info with proper text wrapping"""
        # Prepare text content with proper formatting
        text_sections = []
        
        # History section
        history_text = district.get('historical_significance', 'N/A')
        if history_text and history_text != 'N/A':
            text_sections.append(("HISTORY", history_text))
        
        # People section
        people_info = []
        if district.get('population'):
            people_info.append(f"Population: {district['population']}")
        if district.get('main_ethnic_groups'):
            people_info.append(f"Ethnic Groups: {district['main_ethnic_groups']}")
        if district.get('traditional_occupations'):
            people_info.append(f"Occupations: {district['traditional_occupations']}")
        if people_info:
            text_sections.append(("PEOPLE", "\n".join(people_info)))
        
        # Sacred Sites
        sacred_sites = district.get('sacred_sites', [])
        if sacred_sites:
            sites_text = []
            for site in sacred_sites[:4]:
                site_line = f"• {site['name']}: {site.get('description', '')}"
                if len(site_line) > 60:
                    site_line = site_line[:57] + "..."
                sites_text.append(site_line)
            text_sections.append(("SACRED SITES", "\n".join(sites_text)))
        
        # Festivals
        festivals = district.get('cultural_practices', {}).get('festivals', [])
        if festivals:
            fest_text = []
            for fest in festivals[:2]:
                fest_text.append(f"• {fest['name']} ({fest.get('months', 'N/A')})")
            text_sections.append(("FESTIVALS", "\n".join(fest_text)))
        
        # Cuisine
        cuisine = district.get('cultural_practices', {}).get('cuisine', [])
        if cuisine:
            cuisine_text = "• " + "\n• ".join(cuisine[:3])
            text_sections.append(("LOCAL CUISINE", cuisine_text))
        
        # Wisdom Quotes
        quotes = district.get('wisdom_quotes', [])
        if quotes:
            quote = quotes[0]
            if len(quote) > 80:
                quote = quote[:77] + "..."
            text_sections.append(("WISDOM QUOTE", f"\"{quote}\""))
        
        # Unique Facts
        facts = district.get('unique_facts', [])
        if facts:
            fact_text = "• " + "\n• ".join(facts[:2])
            text_sections.append(("UNIQUE FACTS", fact_text))
        
        # Additional info
        extra_info = []
        if district.get('required_knowledge'):
            extra_info.append(f"Required Knowledge: {district['required_knowledge']}")
        if district.get('completion_reward'):
            extra_info.append(f"Mastery Reward: {district['completion_reward']}")
        if extra_info:
            text_sections.append(("REQUIREMENTS", "\n".join(extra_info)))
        
        # Calculate total content height for scrolling
        line_height = 25
        header_height = 30
        section_spacing = 20
        content_width = panel_width - 60
        
        # Draw each section
        y_pos = panel_y + 125 - self.info_scroll_offset
        small_font = cached_font(22)
        
        # Create clipping region
        clip_rect = pygame.Rect(panel_x + 10, panel_y + 95, panel_width - 30, panel_height - 140)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)
        
        total_height = 0
        
        for section_title, section_content in text_sections:
            # Draw section header
            if panel_y + 95 <= y_pos + header_height <= panel_y + panel_height - 60:
                header = self.font.render(section_title, True, CYAN)
                self.screen.blit(header, (panel_x + 20, y_pos))
                y_pos += header_height
                total_height += header_height
                
                # Draw content with wrapping
                content_lines = section_content.split('\n')
                for line in content_lines:
                    if line.strip():
                        wrapped_lines = wrap_text(line, small_font, content_width)
                        for wrapped_line in wrapped_lines:
                            if panel_y + 95 <= y_pos <= panel_y + panel_height - 60:
                                text_surface = small_font.render(wrapped_line, True, WHEAT)
                                self.screen.blit(text_surface, (panel_x + 30, y_pos))
                                y_pos += line_height
                                total_height += line_height
                            else:
                                y_pos += line_height
                                total_height += line_height
                    else:
                        y_pos += 5
                        total_height += 5
                
                y_pos += section_spacing // 2
                total_height += section_spacing // 2
            else:
                # Skip rendering but still count space
                y_pos += header_height
                total_height += header_height
                content_lines = section_content.split('\n')
                for line in content_lines:
                    if line.strip():
                        wrapped_lines = wrap_text(line, small_font, content_width)
                        y_pos += len(wrapped_lines) * line_height
                        total_height += len(wrapped_lines) * line_height
                    else:
                        y_pos += 5
                        total_height += 5
        
        # Restore clip
        self.screen.set_clip(old_clip)
        
        # Store total height for scroll calculations
        self._last_content_height = total_height

    def draw_district_info_panel(self, district):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        panel_width = 950
        panel_height = 580
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        
        pygame.draw.rect(self.screen, (40, 40, 70), (panel_x, panel_y, panel_width, panel_height), border_radius=15)
        pygame.draw.rect(self.screen, district["region_color"], (panel_x, panel_y, panel_width, panel_height), 4, border_radius=15)
        
        header_font = cached_font(40)
        header_text = f"{district['icon']} {district['full_name']}"
        header = header_font.render(header_text, True, GOLD)
        header_rect = header.get_rect(center=(panel_x + panel_width//2, panel_y + 35))
        self.screen.blit(header, header_rect)
        
        # Close button
        close_rect = pygame.Rect(panel_x + panel_width - 45, panel_y + 10, 35, 35)
        pygame.draw.rect(self.screen, RED, close_rect, border_radius=8)
        close_text = self.font.render("X", True, WHITE)
        close_text_rect = close_text.get_rect(center=(close_rect.centerx, close_rect.centery))
        self.screen.blit(close_text, close_text_rect)
        
        # Draw scrollable content
        self.draw_scrollable_district_info(district, panel_x, panel_y, panel_width, panel_height)
        
        # Draw scroll indicator
        if hasattr(self, '_last_content_height') and self._last_content_height > panel_height - 200:
            max_scroll = max(0, self._last_content_height - (panel_height - 200))
            scroll_bar_height = max(40, panel_height - 170)
            scroll_percent = min(1.0, self.info_scroll_offset / max_scroll) if max_scroll > 0 else 0
            scroll_bar_y = panel_y + 105 + (scroll_bar_height - 40) * scroll_percent
            
            pygame.draw.rect(self.screen, GRAY, (panel_x + panel_width - 20, panel_y + 105, 8, scroll_bar_height), border_radius=4)
            pygame.draw.rect(self.screen, GOLD, (panel_x + panel_width - 20, scroll_bar_y, 8, 40), border_radius=4)
        
        # Buttons
        button_width = 180
        button_height = 40
        button_y = panel_y + panel_height - 55
        
        back_button = pygame.Rect(panel_x + 50, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, RED, back_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, back_button, 2, border_radius=8)
        back_text = self.font.render("BACK", True, WHITE)
        back_text_rect = back_text.get_rect(center=(back_button.centerx, back_button.centery))
        self.screen.blit(back_text, back_text_rect)
        
        explore_button = pygame.Rect(panel_x + panel_width - button_width - 50, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, FOREST_GREEN, explore_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, explore_button, 2, border_radius=8)
        explore_text = self.font.render("EXPLORE", True, WHITE)
        explore_text_rect = explore_text.get_rect(center=(explore_button.centerx, explore_button.centery))
        self.screen.blit(explore_text, explore_text_rect)
        
        return close_rect, back_button, explore_button
        
    def draw_skills_panel(self):
        panel_width = 350
        panel_height = 250
        panel_x = 20
        panel_y = SCREEN_HEIGHT - panel_height - 20
        
        pygame.draw.rect(self.screen, DARK_BROWN, (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, LIGHT_BROWN, (panel_x, panel_y, panel_width, panel_height), 2)
        
        title = self.font.render("🌟 Skills", True, GOLD)
        self.screen.blit(title, (panel_x + 10, panel_y + 10))
        
        y_offset = 45
        for skill in self.skills.values():
            skill_text = f"{skill.type.value}: Lv.{skill.level} ({skill.xp}/{skill.xp_to_next})"
            color = GOLD if skill.level > 2 else WHITE
            rendered = self.small_font.render(skill_text, True, color)
            self.screen.blit(rendered, (panel_x + 10, panel_y + y_offset))
            y_offset += 25
            
        rep_text = f"Reputation: {self.reputation.title}"
        rendered_rep = self.small_font.render(rep_text, True, CYAN)
        self.screen.blit(rendered_rep, (panel_x + 10, panel_y + y_offset + 10))
        
    def draw_exploration_hud(self):
        self.draw_exploration_minimap()

        menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - 55, 10, 110, 42)
        pygame.draw.rect(self.screen, (10, 25, 32), menu_rect, border_radius=7)
        pygame.draw.rect(self.screen, GOLD, menu_rect, 2, border_radius=7)
        menu_text = self.small_font.render("MENU", True, WHITE)
        self.screen.blit(menu_text, menu_text.get_rect(center=menu_rect.center))

        photo_text = self.small_font.render(f"📷 Photos: {len(self.photo_journal.photos)}/{self.photo_journal.max_photos}", True, WHITE)
        self.screen.blit(photo_text, (10, 10))
        
        rep_text = self.small_font.render(f"🏆 {self.reputation.title}", True, GOLD)
        self.screen.blit(rep_text, (10, 35))

    def draw_exploration_minimap(self):
        map_rect = pygame.Rect(SCREEN_WIDTH - 235, 12, 215, 165)
        pygame.draw.rect(self.screen, (10, 25, 32), map_rect, border_radius=8)
        pygame.draw.rect(self.screen, GOLD, map_rect, 2, border_radius=8)

        inner = pygame.Rect(map_rect.x + 8, map_rect.y + 28, map_rect.width - 16, map_rect.height - 58)
        pygame.draw.rect(self.screen, (25, 70, 58), inner, border_radius=4)
        pygame.draw.line(self.screen, (45, 105, 80), inner.midtop, inner.midbottom, 1)
        pygame.draw.line(self.screen, (45, 105, 80), inner.midleft, inner.midright, 1)

        for poi in self.points_of_interest:
            marker_x = inner.x + int((poi.x / WORLD_WIDTH) * inner.width)
            marker_y = inner.y + int((poi.y / WORLD_HEIGHT) * inner.height)
            marker_color = GREEN if poi.visited else GOLD
            pygame.draw.circle(self.screen, marker_color, (marker_x, marker_y), 5)
            pygame.draw.circle(self.screen, WHITE, (marker_x, marker_y), 5, 1)

        if self.explorer:
            player_x = inner.x + int((self.explorer.x / WORLD_WIDTH) * inner.width)
            player_y = inner.y + int((self.explorer.y / WORLD_HEIGHT) * inner.height)
            pygame.draw.circle(self.screen, CYAN, (player_x, player_y), 6)
            pygame.draw.circle(self.screen, WHITE, (player_x, player_y), 6, 1)

        title = cached_font(18).render("SACRED SITES", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(map_rect.centerx, map_rect.y + 14)))
        pygame.draw.circle(self.screen, GOLD, (map_rect.x + 45, map_rect.bottom - 13), 4)
        self.screen.blit(cached_font(14).render("site", True, WHITE), (map_rect.x + 53, map_rect.bottom - 20))
        pygame.draw.circle(self.screen, CYAN, (map_rect.x + 112, map_rect.bottom - 13), 4)
        self.screen.blit(cached_font(14).render("you", True, WHITE), (map_rect.x + 120, map_rect.bottom - 20))

    def draw_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 190, SCREEN_HEIGHT // 2 - 155, 380, 310)
        pygame.draw.rect(self.screen, (10, 25, 32), panel, border_radius=10)
        pygame.draw.rect(self.screen, GOLD, panel, 3, border_radius=10)
        title = self.title_font.render("PAUSED", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 55)))

        buttons = {
            "resume": pygame.Rect(panel.x + 45, panel.y + 95, 290, 48),
            "mute": pygame.Rect(panel.x + 45, panel.y + 155, 290, 48),
            "leave": pygame.Rect(panel.x + 45, panel.y + 215, 290, 48),
        }
        labels = {
            "resume": "RESUME GAME",
            "mute": "UNMUTE SOUND" if self.sound_muted else "MUTE SOUND",
            "leave": "LEAVE GAME",
        }
        for key, rect in buttons.items():
            pygame.draw.rect(self.screen, (35, 65, 68), rect, border_radius=6)
            pygame.draw.rect(self.screen, LIGHT_BROWN, rect, 2, border_radius=6)
            text = self.small_font.render(labels[key], True, WHITE)
            self.screen.blit(text, text.get_rect(center=rect.center))
        return buttons

    def toggle_sound(self):
        self.sound_muted = not self.sound_muted
        pygame.mixer.music.set_volume(0.0 if self.sound_muted else 1.0)
        
    def start_district_exploration(self, district_data):
        self.current_district = district_data
        self.exploration_complete = False
        self.time_of_day = TimeOfDay.DAY
        self.time_counter = 0
        self.generate_exploration_level(district_data)
        self.exploration_narration_text = f"🌿 {district_data['tour_narration']} 🌿"
        self.exploration_narration_timer = 180
        self.info_scroll_offset = 0
        self.state = GameState.EXPLORATION
        
    def draw_menu_background(self):
        """Paro Taktsang (Tiger's Nest) painted with pygame shapes."""
        if self.menu_background is not None:
            self.screen.blit(self.menu_background, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 70))
            self.screen.blit(overlay, (0, 0))
            return

        t = pygame.time.get_ticks()

        # --- SKY  (hazy atmospheric gradient, lighter at horizon) ---
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(130 + (1 - ratio) * 60)
            g = int(155 + (1 - ratio) * 55)
            b = int(185 + (1 - ratio) * 35)
            pygame.draw.line(self.screen, (min(255, r), min(255, g), min(255, b)),
                             (0, y), (SCREEN_WIDTH, y))

        # --- FAR MOUNTAINS (misty, blue-gray silhouettes) ---
        far = [(0, 420), (80, 300), (180, 340), (320, 240), (430, 270),
               (580, 195), (720, 235), (880, 205), (1000, 255), (1120, 220),
               (1200, 260), (1200, 700), (0, 700)]
        pygame.draw.polygon(self.screen, (155, 165, 180), far)

        mid = [(0, 460), (70, 360), (190, 390), (290, 320), (460, 370),
               (620, 300), (790, 345), (940, 310), (1080, 355), (1200, 330),
               (1200, 700), (0, 700)]
        pygame.draw.polygon(self.screen, (85, 105, 90), mid)

        # --- VALLEY FLOOR (dark dense forest at base) ---
        pygame.draw.rect(self.screen, (40, 65, 40), (0, 490, SCREEN_WIDTH, 210))

        # Dense valley pine trees
        for ix in range(0, SCREEN_WIDTH, 22):
            h = 55 + ((ix * 7) % 35)
            cx = ix + 11
            ty = 492
            pygame.draw.polygon(self.screen, (18, 52, 18),
                                [(cx, ty - h), (cx - 13, ty), (cx + 13, ty)])
            pygame.draw.polygon(self.screen, (25, 70, 25),
                                [(cx, ty - h + 15), (cx - 10, ty + 8), (cx + 10, ty + 8)])

        # --- ROCKY CLIFF (right-centre bulk) ---
        cliff = [(420, 700), (380, 530), (400, 400), (450, 290), (510, 200),
                 (580, 130), (660, 85), (760, 70), (870, 95), (970, 160),
                 (1060, 260), (1150, 380), (1200, 500), (1200, 700)]
        pygame.draw.polygon(self.screen, (105, 98, 85), cliff)

        # Cliff texture - rough vertical cracks
        crack_col = (82, 76, 65)
        for ci, (cx2, cy2, cx3, cy3) in enumerate([
            (500, 330, 530, 560), (560, 260, 600, 490), (640, 200, 670, 420),
            (720, 160, 755, 380), (820, 180, 840, 340)
        ]):
            pygame.draw.line(self.screen, crack_col, (cx2, cy2), (cx3, cy3), 2)
            pygame.draw.line(self.screen, crack_col,
                             (cx2 + 12, cy2 + 20), (cx3 + 10, cy3), 1)

        # Cliff-face pine accents
        for tx, ty2 in [(430, 430), (400, 470), (460, 370), (490, 310),
                        (535, 255), (585, 200), (628, 165), (665, 140)]:
            th = 45 + ((tx * 3) % 20)
            pygame.draw.polygon(self.screen, (22, 68, 22),
                                [(tx, ty2 - th), (tx - 11, ty2), (tx + 11, ty2)])
            pygame.draw.polygon(self.screen, (18, 55, 18),
                                [(tx, ty2 - th + 12), (tx - 8, ty2 + 6), (tx + 8, ty2 + 6)])

        # --- MONASTERY LEDGE ---
        bx, by = 600, 190   # anchor of monastery cluster
        pygame.draw.polygon(self.screen, (120, 110, 92),
                            [(bx - 30, by + 180), (bx + 290, by + 180),
                             (bx + 310, by + 200), (bx - 50, by + 200)])

        # Helper: draw a Bhutanese building section
        def bhutan_building(x, y, w, h, wall=(238, 232, 220), roof=(95, 45, 28)):
            # White wall
            pygame.draw.rect(self.screen, wall, (x, y, w, h))
            pygame.draw.rect(self.screen, (180, 175, 165), (x, y, w, h), 1)
            # Red band just below roof
            pygame.draw.rect(self.screen, (155, 48, 30), (x, y, w, 10))
            # Curved upswept roof
            roof_pts = [(x - 8, y + 8), (x + w // 2, y - 20), (x + w + 8, y + 8)]
            pygame.draw.polygon(self.screen, roof, roof_pts)
            pygame.draw.polygon(self.screen, (130, 70, 40), roof_pts, 2)
            # Gold roof ridge
            pygame.draw.line(self.screen, GOLD, (x, y + 8), (x + w, y + 8), 2)

        # Building A — main temple (largest)
        bhutan_building(bx, by, 140, 130)
        # Windows A
        for wx in [bx + 18, bx + 58, bx + 98]:
            pygame.draw.rect(self.screen, (65, 48, 32), (wx, by + 28, 20, 24), border_radius=3)
            pygame.draw.rect(self.screen, GOLD, (wx, by + 28, 20, 24), 1, border_radius=3)
            pygame.draw.line(self.screen, GOLD, (wx, by + 28), (wx + 20, by + 28), 1)
        # Door A
        pygame.draw.rect(self.screen, (55, 38, 20), (bx + 55, by + 95, 30, 35), border_radius=4)
        pygame.draw.rect(self.screen, GOLD, (bx + 55, by + 95, 30, 35), 1, border_radius=4)

        # Building B — left wing (medium)
        bhutan_building(bx - 80, by + 45, 85, 100)
        for wx in [bx - 70, bx - 42]:
            pygame.draw.rect(self.screen, (65, 48, 32), (wx, by + 72, 18, 22), border_radius=2)
            pygame.draw.rect(self.screen, GOLD, (wx, by + 72, 18, 22), 1, border_radius=2)

        # Building C — right tower (tall narrow)
        bhutan_building(bx + 148, by + 20, 65, 150, wall=(232, 226, 214))
        # Extra upper tier
        bhutan_building(bx + 158, by - 15, 45, 40, wall=(240, 234, 222))
        for wx in [bx + 153, bx + 178]:
            pygame.draw.rect(self.screen, (65, 48, 32), (wx, by + 50, 14, 18), border_radius=2)

        # Building D — small shrine (far left on ledge)
        bhutan_building(bx - 160, by + 90, 60, 75)
        pygame.draw.rect(self.screen, (65, 48, 32), (bx - 143, by + 118, 14, 18), border_radius=2)

        # Gold finials / pinnacles on roofs
        for fx, fy in [(bx + 70, by - 22), (bx - 38, by + 23),
                       (bx + 180, by - 2), (bx - 130, by + 68)]:
            pygame.draw.polygon(self.screen, GOLD,
                                [(fx, fy - 14), (fx - 4, fy), (fx + 4, fy)])
            pygame.draw.circle(self.screen, GOLD, (fx, fy - 14), 3)

        # --- PRAYER FLAGS strung between buildings ---
        flag_cols = [RED, (0, 100, 200), WHITE, (0, 170, 0), YELLOW]
        rope_pts = [(bx - 180, by + 75), (bx - 90, by + 55), (bx + 70, by - 15),
                    (bx + 215, by + 18)]
        for i in range(len(rope_pts) - 1):
            pygame.draw.line(self.screen, (120, 100, 80), rope_pts[i], rope_pts[i + 1], 1)
        flag_count = 0
        for si in range(len(rope_pts) - 1):
            x1, y1 = rope_pts[si]
            x2, y2 = rope_pts[si + 1]
            steps = 5
            for fi in range(steps):
                frac = fi / steps
                fx = int(x1 + (x2 - x1) * frac)
                fy = int(y1 + (y2 - y1) * frac)
                sway = math.sin(t / 550 + flag_count) * 4
                fc = flag_cols[flag_count % len(flag_cols)]
                pygame.draw.polygon(self.screen, fc,
                                    [(fx, fy), (fx + 16, fy + sway),
                                     (fx + 16, fy + 12 + sway), (fx, fy + 12)])
                flag_count += 1

        # --- MIST / FOG drifting across scene ---
        mist = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        mist_speed = (t // 25) % SCREEN_WIDTH
        for mi in range(4):
            mx = (mi * 380 + mist_speed) % SCREEN_WIDTH
            my = 360 + mi * 35
            mw = 420 + mi * 80
            alpha = 32 + mi * 10
            pygame.draw.ellipse(mist, (255, 255, 255, alpha),
                                (mx - mw // 2, my, mw, 55))
            if mx - mw // 2 < 0:
                pygame.draw.ellipse(mist, (255, 255, 255, alpha),
                                    (mx - mw // 2 + SCREEN_WIDTH, my, mw, 55))
        # Soft light rays from upper-right sky
        for ri in range(5):
            ray = [(880 + ri * 18, 0), (900 + ri * 18, 0),
                   (580 + ri * 25, 430), (558 + ri * 25, 430)]
            pygame.draw.polygon(mist, (255, 252, 200, 14), ray)
        self.screen.blit(mist, (0, 0))

    def draw_background(self):
        self.draw_forest_background()

    def draw_exploration_atmosphere(self):
        atmosphere = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        horizon_color = {
            TimeOfDay.DAWN: (255, 180, 110, 18),
            TimeOfDay.DAY: (255, 245, 190, 10),
            TimeOfDay.DUSK: (185, 105, 75, 24),
            TimeOfDay.NIGHT: (30, 50, 105, 34),
        }[self.time_of_day]
        pygame.draw.rect(atmosphere, horizon_color, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        for index in range(5):
            x = 110 + index * 250
            pygame.draw.polygon(
                atmosphere,
                (255, 245, 195, 8),
                [(x, 0), (x + 42, 0), (x + 205, SCREEN_HEIGHT), (x + 145, SCREEN_HEIGHT)],
            )
        edge = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(edge, (4, 13, 18, 42), edge.get_rect(), 26)
        atmosphere.blit(edge, (0, 0))
        self.screen.blit(atmosphere, (0, 0))
        
    def draw_exploration_ui(self):
        if self.explorer is None or self.current_district is None:
            return
        stats_panel = pygame.Surface((335, 142), pygame.SRCALPHA)
        stats_panel.fill((5, 18, 25, 190))
        pygame.draw.rect(stats_panel, (214, 177, 84, 210), stats_panel.get_rect(), 2, border_radius=12)
        self.screen.blit(stats_panel, (10, 8))

        xp_width = 300
        xp_height = 16
        xp_x = 20
        xp_y = 70
        
        pygame.draw.rect(self.screen, (22, 38, 43), (xp_x, xp_y, xp_width, xp_height), border_radius=8)
        pygame.draw.rect(self.screen, (95, 118, 116), (xp_x, xp_y, xp_width, xp_height), 1, border_radius=8)
        xp_percent = self.explorer.xp / max(1, self.explorer.xp_to_next_level)
        pygame.draw.rect(self.screen, GOLD, (xp_x, xp_y, int(xp_width * xp_percent), xp_height), border_radius=8)
        pygame.draw.line(self.screen, (255, 242, 170), (xp_x + 5, xp_y + 3), (xp_x + max(5, int(xp_width * xp_percent) - 5), xp_y + 3), 1)
        
        xp_text = self.small_font.render(f"Lv.{self.explorer.level} XP:{self.explorer.xp}/{self.explorer.xp_to_next_level}", True, WHITE)
        self.screen.blit(xp_text, (xp_x + 10, xp_y - 18))
        
        knowledge_width = 300
        knowledge_height = 15
        knowledge_x = 20
        knowledge_y = 100
        
        pygame.draw.rect(self.screen, (22, 38, 43), (knowledge_x, knowledge_y, knowledge_width, knowledge_height), border_radius=8)
        pygame.draw.rect(self.screen, (95, 118, 116), (knowledge_x, knowledge_y, knowledge_width, knowledge_height), 1, border_radius=8)
        knowledge_percent = min(1.0, self.explorer.knowledge / max(1, self.current_district.get("required_knowledge", 70)))
        pygame.draw.rect(self.screen, CYAN, (knowledge_x, knowledge_y, int(knowledge_width * knowledge_percent), knowledge_height), border_radius=8)
        pygame.draw.line(self.screen, (190, 255, 255), (knowledge_x + 5, knowledge_y + 3), (knowledge_x + max(5, int(knowledge_width * knowledge_percent) - 5), knowledge_y + 3), 1)
        
        knowledge_text = self.small_font.render(f"Knowledge: {self.explorer.knowledge}/{self.current_district.get('required_knowledge', 70)}", True, WHITE)
        self.screen.blit(knowledge_text, (knowledge_x + 10, knowledge_y - 18))
        
        visited_count = sum(1 for poi in self.points_of_interest if poi.visited)
        total_sites = max(1, len(self.points_of_interest))
        progress_text = self.small_font.render(f"📍 Sites:{visited_count}/{total_sites}", True, GOLD)
        self.screen.blit(progress_text, (SCREEN_WIDTH//2 - 80, 58))
        
        secrets_found = sum(1 for s in self.hidden_discoveries if s.discovered)
        total_secrets = max(1, len(self.hidden_discoveries))
        secrets_text = self.small_font.render(f"🔍 Secrets:{secrets_found}/{total_secrets}", True, YELLOW)
        self.screen.blit(secrets_text, (SCREEN_WIDTH//2 - 80, 83))
        
        hint_panel = pygame.Surface((760, 30), pygame.SRCALPHA)
        hint_panel.fill((5, 18, 25, 185))
        pygame.draw.rect(hint_panel, (214, 177, 84, 160), hint_panel.get_rect(), 1, border_radius=10)
        self.screen.blit(hint_panel, hint_panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)))
        inst_text = self.small_font.render("WASD Move  |  P Photo  |  I Skills  |  Approach sites  |  Talk to monks  |  ESC Pause", True, WHITE)
        inst_rect = inst_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 18))
        self.screen.blit(inst_text, inst_rect)
        
        all_pois_visited = all(poi.visited for poi in self.points_of_interest)
        enough_knowledge = self.explorer.knowledge >= self.current_district.get("required_knowledge", 70)
        if all_pois_visited and enough_knowledge and not self.exploration_complete:
            self.exploration_complete = True
            self.complete_district()
            
    def complete_district(self):
        if self.current_district is None or self.explorer is None:
            return
        district_name = self.current_district["name"]
        if district_name not in self.completed_districts:
            self.completed_districts.append(district_name)
            self.update_completion_status()
            self.explorer.add_xp(200)
            self.explorer.wisdom += 25
            self.reputation.modify(15)
            self.save_game()
            self.raid_enemy_health = 1
            self.enemies = [
                RaiderEnemy(
                    self.explorer.x + math.cos(angle) * 500,
                    self.explorer.y + math.sin(angle) * 500,
                    self.enemy_image,
                )
                for angle in [
                    random.uniform(0, 2 * math.pi)
                    for _ in range(random.randint(4, 5))
                ]
            ]
            self.raid_feedback = ""
            self.raid_feedback_timer = 0
            self.cultural_quiz_questions = self.build_cultural_quiz()
            self.cultural_quiz_index = 0
            self.cultural_quiz_score = 0
            self.current_cultural_quiz = self.cultural_quiz_questions[0]
            self.state = GameState.RAID

    def build_cultural_quiz(self):
        if self.current_district is None:
            return []
        return [
            {"question": question, "options": options, "answer": answer}
            for question, options, answer in CULTURAL_QUIZ_DATA.get(self.current_district["name"], [])
        ]
        quiz_data = {
            "Thimphu": [
                ("Which site is the main seat of Bhutan's government and central monastic body?", ["Tango Monastery", "Tashichho Dzong", "Changangkha Lhakhang", "Memorial Chorten"], "Tashichho Dzong"),
                ("Which site is famous for its large statue of Guru Rinpoche?", ["Buddha Dordenma", "Tango Monastery", "Tashichho Dzong", "Memorial Chorten"], "Buddha Dordenma"),
                ("Which site is a famous stupa in the heart of Thimphu?", ["Changangkha Lhakhang", "Memorial Chorten", "Tango Monastery", "Buddha Dordenma"], "Memorial Chorten"),
            ],
            "Paro": [
                ("Which monastery is famously located on a cliff?", ["Kyichu Lhakhang", "Rinpung Dzong", "Taktsang Monastery", "Ta Dzong"], "Taktsang Monastery"),
                ("Which dzong is also known as Paro Dzong?", ["Rinpung Dzong", "Drukgyel Dzong", "Ta Dzong", "Kyichu Lhakhang"], "Rinpung Dzong"),
                ("Which site was built as a watchtower and now houses the National Museum?", ["Taktsang Monastery", "Ta Dzong", "Drukgyel Dzong", "Rinpung Dzong"], "Ta Dzong"),
            ],
            "Punakha": [
                ("Which famous dzong stands at the meeting point of two rivers?", ["Chimi Lhakhang", "Nalanda Buddhist College", "Punakha Dzong", "Khamsum Yulley Namgyal Chorten"], "Punakha Dzong"),
                ("Which site is associated with the Divine Madman?", ["Chimi Lhakhang", "Punakha Dzong", "Nalanda Buddhist College", "Khamsum Yulley Namgyal Chorten"], "Chimi Lhakhang"),
                ("Which site is a famous four-storey chorten overlooking the Punakha valley?", ["Punakha Dzong", "Khamsum Yulley Namgyal Chorten", "Chimi Lhakhang", "Nalanda Buddhist College"], "Khamsum Yulley Namgyal Chorten"),
            ],
            "Bumthang": [
                ("Which dzong is located in the Bumthang valley?", ["Jakar Dzong", "Tamshing Lhakhang", "Jampa Lhakhang", "Membartsho"], "Jakar Dzong"),
                ("Which site is known as the Burning Lake?", ["Kurjey Lhakhang", "Membartsho", "Tamshing Lhakhang", "Jampa Lhakhang"], "Membartsho"),
                ("Which lhakhang is one of the oldest temples in Bhutan?", ["Jampa Lhakhang", "Jakar Dzong", "Membartsho", "Kurjey Lhakhang"], "Jampa Lhakhang"),
            ],
            "Wangdue Phodrang": [
                ("Which dzong is the main historical fortress of Wangdue Phodrang?", ["Gangtey Monastery", "Wangdue Phodrang Dzong", "Rinchengang Village", "Phobjikha Valley"], "Wangdue Phodrang Dzong"),
                ("Which valley is famous for black-necked cranes?", ["Phobjikha Valley", "Rinchengang Village", "Gangtey Monastery", "Wangdue Phodrang Dzong"], "Phobjikha Valley"),
                ("Which monastery is located in the Phobjikha Valley?", ["Rinchengang Village", "Wangdue Phodrang Dzong", "Gangtey Monastery", "Phobjikha Valley"], "Gangtey Monastery"),
            ],
            "Trongsa": [
                ("Which is the famous fortress of Trongsa?", ["Kuenga Rabten Palace", "Chendebji Chorten", "Trongsa Dzong", "Ta Dzong"], "Trongsa Dzong"),
                ("Which site is a historical palace associated with the Wangchuck dynasty?", ["Kuenga Rabten Palace", "Trongsa Dzong", "Ta Dzong", "Chendebji Chorten"], "Kuenga Rabten Palace"),
                ("Which site is a famous chorten on the road between Trongsa and Wangdue?", ["Ta Dzong", "Chendebji Chorten", "Trongsa Dzong", "Kuenga Rabten Palace"], "Chendebji Chorten"),
            ],
            "Trashigang": [
                ("Which dzong is a major historical landmark of Trashigang?", ["Gom Kora", "Bartsham Lhakhang", "Trashigang Dzong", "Drametse Monastery"], "Trashigang Dzong"),
                ("Which site is famous for the Drametse Ngacham dance?", ["Drametse Monastery", "Gom Kora", "Bartsham Lhakhang", "Trashigang Dzong"], "Drametse Monastery"),
                ("Which sanctuary is known for its rich wildlife and highland landscapes?", ["Gom Kora", "Merak Sakteng Wildlife Sanctuary", "Drametse Monastery", "Bartsham Lhakhang"], "Merak Sakteng Wildlife Sanctuary"),
            ],
            "Mongar": [
                ("Which is the main dzong of Mongar?", ["Mongar Dzong", "Ngatshang Gonpa", "Lhungtenzampa Bridge", "Bumdeling Wildlife Sanctuary"], "Mongar Dzong"),
                ("Which site is a famous bridge in Mongar?", ["Ngatshang Gonpa", "Bumdeling Wildlife Sanctuary", "Lhungtenzampa Bridge", "Mongar Dzong"], "Lhungtenzampa Bridge"),
                ("Which site is associated with wildlife conservation?", ["Mongar Dzong", "Ngatshang Gonpa", "Lhungtenzampa Bridge", "Bumdeling Wildlife Sanctuary"], "Bumdeling Wildlife Sanctuary"),
            ],
            "Lhuentse": [
                ("Which dzong is the administrative and historical landmark of Lhuentse?", ["Khoma Village", "Lhuentse Dzong", "Tangmachu Lhakhang", "Gangzur Village"], "Lhuentse Dzong"),
                ("Which village is famous for traditional weaving?", ["Gangzur Village", "Khoma Village", "Tangmachu Lhakhang", "Lhuentse Dzong"], "Khoma Village"),
                ("Which village is known for traditional pottery?", ["Lhuentse Dzong", "Tangmachu Lhakhang", "Gangzur Village", "Khoma Village"], "Gangzur Village"),
            ],
            "Trashi Yangtse": [
                ("Which famous chorten is located in Trashi Yangtse?", ["Rigsum Gonpa", "Chorten Kora", "Bumdeling Valley", "Trashi Yangtse Dzong"], "Chorten Kora"),
                ("Which site is the main dzong of Trashi Yangtse?", ["Chorten Kora", "Bumdeling Valley", "Trashi Yangtse Dzong", "Rigsum Gonpa"], "Trashi Yangtse Dzong"),
                ("Which area is known for its natural landscape and wildlife?", ["Chorten Kora", "Rigsum Gonpa", "Trashi Yangtse Dzong", "Bumdeling Valley"], "Bumdeling Valley"),
            ],
            "Samdrup Jongkhar": [
                ("Which temple is a famous landmark of Samdrup Jongkhar?", ["Zangtopelri Temple", "Gomtu Trade Market", "Daifam Wildlife Sanctuary", "Samdrup Jongkhar Dzong"], "Zangtopelri Temple"),
                ("Which site is associated with trade and commerce?", ["Daifam Wildlife Sanctuary", "Gomtu Trade Market", "Zangtopelri Temple", "Samdrup Jongkhar Dzong"], "Gomtu Trade Market"),
                ("Which site is connected with wildlife conservation?", ["Samdrup Jongkhar Dzong", "Zangtopelri Temple", "Daifam Wildlife Sanctuary", "Gomtu Trade Market"], "Daifam Wildlife Sanctuary"),
            ],
            "Pemagatshel": [
                ("Which monastery is an important landmark of Pemagatshel?", ["Khar Monastery", "Chaling Village", "Yongla Gonpa", "Pemagatshel Dzong"], "Khar Monastery"),
                ("Which is the main dzong of Pemagatshel?", ["Yongla Gonpa", "Pemagatshel Dzong", "Khar Monastery", "Chaling Village"], "Pemagatshel Dzong"),
                ("Which of these is a village in Pemagatshel?", ["Yongla Gonpa", "Khar Monastery", "Chaling Village", "Pemagatshel Dzong"], "Chaling Village"),
            ],
            "Chukha": [
                ("Which site is the main dzong of Chukha?", ["Rinchending Goenpa", "Chukha Dzong", "Phuntsholing Market", "Chukha Hydropower Dam"], "Chukha Dzong"),
                ("Which site is related to hydropower production?", ["Chukha Hydropower Dam", "Chukha Dzong", "Rinchending Goenpa", "Phuntsholing Market"], "Chukha Hydropower Dam"),
                ("Which site is known as a busy commercial area?", ["Chukha Dzong", "Rinchending Goenpa", "Phuntsholing Market", "Chukha Hydropower Dam"], "Phuntsholing Market"),
            ],
            "Haa": [
                ("Which site is known as the White Temple?", ["Kila Nunnery", "Lhakhang Nagpo", "Lhakhang Karpo", "Haa Summer Festival Grounds"], "Lhakhang Karpo"),
                ("Which site is known as the Black Temple?", ["Lhakhang Nagpo", "Lhakhang Karpo", "Kila Nunnery", "Haa Summer Festival Grounds"], "Lhakhang Nagpo"),
                ("Which site is a nunnery located in the mountains?", ["Lhakhang Karpo", "Kila Nunnery", "Lhakhang Nagpo", "Haa Summer Festival Grounds"], "Kila Nunnery"),
            ],
            "Gasa": [
                ("Which site is famous for its natural hot springs?", ["Laya Village", "Gasa Dzong", "Gasa Hot Springs", "Snowman Trek Route"], "Gasa Hot Springs"),
                ("Which village is a famous high-altitude settlement?", ["Gasa Hot Springs", "Laya Village", "Gasa Dzong", "Snowman Trek Route"], "Laya Village"),
                ("Which route is famous as a challenging Himalayan trek?", ["Gasa Dzong", "Laya Village", "Gasa Hot Springs", "Snowman Trek Route"], "Snowman Trek Route"),
            ],
            "Sarpang": [
                ("Which national park is located partly in Sarpang?", ["Royal Manas National Park", "Jigme Singye Wangchuck National Park", "Bumdeling Wildlife Sanctuary", "Daifam Wildlife Sanctuary"], "Royal Manas National Park"),
                ("Which site is associated with Bhutan's new planned urban development?", ["Sarpang Dzong", "Tingtibi Village", "Gelephu Mindfulness City Site", "Royal Manas National Park"], "Gelephu Mindfulness City Site"),
                ("Which is the main dzong of Sarpang?", ["Tingtibi Village", "Sarpang Dzong", "Royal Manas National Park", "Gelephu Mindfulness City Site"], "Sarpang Dzong"),
            ],
            "Tsirang": [
                ("Which is the main dzong of Tsirang?", ["Damphu Dzong", "Kikorthang Market", "Patale Viewpoint", "Tsirangtoe Monastery"], "Damphu Dzong"),
                ("Which site is a market in Tsirang?", ["Tsirangtoe Monastery", "Damphu Dzong", "Kikorthang Market", "Patale Viewpoint"], "Kikorthang Market"),
                ("Which site is known as a viewpoint?", ["Patale Viewpoint", "Damphu Dzong", "Tsirangtoe Monastery", "Kikorthang Market"], "Patale Viewpoint"),
            ],
            "Dagana": [
                ("Which is the main dzong of Dagana?", ["Lawa Monastery", "Dagana Dzong", "Khipisa Viewpoint", "Jigme Singye Wangchuck National Park"], "Dagana Dzong"),
                ("Which site is a national park?", ["Lawa Monastery", "Khipisa Viewpoint", "Dagana Dzong", "Jigme Singye Wangchuck National Park"], "Jigme Singye Wangchuck National Park"),
                ("Which site provides scenic views of the surrounding area?", ["Khipisa Viewpoint", "Dagana Dzong", "Lawa Monastery", "Jigme Singye Wangchuck National Park"], "Khipisa Viewpoint"),
            ],
            "Samtse": [
                ("Which is the main dzong of Samtse?", ["Dorokha Village", "Chargharey Lhakhang", "Samtse Dzong", "Samtse Tea Estate"], "Samtse Dzong"),
                ("Which site is associated with tea production?", ["Samtse Tea Estate", "Samtse Dzong", "Dorokha Village", "Chargharey Lhakhang"], "Samtse Tea Estate"),
                ("Which of these is a village?", ["Samtse Dzong", "Dorokha Village", "Samtse Tea Estate", "Chargharey Lhakhang"], "Dorokha Village"),
            ],
            "Zhemgang": [
                ("Which is the main dzong of Zhemgang?", ["Ngang Lhakhang", "Phumzur Village", "Zhemgang Dzong", "Kheng Heritage Trail"], "Zhemgang Dzong"),
                ("Which site is a heritage trail?", ["Ngang Lhakhang", "Kheng Heritage Trail", "Phumzur Village", "Zhemgang Dzong"], "Kheng Heritage Trail"),
                ("Which of these is a village in Zhemgang?", ["Phumzur Village", "Zhemgang Dzong", "Ngang Lhakhang", "Kheng Heritage Trail"], "Phumzur Village"),
            ],
        }
        return [
            {"question": question, "options": options, "answer": answer}
            for question, options, answer in quiz_data.get(self.current_district["name"], [])
        ]

    def handle_raid(self):
        if self.explorer is None or not self.enemies or not self.cultural_quiz_questions:
            self.state = GameState.LEVEL_SELECT
            return

        for raider in self.enemies:
            raider.move_toward(self.explorer.x, self.explorer.y)
        distance = min(
            math.hypot(raider.x - self.explorer.x, raider.y - self.explorer.y)
            for raider in self.enemies
        )

        self.screen.fill(self.time_of_day.ambient_color)
        self.draw_terrain_with_forest()
        for poi in self.points_of_interest:
            poi.draw(self.screen, self.camera_x, self.camera_y)
        for monk in self.monks:
            monk.draw(self.screen, self.camera_x, self.camera_y)
        for raider in self.enemies:
            raider.draw(self.screen, self.camera_x, self.camera_y)
        self.explorer.draw(self.screen, self.camera_x, self.camera_y)

        if distance > 55:
            chase_text = self.font.render("A raider is approaching!", True, RED)
            self.screen.blit(chase_text, chase_text.get_rect(center=(SCREEN_WIDTH // 2, 55)))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
        else:
            panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 370, 70, 740, 560)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            self.screen.blit(overlay, (0, 0))
            pygame.draw.rect(self.screen, (35, 15, 15), panel_rect, border_radius=20)
            pygame.draw.rect(self.screen, DARK_RED, panel_rect, 4, border_radius=20)
            question_number = self.cultural_quiz_index + 1
            total_questions = len(self.cultural_quiz_questions)
            title = self.big_font.render(f"Sacred District Quiz {question_number}/{total_questions}", True, GOLD)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 115)))
            enemy_text = self.font.render("Answer to complete the district", True, WHITE)
            self.screen.blit(enemy_text, enemy_text.get_rect(center=(SCREEN_WIDTH // 2, 170)))
            question_lines = wrap_text(self.current_cultural_quiz["question"], self.font, 620)
            for index, line in enumerate(question_lines[:2]):
                question_text = self.font.render(line, True, YELLOW)
                self.screen.blit(question_text, question_text.get_rect(center=(SCREEN_WIDTH // 2, 220 + index * 32)))

            option_rects = []
            for index, option in enumerate(self.current_cultural_quiz["options"]):
                rect = pygame.Rect(SCREEN_WIDTH // 2 - 280, 295 + index * 55, 560, 45)
                pygame.draw.rect(self.screen, (55, 20, 20), rect, border_radius=10)
                pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=10)
                option_text = self.small_font.render(f"{chr(65 + index)}. {option}", True, WHITE)
                self.screen.blit(option_text, option_text.get_rect(center=rect.center))
                option_rects.append((rect, option))

            if self.raid_feedback_timer > 0:
                self.raid_feedback_timer -= 1
                feedback = self.small_font.render(self.raid_feedback, True, self.raid_feedback_color)
                self.screen.blit(feedback, feedback.get_rect(center=(SCREEN_WIDTH // 2, 575)))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, option in option_rects:
                        if rect.collidepoint(event.pos):
                            if option == self.current_cultural_quiz["answer"]:
                                self.cultural_quiz_score += 1
                                self.explorer.add_xp(100)
                                self.explorer.wisdom += 25
                                self.save_game()
                                if self.cultural_quiz_index + 1 < len(self.cultural_quiz_questions):
                                    self.cultural_quiz_index += 1
                                    self.current_cultural_quiz = self.cultural_quiz_questions[self.cultural_quiz_index]
                                    self.raid_feedback = "Correct! Next question."
                                    self.raid_feedback_color = GREEN
                                    self.raid_feedback_timer = 90
                                else:
                                    self.show_completion_certificate()
                                    self.map_selected_district = None
                                    self.state = GameState.BHUTAN_MAP
                            else:
                                self.raid_feedback = "Wrong answer. Try again!"
                                self.raid_feedback_color = RED
                                self.raid_feedback_timer = 120
                            break

        pygame.display.flip()
            
    def handle_main_menu(self):
        self.draw_menu_background()

        if self.show_menu_guide:
            guide_rect = pygame.Rect(250, 105, 700, 490)
            pygame.draw.rect(self.screen, (15, 30, 35), guide_rect, border_radius=16)
            pygame.draw.rect(self.screen, GOLD, guide_rect, 3, border_radius=16)
            guide_title = self.big_font.render("How to Explore Bhutan", True, GOLD)
            self.screen.blit(guide_title, guide_title.get_rect(center=(SCREEN_WIDTH // 2, 155)))
            guide_lines = [
                "Choose a district on the Bhutan map to begin.",
                "Use WASD or the arrow keys to move your explorer.",
                "Visit every marked site and collect knowledge.",
                "Talk to monks and discover hidden secrets.",
                "Press P to take a photo and I to view your skills.",
                "Complete the cultural challenge to master a district.",
            ]
            for index, line in enumerate(guide_lines):
                guide_text = self.small_font.render(line, True, WHITE)
                self.screen.blit(guide_text, (guide_rect.x + 45, 205 + index * 42))
            dismiss_text = self.small_font.render("Click or press any key to return", True, (210, 210, 210))
            self.screen.blit(dismiss_text, dismiss_text.get_rect(center=(SCREEN_WIDTH // 2, 555)))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self.show_menu_guide = False
            pygame.display.flip()
            return
        
        title_y = 150 + math.sin(pygame.time.get_ticks() / 1000) * 5
        title = self.title_font.render("THREADS OF TIME", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, title_y))
        
        shadow = self.title_font.render("THREADS OF TIME", True, BLACK)
        shadow_rect = shadow.get_rect(center=(SCREEN_WIDTH//2 + 3, title_y + 3))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(title, title_rect)
        
        subtitle = self.small_font.render("A Journey Through Time", True, WHITE)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH//2, title_y + 55))
        self.screen.blit(subtitle, subtitle_rect)
        
        menu_items = ["NEW GAME", "GUIDE", "QUIT"]
        menu_y = 350
        hovered_item = None
        
        mouse_pos = pygame.mouse.get_pos()
        for i, item in enumerate(menu_items):
            text = self.big_font.render(item, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, menu_y + i * 70))
            if text_rect.collidepoint(mouse_pos):
                hovered_item = i
                pygame.draw.rect(self.screen, GOLD, text_rect.inflate(20, 10), 3, border_radius=10)
                
        for i, item in enumerate(menu_items):
            color = GOLD if hovered_item == i else WHITE
            text = self.big_font.render(item, True, color)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, menu_y + i * 70))
            self.screen.blit(text, text_rect)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for i, item in enumerate(menu_items):
                        text = self.big_font.render(item, True, WHITE)
                        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, menu_y + i * 70))
                        if text_rect.collidepoint(mouse_pos):
                            if item == "NEW GAME":
                                self.clear_save()
                                self.completed_districts = []
                                self.state = GameState.CHARACTER_CUSTOMIZATION
                            elif item == "GUIDE":
                                self.show_menu_guide = True
                            elif item == "QUIT":
                                self.running = False
                                
        pygame.display.flip()
        
    def handle_character_customization(self):
        self.draw_menu_background()

        # ── Layout constants ────────────────────────────────────────────────
        # Left panel: character preview  (x 40-290)
        # Right panel: all controls      (x 310-1160, centred at 735)
        PANEL_CX  = 735        # horizontal centre of the control column
        PREV_CX   = 165        # horizontal centre of the preview panel

        # ── Defaults ────────────────────────────────────────────────────────
        if hasattr(self, 'saved_explorer_data') and self.saved_explorer_data:
            default_name = self.saved_explorer_data["name"]
            saved_class = self.saved_explorer_data.get("class_name", "Custom Explorer")
            self.selected_class = saved_class if saved_class in CHARACTER_CLASSES else "Custom Explorer"
        else:
            default_name = "Explorer"

        default_color = CHARACTER_CLASSES[self.selected_class]["color"]
        default_hat = CHARACTER_CLASSES[self.selected_class]["hat"]
        self.selected_color = default_color
        self.selected_hat = default_hat

        display_name = self.name_input if self.name_input else default_name
        if self.input_active and pygame.time.get_ticks() // 500 % 2 == 0:
            display_name += "|"

        panel_rect = pygame.Rect(30, 80, 270, 560)
        panel_surf = pygame.Surface((270, 560), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 140))
        self.screen.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(self.screen, GOLD, panel_rect, 2, border_radius=12)

        pl_title = self.small_font.render("Preview", True, GOLD)
        self.screen.blit(pl_title, (PREV_CX - pl_title.get_width()//2, 90))

        S = self.screen
        preview_y = 160
        accent = default_color
        preview_source = self.horse_preview_sprite if self.selected_class == "Horse" else self.preview_sprite
        if preview_source:
            content = preview_source.get_bounding_rect()
            preview_sprite = preview_source.subsurface(content)
            preview_height = 128 if self.selected_class != "Horse" else 150
            preview_width = int(preview_sprite.get_width() * preview_height / preview_sprite.get_height())
            preview_sprite = pygame.transform.scale(preview_sprite, (preview_width, preview_height))
            preview_rect = preview_sprite.get_rect(center=(PREV_CX, preview_y + 54))
            S.blit(preview_sprite, preview_rect)

        nf_prev = pygame.font.Font(None, 22)
        nm_prev = nf_prev.render(display_name[:16], True, WHITE)
        self.screen.blit(nm_prev, (PREV_CX - nm_prev.get_width()//2, preview_y + 118))

        swatch_y = preview_y + 148
        swatch_r = pygame.Rect(PREV_CX - 40, swatch_y, 80, 18)
        pygame.draw.rect(self.screen, accent, swatch_r, border_radius=5)
        pygame.draw.rect(self.screen, WHITE, swatch_r, 1, border_radius=5)

        title = self.big_font.render("Create Your Explorer", True, GOLD)
        self.screen.blit(title, (PANEL_CX - title.get_width()//2, 28))

        sub = self.small_font.render("Name your traveler", True, (210, 210, 210))
        self.screen.blit(sub, (PANEL_CX - sub.get_width()//2, 72))

        name_label = self.font.render("Enter your name:", True, WHITE)
        self.screen.blit(name_label, (PANEL_CX - name_label.get_width()//2, 108))

        name_box = pygame.Rect(PANEL_CX - 160, 138, 320, 46)
        box_col = (100, 100, 150) if self.input_active else (50, 50, 80)
        pygame.draw.rect(self.screen, box_col, name_box, border_radius=8)
        pygame.draw.rect(self.screen, GOLD, name_box, 2, border_radius=8)
        name_text = self.small_font.render(display_name[:22], True, WHITE)
        name_rect = name_text.get_rect(center=name_box.center)
        self.screen.blit(name_text, name_rect)

        xp_available = 0
        if hasattr(self, 'saved_explorer_data') and self.saved_explorer_data:
            xp_available = self.saved_explorer_data.get("xp", 0)
        elif self.explorer:
            xp_available = self.explorer.xp

        xp_text = self.small_font.render(f"Available XP: {xp_available}", True, GOLD)
        self.screen.blit(xp_text, (PANEL_CX - xp_text.get_width()//2, 192))

        song_shop_button = pygame.Rect(PANEL_CX - 120, 245, 240, 44)
        pygame.draw.rect(self.screen, (70, 50, 120), song_shop_button, border_radius=10)
        pygame.draw.rect(self.screen, GOLD, song_shop_button, 2, border_radius=10)
        song_shop_text = self.small_font.render("♪  Song Shop", True, WHITE)
        self.screen.blit(song_shop_text, song_shop_text.get_rect(center=song_shop_button.center))

        start_button = pygame.Rect(PANEL_CX - 115, 634, 230, 48)
        button_color = (0, 130, 60) if len(self.name_input.strip()) > 0 else (80, 80, 80)
        pygame.draw.rect(self.screen, button_color, start_button, border_radius=12)
        pygame.draw.rect(self.screen, WHITE, start_button, 2, border_radius=12)
        start_text = self.font.render("⚔  Begin Adventure", True, WHITE)
        start_rect = start_text.get_rect(center=start_button.center)
        self.screen.blit(start_text, start_rect)

        if self.show_error:
            error_text = self.small_font.render("Please enter a name!", True, RED)
            error_rect = error_text.get_rect(center=(PANEL_CX, 610))
            self.screen.blit(error_text, error_rect)
            self.error_timer += 1
            if self.error_timer > 120:
                self.show_error = False
                self.error_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if name_box.collidepoint(event.pos):
                        self.input_active = True
                    else:
                        self.input_active = False

                    if song_shop_button.collidepoint(event.pos):
                        self.state = GameState.SONG_SHOP
                        pygame.display.flip()
                        return

                    if start_button.collidepoint(event.pos):
                        final_name = self.name_input.strip()
                        if len(final_name) > 0:
                            if hasattr(self, 'saved_explorer_data') and self.saved_explorer_data:
                                self.explorer = Explorer(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, default_color, final_name, default_hat, self.selected_class)
                                self.explorer.knowledge = self.saved_explorer_data.get("knowledge", 0)
                                self.explorer.wisdom = self.saved_explorer_data.get("wisdom", 0)
                                self.explorer.level = self.saved_explorer_data.get("level", 1)
                                self.explorer.xp = self.saved_explorer_data.get("xp", 0)
                                self.explorer.completed_districts = self.completed_districts
                                delattr(self, 'saved_explorer_data')
                            else:
                                self.explorer = Explorer(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, default_color, final_name, default_hat, self.selected_class)
                            self.create_level_cards()
                            self.map_selected_district = None
                            self.state = GameState.BHUTAN_MAP
                        else:
                            self.show_error = True
                            self.error_timer = 0

            elif event.type == pygame.KEYDOWN:
                if self.input_active:
                    if event.key == pygame.K_RETURN:
                        final_name = self.name_input.strip()
                        if len(final_name) > 0:
                            if hasattr(self, 'saved_explorer_data') and self.saved_explorer_data:
                                self.explorer = Explorer(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, default_color, final_name, default_hat, self.selected_class)
                                self.explorer.knowledge = self.saved_explorer_data.get("knowledge", 0)
                                self.explorer.wisdom = self.saved_explorer_data.get("wisdom", 0)
                                self.explorer.level = self.saved_explorer_data.get("level", 1)
                                self.explorer.xp = self.saved_explorer_data.get("xp", 0)
                                self.explorer.completed_districts = self.completed_districts
                                delattr(self, 'saved_explorer_data')
                            else:
                                self.explorer = Explorer(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, default_color, final_name, default_hat, self.selected_class)
                            self.create_level_cards()
                            self.map_selected_district = None
                            self.state = GameState.BHUTAN_MAP
                        else:
                            self.show_error = True
                            self.error_timer = 0
                    elif event.key == pygame.K_BACKSPACE:
                        self.name_input = self.name_input[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MAIN_MENU
                    else:
                        if event.unicode and event.unicode.isprintable() and len(self.name_input) < 20:
                            self.name_input += event.unicode

        pygame.display.flip()

    def handle_song_shop(self):
        self.draw_menu_background()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("Song Shop", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))
        xp_text = self.small_font.render(f"Available XP: {self.available_song_xp()}", True, GOLD)
        self.screen.blit(xp_text, xp_text.get_rect(center=(SCREEN_WIDTH // 2, 108)))

        song_rects = []
        for index, song_key in enumerate(("world_music_day", "ling_sho_ray")):
            song = self.song_catalog[song_key]
            rect = pygame.Rect(220, 160 + index * 150, 760, 115)
            pygame.draw.rect(self.screen, (35, 45, 65), rect, border_radius=12)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=12)
            name = self.font.render(song["title"], True, WHITE)
            self.screen.blit(name, (rect.x + 28, rect.y + 18))
            status = "OWNED" if song_key in self.owned_songs else f"BUY FOR {song['cost']} XP"
            status_color = LIGHT_GREEN if song_key in self.owned_songs else YELLOW
            status_text = self.small_font.render(status, True, status_color)
            self.screen.blit(status_text, (rect.x + 28, rect.y + 62))
            song_rects.append((rect, song_key))

        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 110, 535, 220, 48)
        pygame.draw.rect(self.screen, (65, 65, 85), back_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, back_rect, 2, border_radius=10)
        back_text = self.small_font.render("Back", True, WHITE)
        self.screen.blit(back_text, back_text.get_rect(center=back_rect.center))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    self.state = GameState.CHARACTER_CUSTOMIZATION
                else:
                    for rect, song_key in song_rects:
                        if rect.collidepoint(event.pos):
                            self.buy_song(song_key)
                            break
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = GameState.CHARACTER_CUSTOMIZATION

        pygame.display.flip()
        
    def handle_level_select(self):
        self.draw_background()
        
        title = self.big_font.render("Select a Dzongkhag", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 60))
        self.screen.blit(title, title_rect)
        
        subtitle = self.small_font.render(f"Complete all 20 districts ({len(self.completed_districts)}/20 completed)", True, WHITE)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH//2, 100))
        self.screen.blit(subtitle, subtitle_rect)
        
        if self.explorer:
            level_panel = pygame.Rect(10, 10, 280, 70)
            pygame.draw.rect(self.screen, (0, 0, 0, 128), level_panel, border_radius=10)
            pygame.draw.rect(self.screen, GOLD, level_panel, 2, border_radius=10)
            
            level_text = self.small_font.render(f"🌿 {self.explorer.name} (Lv.{self.explorer.level})", True, WHITE)
            self.screen.blit(level_text, (20, 18))
            
            xp_text = self.small_font.render(f"XP: {self.explorer.xp}/{self.explorer.xp_to_next_level}", True, GOLD)
            self.screen.blit(xp_text, (20, 40))
            
            knowledge_text = self.small_font.render(f"Knowledge: {self.explorer.knowledge}", True, CYAN)
            self.screen.blit(knowledge_text, (20, 62))
            
            progress_width = 140
            progress_height = 12
            progress_x = SCREEN_WIDTH - 160
            progress_y = 45
            pygame.draw.rect(self.screen, GRAY, (progress_x, progress_y, progress_width, progress_height), border_radius=7)
            fill_width = (len(self.completed_districts) / 20) * progress_width
            pygame.draw.rect(self.screen, FOREST_GREEN, (progress_x, progress_y, fill_width, progress_height), border_radius=7)
            
        mouse_pos = pygame.mouse.get_pos()

        self.scroll_speed *= 0.9
        self.scroll_y += self.scroll_speed
        self.scroll_y = max(-400, min(self.scroll_y, 200))
        
        for card in self.level_cards:
            original_y = card.y
            card.y += self.scroll_y
            card.rect.y = card.y
            
            if -card.height < card.y < SCREEN_HEIGHT + card.height:
                card.draw(self.screen, mouse_pos)
                
            card.y = original_y
            card.rect.y = original_y
                
        back_button = pygame.Rect(10, SCREEN_HEIGHT - 50, 120, 40)
        pygame.draw.rect(self.screen, RED, back_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, back_button, 2, border_radius=8)
        back_text = self.font.render("Menu", True, WHITE)
        back_text_rect = back_text.get_rect(center=(70, SCREEN_HEIGHT - 30))
        self.screen.blit(back_text, back_text_rect)
        
        save_button = pygame.Rect(SCREEN_WIDTH - 130, SCREEN_HEIGHT - 50, 120, 40)
        pygame.draw.rect(self.screen, BLUE, save_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, save_button, 2, border_radius=8)
        save_text = self.font.render("Save", True, WHITE)
        save_text_rect = save_text.get_rect(center=(SCREEN_WIDTH - 70, SCREEN_HEIGHT - 30))
        self.screen.blit(save_text, save_text_rect)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEWHEEL:
                self.scroll_speed += event.y * 30
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click_pos = event.pos
                    for card in self.level_cards:
                        displayed_rect = card.rect.move(0, self.scroll_y)
                        if displayed_rect.collidepoint(click_pos):
                            self.selected_district_for_info = card.district_data
                            self.state = GameState.DISTRICT_INFO
                            break
                            
                    if back_button.collidepoint(click_pos):
                        self.save_game()
                        self.state = GameState.MAIN_MENU
                        
                    if save_button.collidepoint(click_pos):
                        if self.save_game():
                            self.draw_background()
                            confirmation = self.font.render("Game Saved!", True, GREEN)
                            conf_rect = confirmation.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
                            self.screen.blit(confirmation, conf_rect)
                            pygame.display.flip()
                            pygame.time.wait(500)
                            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.MAIN_MENU
                    
        pygame.display.flip()

    def show_captured_images(self):
        viewing_images = True
        while viewing_images and self.running:
            self.screen.fill((18, 20, 24))
            title = self.big_font.render("Captured Images", True, GOLD)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 38)))

            captured_images = [
                self.landmark_images[landmark_name]
                for _, landmark_name in self.photo_journal.photos
                if landmark_name in self.landmark_images
            ]
            if not captured_images:
                empty_text = self.font.render("No exploration photos captured yet.", True, WHITE)
                self.screen.blit(empty_text, empty_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            else:
                columns = 3
                image_width = 330
                image_height = 220
                for index, image in enumerate(captured_images):
                    column = index % columns
                    row = index // columns
                    image_rect = pygame.Rect(
                        30 + column * 390,
                        85 + row * 260,
                        image_width,
                        image_height,
                    )
                    if image_rect.bottom > SCREEN_HEIGHT - 55:
                        break
                    scaled_image = pygame.transform.smoothscale(image, image_rect.size)
                    self.screen.blit(scaled_image, image_rect)

            back_button = pygame.Rect(SCREEN_WIDTH - 170, SCREEN_HEIGHT - 48, 140, 36)
            pygame.draw.rect(self.screen, RED, back_button, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, back_button, 2, border_radius=8)
            back_text = self.small_font.render("BACK", True, WHITE)
            self.screen.blit(back_text, back_text.get_rect(center=back_button.center))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    viewing_images = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    viewing_images = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if back_button.collidepoint(event.pos):
                        viewing_images = False

            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_bhutan_map(self):
        self.screen.fill((235, 239, 225))
        title = self.big_font.render("Bhutan District Map", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 35)))

        markers = {
            "Thimphu": (0.2817, 0.5069), "Paro": (0.2212, 0.5264),
            "Haa": (0.1803, 0.5741), "Chukha": (0.2582, 0.7134),
            "Samtse": (0.1440, 0.8164), "Dagana": (0.3383, 0.7060),
            "Punakha": (0.3417, 0.4433), "Wangdue Phodrang": (0.3533, 0.5039),
            "Gasa": (0.3088, 0.2917), "Trongsa": (0.5056, 0.5051),
            "Bumthang": (0.5704, 0.4664), "Lhuentse": (0.6865, 0.4095),
            "Mongar": (0.7057, 0.6192), "Trashigang": (0.7880, 0.6095),
            "Trashi Yangtse": (0.7715, 0.4382), "Sarpang": (0.4510, 0.8213),
            "Tsirang": (0.4130, 0.7315), "Zhemgang": (0.5514, 0.6512),
            "Samdrup Jongkhar": (0.7711, 0.8498), "Pemagatshel": (0.7440, 0.7287),
        }

        self.map_zoom += (self.map_zoom_target - self.map_zoom) * 0.28
        map_rect = None
        if self.map_image:
            if self.map_selected_district:
                map_area = pygame.Rect(20, 80, 735, 555)
                selected_relative = markers[self.map_selected_district]
                scaled_size = (
                    int(self.map_image.get_width() * self.map_zoom),
                    int(self.map_image.get_height() * self.map_zoom),
                )
                scaled_map = pygame.transform.smoothscale(self.map_image, scaled_size)
                focus = (map_area.centerx, map_area.centery)
                map_rect = pygame.Rect(
                    focus[0] - int(selected_relative[0] * scaled_map.get_width()),
                    focus[1] - int(selected_relative[1] * scaled_map.get_height()),
                    scaled_map.get_width(),
                    scaled_map.get_height(),
                )
                self.screen.set_clip(map_area)
                self.screen.blit(scaled_map, map_rect)
                self.screen.set_clip(None)
            else:
                map_rect = self.map_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
                self.screen.blit(self.map_image, map_rect)
        else:
            message = self.font.render("Bhutan map image not found", True, RED)
            self.screen.blit(message, message.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

        mouse_pos = pygame.mouse.get_pos()
        if map_rect:
            for district_name, (relative_x, relative_y) in markers.items():
                marker_pos = (
                    map_rect.x + int(relative_x * map_rect.width),
                    map_rect.y + int(relative_y * map_rect.height),
                )
                selected = district_name == self.map_selected_district
                hovered = math.hypot(mouse_pos[0] - marker_pos[0], mouse_pos[1] - marker_pos[1]) < 18
                radius = 15 if selected else 10
                if not self.map_selected_district or selected:
                    pygame.draw.circle(self.screen, BLACK, (marker_pos[0] + 2, marker_pos[1] + 2), radius)
                    pygame.draw.circle(self.screen, GOLD if selected else RED, marker_pos, radius)
                    pygame.draw.circle(self.screen, WHITE, marker_pos, radius, 2)
                if hovered or selected:
                    label = self.small_font.render(district_name, True, WHITE)
                    label_rect = label.get_rect(center=(marker_pos[0], marker_pos[1] - 25))
                    pygame.draw.rect(self.screen, BLACK, label_rect.inflate(10, 6), border_radius=4)
                    self.screen.blit(label, label_rect)

        selected_district = next(
            (district for district in bhutan_districts if district["name"] == self.map_selected_district),
            None,
        )
        info_rect = None
        explore_button = pygame.Rect(0, 0, 0, 0)
        back_button = pygame.Rect(0, 0, 0, 0)
        if selected_district:
            info_rect = pygame.Rect(775, 80, 405, 555)
            pygame.draw.rect(self.screen, (20, 35, 38), info_rect, border_radius=14)
            pygame.draw.rect(self.screen, selected_district["region_color"], info_rect, 3, border_radius=14)
            header = self.font.render(f"{selected_district['icon']} {selected_district['name']}", True, GOLD)
            self.screen.blit(header, (info_rect.x + 20, info_rect.y + 18))

            summary = [
                ("REGION", selected_district.get("region", "Bhutan")),
                ("ABOUT", selected_district.get("historical_significance", "A place rich in living culture and history.")),
                ("KNOWN FOR", selected_district.get("religious_importance", "Sacred places, local stories, and traditions.")),
                ("TRAVEL NOTE", selected_district.get("tour_narration", "Explore the district to uncover its stories.")),
            ]
            y_pos = info_rect.y + 70
            for section_title, section_text in summary:
                section = self.small_font.render(section_title, True, CYAN)
                self.screen.blit(section, (info_rect.x + 20, y_pos))
                y_pos += 25
                for line in wrap_text(section_text, self.small_font, info_rect.width - 45)[:3]:
                    self.screen.blit(self.small_font.render(line, True, WHITE), (info_rect.x + 20, y_pos))
                    y_pos += 23
                y_pos += 10

            explore_button = pygame.Rect(info_rect.x + 20, info_rect.bottom - 65, 175, 42)
            back_button = pygame.Rect(info_rect.right - 195, info_rect.bottom - 65, 175, 42)
            pygame.draw.rect(self.screen, FOREST_GREEN, explore_button, border_radius=8)
            pygame.draw.rect(self.screen, RED, back_button, border_radius=8)
            self.screen.blit(self.small_font.render("EXPLORE", True, WHITE), self.small_font.render("EXPLORE", True, WHITE).get_rect(center=explore_button.center))
            self.screen.blit(self.small_font.render("BACK TO MAP", True, WHITE), self.small_font.render("BACK TO MAP", True, WHITE).get_rect(center=back_button.center))
            instruction = self.small_font.render("Click another circle to inspect it | ESC: back", True, WHITE)
        else:
            instruction = self.small_font.render("Click a district circle to zoom in and learn about it | ESC: return", True, WHITE)
        self.screen.blit(instruction, (25, SCREEN_HEIGHT - 32))
        lobby_button = pygame.Rect(25, SCREEN_HEIGHT - 78, 145, 38)
        pygame.draw.rect(self.screen, DARK_BLUE, lobby_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, lobby_button, 2, border_radius=8)
        lobby_text = self.small_font.render("Lobby", True, WHITE)
        self.screen.blit(lobby_text, lobby_text.get_rect(center=lobby_button.center))
        captured_button = pygame.Rect(185, SCREEN_HEIGHT - 78, 205, 38)
        pygame.draw.rect(self.screen, DARK_BLUE, captured_button, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, captured_button, 2, border_radius=8)
        captured_text = self.small_font.render("IMGAE CAPTURED", True, WHITE)
        self.screen.blit(captured_text, captured_text.get_rect(center=captured_button.center))

        if self.show_game_guide:
            guide_rect = pygame.Rect(250, 130, 700, 420)
            pygame.draw.rect(self.screen, (15, 30, 35), guide_rect, border_radius=16)
            pygame.draw.rect(self.screen, GOLD, guide_rect, 3, border_radius=16)
            guide_title = self.big_font.render("How to Explore Bhutan", True, GOLD)
            self.screen.blit(guide_title, guide_title.get_rect(center=(SCREEN_WIDTH // 2, 180)))
            guide_lines = [
                "Choose a district on the map to begin.",
                "Use WASD or the arrow keys to move.",
                "Visit every marked site and collect knowledge.",
                "Talk to monks, discover secrets, and learn about Bhutan.",
                "Press P to take a photo and I to view your skills.",
                "Complete the cultural challenge to master the district.",
            ]
            for index, line in enumerate(guide_lines):
                guide_text = self.small_font.render(line, True, WHITE)
                self.screen.blit(guide_text, (guide_rect.x + 55, 230 + index * 38))
            dismiss_text = self.small_font.render("Click or press any key to continue", True, (210, 210, 210))
            self.screen.blit(dismiss_text, dismiss_text.get_rect(center=(SCREEN_WIDTH // 2, 510)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and lobby_button.collidepoint(event.pos):
                self.map_selected_district = None
                self.map_zoom_target = 1.0
                self.state = GameState.CHARACTER_CUSTOMIZATION
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and captured_button.collidepoint(event.pos):
                self.show_captured_images()
            elif self.show_game_guide and (event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN):
                self.show_game_guide = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.map_selected_district:
                    self.map_selected_district = None
                    self.map_zoom_target = 1.0
                else:
                    self.state = GameState.MAIN_MENU
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and map_rect:
                if info_rect and explore_button.collidepoint(event.pos):
                    self.start_district_exploration(selected_district)
                    break
                if info_rect and back_button.collidepoint(event.pos):
                    self.map_selected_district = None
                    self.map_zoom_target = 1.0
                    break
                for district_name, (relative_x, relative_y) in markers.items():
                    marker_pos = (
                        map_rect.x + int(relative_x * map_rect.width),
                        map_rect.y + int(relative_y * map_rect.height),
                    )
                    if math.hypot(event.pos[0] - marker_pos[0], event.pos[1] - marker_pos[1]) < 20:
                        self.map_selected_district = district_name
                        self.map_zoom_target = 1.8
                        break

        pygame.display.flip()
        
    def handle_district_info(self):
        if not self.selected_district_for_info:
            self.state = GameState.LEVEL_SELECT
            return
            
        self.draw_background()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.MOUSEWHEEL:
                self.info_scroll_offset -= event.y * 30
                self.info_scroll_offset = max(0, self.info_scroll_offset)
                
        close_rect, back_button, explore_button = self.draw_district_info_panel(self.selected_district_for_info)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if close_rect.collidepoint(mouse_pos) or back_button.collidepoint(mouse_pos):
                        self.state = GameState.LEVEL_SELECT
                        self.selected_district_for_info = None
                        self.info_scroll_offset = 0
                    elif explore_button.collidepoint(mouse_pos):
                        self.start_district_exploration(self.selected_district_for_info)
                        self.selected_district_for_info = None
                        self.info_scroll_offset = 0
                        
        pygame.display.flip()
        
    def handle_exploration(self):
        if self.explorer is None or self.current_district is None:
            self.state = GameState.BHUTAN_MAP
            return
        if self.show_pause_menu:
            buttons = self.draw_pause_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_pause_menu = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if buttons["resume"].collidepoint(event.pos):
                        self.show_pause_menu = False
                    elif buttons["mute"].collidepoint(event.pos):
                        self.toggle_sound()
                    elif buttons["leave"].collidepoint(event.pos):
                        self.show_pause_menu = False
                        self.state = GameState.MAIN_MENU
                        return
            pygame.display.flip()
            return

        keys = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.show_pause_menu = True
                    return
                elif event.key == pygame.K_i:
                    self.draw_skills_panel()
                    pygame.display.flip()
                    pygame.time.wait(1500)
                elif event.key == pygame.K_p:
                    if self.photo_journal.capture(self.current_district["name"], f"{self.current_district['name']} Landscape"):
                        self.explorer.add_xp(self.photo_journal.bonus_xp_per_photo)
                        self.add_particles(self.explorer.x, self.explorer.y, GOLD, 15)
                        self.show_notification(f"📸 Photo captured! +{self.photo_journal.bonus_xp_per_photo} XP", GOLD)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - 55, 10, 110, 42)
                if menu_rect.collidepoint(event.pos):
                    self.show_pause_menu = True
                    return
                        
        self.time_of_day = TimeOfDay.DAY
        self.camera_x = int(self.explorer.x - SCREEN_WIDTH // 2)
        self.camera_y = int(self.explorer.y - SCREEN_HEIGHT // 2)
        self.camera_x = max(0, min(self.camera_x, WORLD_WIDTH - SCREEN_WIDTH))
        self.camera_y = max(0, min(self.camera_y, WORLD_HEIGHT - SCREEN_HEIGHT))
        
        if self.explorer:
            move_explorer(self.explorer, keys)
        
        for animal in self.wildlife[:]:
            animal.update()
            if not animal.active:
                self.wildlife.remove(animal)
        
        self.encounter_cooldown += 1
        if self.encounter_cooldown > 60 and random.random() < 0.025:
            self.trigger_random_encounter()
            self.encounter_cooldown = 0
        
        if self.handle_exploration_collisions():
            return
        
        self.screen.fill(self.time_of_day.ambient_color)
        self.draw_terrain_with_forest()
        self.draw_exploration_atmosphere()
        
        for animal in self.wildlife:
            animal.draw(self.screen, self.camera_x, self.camera_y)

        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera_x, self.camera_y)

        for scroll in self.knowledge_scrolls:
            scroll.draw(self.screen, self.camera_x, self.camera_y)

        for heart in self.exp_hearts:
            heart.draw(self.screen, self.camera_x, self.camera_y)
        
        for discovery in self.hidden_discoveries:
            discovery.draw(self.screen, self.camera_x, self.camera_y)
        
        for poi in self.points_of_interest:
            poi.draw(self.screen, self.camera_x, self.camera_y)
        
        for monk in self.monks:
            monk.draw(self.screen, self.camera_x, self.camera_y)
        
        if self.explorer:
            self.explorer.draw(self.screen, self.camera_x, self.camera_y)
        
        self.particles = [p for p in self.particles if p.update()]
        for particle in self.particles:
            particle.draw(self.screen, self.camera_x, self.camera_y)
        
        self.draw_visibility_overlay()
        self.draw_exploration_ui()
        self.draw_exploration_hud()
        
        if self.exploration_narration_timer > 0:
            self.exploration_narration_timer -= 1
            if self.exploration_narration_timer > 0:
                text_surface = self.small_font.render(self.exploration_narration_text, True, WHEAT)
                self.screen.blit(text_surface, (20, SCREEN_HEIGHT - 60))
                
        pygame.display.flip()

    def handle_exploration_collisions(self):
        if self.explorer is None:
            return False
        player_rect = self.explorer.rect()
        interactions = [
            (self.points_of_interest, self._handle_poi_collision),
            (self.monks, self._handle_monk_collision),
            (self.knowledge_scrolls, self._handle_scroll_collision),
            (self.exp_hearts, self._handle_heart_collision),
            (self.hidden_discoveries, self._handle_discovery_collision),
        ]
        for entities, on_hit in interactions:
            for entity in entities:
                if entity.check_collision(player_rect):
                    on_hit(entity)
                    return True
        return False

    def _handle_poi_collision(self, poi):
        poi.visited = True
        self.show_knowledge_panel(poi)

    def _handle_monk_collision(self, monk):
        story = monk.interact(self.explorer, self.reputation.trust_level)
        self.show_monk_dialogue(monk, story)

    def _handle_scroll_collision(self, scroll):
        message = scroll.collect(self.explorer)
        self.show_notification(message, GREEN)

    def _handle_heart_collision(self, heart):
        message = heart.collect(self.explorer)
        self.add_particles(heart.x, heart.y, (255, 80, 100), 10)
        self.show_notification(message, (255, 100, 120))

    def _handle_discovery_collision(self, discovery):
        message = discovery.discover(self.explorer)
        self.show_discovery_panel(discovery)
        self.show_notification(message, GOLD)
        
    def handle_cultural_challenge(self):
        if self.explorer is None:
            self.state = GameState.BHUTAN_MAP
            return
        self.draw_background()
        
        if not self.current_cultural_quiz:
            self.state = GameState.LEVEL_SELECT
            return
            
        panel_rect = pygame.Rect(SCREEN_WIDTH//2 - 350, 100, 700, 450)
        pygame.draw.rect(self.screen, (0, 0, 0, 200), panel_rect, border_radius=20)
        pygame.draw.rect(self.screen, FOREST_GREEN, panel_rect, 3, border_radius=20)
        
        title = self.big_font.render("Cultural Challenge", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 140))
        self.screen.blit(title, title_rect)
        
        question_lines = wrap_text(self.current_cultural_quiz["question"], self.font, 620)
        for line_index, question_line in enumerate(question_lines):
            question_surface = self.font.render(question_line, True, YELLOW)
            question_rect = question_surface.get_rect(center=(SCREEN_WIDTH//2, 185 + line_index * 30))
            self.screen.blit(question_surface, question_rect)
        
        options = self.current_cultural_quiz["options"]
        option_rects = []
        start_y = 230 + len(question_lines) * 30
        
        for i, option in enumerate(options):
            rect = pygame.Rect(SCREEN_WIDTH//2 - 280, start_y + i * 55, 560, 45)
            
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(self.screen, (50, 50, 100), rect, border_radius=10)
            else:
                pygame.draw.rect(self.screen, (30, 30, 80), rect, border_radius=10)
                
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=10)
            
            option_surface = self.font.render(f"{chr(65+i)}. {option}", True, WHITE)
            option_rect = option_surface.get_rect(center=(SCREEN_WIDTH//2, start_y + i * 55 + 22))
            self.screen.blit(option_surface, option_rect)
            option_rects.append((rect, option))
            
        reward_text = self.small_font.render("Complete to earn 100 XP and your Certificate!", True, GOLD)
        reward_rect = reward_text.get_rect(center=(SCREEN_WIDTH//2, 500))
        self.screen.blit(reward_text, reward_rect)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    for rect, option in option_rects:
                        if rect.collidepoint(mouse_pos):
                            if option == self.current_cultural_quiz["answer"]:
                                self.explorer.add_xp(100)
                                self.explorer.wisdom += 25
                                self.save_game()
                                
                                correct_text = self.font.render("Correct! You mastered this district!", True, GREEN)
                                correct_rect = correct_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 70))
                                self.screen.blit(correct_text, correct_rect)
                                pygame.display.flip()
                                pygame.time.wait(1500)
                                
                                self.show_completion_certificate()
                                self.map_selected_district = None
                                self.state = GameState.BHUTAN_MAP
                            else:
                                wrong_text = self.font.render(f"Correct: {self.current_cultural_quiz['answer']}", True, RED)
                                wrong_rect = wrong_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 70))
                                self.screen.blit(wrong_text, wrong_rect)
                                pygame.display.flip()
                                pygame.time.wait(2000)
                            break
                            
        pygame.display.flip()
        
    def show_completion_certificate(self):
        render_completion_certificate(self)
                    
    def handle_game_over(self):
        self.draw_background()
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        game_over_text = self.title_font.render("Journey Complete", True, GOLD)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(game_over_text, game_over_rect)
        
        if self.explorer:
            stats = [
                f"Final Level: {self.explorer.level}",
                f"Knowledge: {self.explorer.knowledge}",
                f"Wisdom: {self.explorer.wisdom}",
                f"Districts: {len(self.completed_districts)}/20"
            ]
            for i, stat in enumerate(stats):
                stat_text = self.font.render(stat, True, WHITE)
                stat_rect = stat_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20 + i * 40))
                self.screen.blit(stat_text, stat_rect)
                
        restart_text = self.big_font.render("Return to Main Menu", True, YELLOW)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 140))
        self.screen.blit(restart_text, restart_rect)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.clear_save()
                self.state = GameState.MAIN_MENU
                
        pygame.display.flip()
        
    def handle_victory(self):
        self.draw_background()
        
        for _ in range(50):
            particle_x = random.randint(0, SCREEN_WIDTH)
            particle_y = random.randint(0, SCREEN_HEIGHT)
            self.add_particles(particle_x, particle_y, GOLD, 1)
        
        victory_text = self.title_font.render("GRAND MASTER EXPLORER!", True, GOLD)
        victory_rect = victory_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 80))
        
        shadow = self.title_font.render("GRAND MASTER EXPLORER!", True, BLACK)
        shadow_rect = shadow.get_rect(center=(SCREEN_WIDTH//2 + 5, SCREEN_HEIGHT//2 - 75))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(victory_text, victory_rect)
        
        congrats_text = self.big_font.render("You mastered all 20 Dzongkhags of Bhutan!", True, WHITE)
        congrats_rect = congrats_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(congrats_text, congrats_rect)
        
        if self.explorer:
            stats = [
                f"Final Level: {self.explorer.level}",
                f"Total Knowledge: {self.explorer.knowledge}",
                f"Total Wisdom: {self.explorer.wisdom}",
                f"All 20 Districts Mastered!",
                f"Photos Taken: {len(self.photo_journal.photos)}"
            ]
            for i, stat in enumerate(stats):
                stat_text = self.font.render(stat, True, YELLOW)
                stat_rect = stat_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60 + i * 40))
                self.screen.blit(stat_text, stat_rect)
                
        restart_text = self.font.render("Click to return to main menu", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 260))
        self.screen.blit(restart_text, restart_rect)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.clear_save()
                self.state = GameState.MAIN_MENU
                
        pygame.display.flip()
        
    def save_game(self):
        if not self.explorer:
            return False
            
        save_data = {
            "completed_districts": self.completed_districts,
            "explorer_name": self.explorer.name,
            "explorer_color": self.explorer.color,
            "explorer_hat": self.explorer.hat_type,
            "explorer_class": self.explorer.class_name,
            "knowledge": self.explorer.knowledge,
            "wisdom": self.explorer.wisdom,
            "level": self.explorer.level,
            "xp": self.explorer.xp,
            "unlocked_classes": sorted(self.unlocked_classes),
            "owned_songs": sorted(self.owned_songs),
            "selected_song": self.selected_song,
            "collectibles": self.explorer.collectibles,
            "reputation_score": self.reputation.score,
            "photos": self.photo_journal.photos,
            "skills": {s.type.value: {"level": s.level, "xp": s.xp} for s in self.skills.values()}
        }
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(save_data, f)
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
            
    def load_game(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f:
                    save_data = json.load(f)
                self.completed_districts = save_data.get("completed_districts", [])
                self.saved_explorer_data = {
                    "name": save_data.get("explorer_name", "Explorer"),
                    "color": save_data.get("explorer_color", FOREST_GREEN),
                    "hat": save_data.get("explorer_hat", "traditional"),
                    "class_name": save_data.get("explorer_class", "Forest Ranger"),
                    "knowledge": save_data.get("knowledge", 0),
                    "wisdom": save_data.get("wisdom", 0),
                    "level": save_data.get("level", 1),
                    "xp": save_data.get("xp", 0),
                    "collectibles": save_data.get("collectibles", [])
                }
                self.unlocked_classes = set(save_data.get("unlocked_classes", ["Custom Explorer"]))
                self.unlocked_classes.add(self.saved_explorer_data["class_name"])
                self.owned_songs = set(save_data.get("owned_songs", ["folk_90s"]))
                self.owned_songs.add("folk_90s")
                saved_song = save_data.get("selected_song", "folk_90s")
                if saved_song in self.owned_songs:
                    self.play_song(saved_song)
                self.reputation.score = save_data.get("reputation_score", 0)
                self.reputation.trust_level = (self.reputation.score + 100) // 40
                self.photo_journal.photos = save_data.get("photos", [])
                
                skills_data = save_data.get("skills", {})
                for skill_type in self.skills.values():
                    if skill_type.type.value in skills_data:
                        skill_type.level = skills_data[skill_type.type.value]["level"]
                        skill_type.xp = skills_data[skill_type.type.value]["xp"]
                return True
            except Exception as e:
                print(f"Error loading: {e}")
                return False
        return False
        
    def clear_save(self):
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        self.completed_districts = []
        self.saved_explorer_data = None
        self.explorer = cast(Explorer, None)
        self.name_input = ""
        self.selected_class = "Custom Explorer"
        self.unlocked_classes = {"Custom Explorer"}
        self.owned_songs = {"folk_90s"}
        self.selected_song = "folk_90s"
        self.play_song("folk_90s")
        self.reputation = Reputation()
        self.photo_journal = PhotoJournal()
        for skill in self.skills.values():
            skill.level = 1
            skill.xp = 0
            
    def run(self):
        while self.running:
            if self.state == GameState.INTRO:
                if not hasattr(self, "intro"):
                    self.intro = IntroSequence(self.screen, self.finish_intro)
                self.intro.handle()
            elif self.state == GameState.MAIN_MENU:
                self.handle_main_menu()
            elif self.state == GameState.CHARACTER_CUSTOMIZATION:
                self.handle_character_customization()
            elif self.state == GameState.SONG_SHOP:
                self.handle_song_shop()
            elif self.state == GameState.BHUTAN_MAP:
                self.handle_bhutan_map()
            elif self.state == GameState.LEVEL_SELECT:
                self.handle_level_select()
            elif self.state == GameState.DISTRICT_INFO:
                self.handle_district_info()
            elif self.state == GameState.EXPLORATION:
                self.handle_exploration()
            elif self.state == GameState.RAID:
                self.handle_raid()
            elif self.state == GameState.CULTURAL_CHALLENGE:
                self.handle_cultural_challenge()
            elif self.state == GameState.GAME_OVER:
                self.handle_game_over()
            elif self.state == GameState.VICTORY:
                self.handle_victory()
                
            self.clock.tick(FPS)
            

def run_game():
    pygame.init()
    try:
        pygame.mixer.init()
        game = Game()
        game.run()
    finally:
        pygame.quit()

if __name__ == "__main__":
    run_game()