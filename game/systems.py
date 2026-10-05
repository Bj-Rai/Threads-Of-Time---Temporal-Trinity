from enum import Enum


class SkillType(Enum):
    NAVIGATION = "Navigation"
    CULTURAL_KNOWLEDGE = "Cultural Knowledge"
    LANGUAGE = "Language"
    STEALTH = "Stealth"


class Skill:
    def __init__(self, skill_type, level=1):
        self.type = skill_type
        self.level = level
        self.xp = 0
        self.xp_to_next = 100 * level

    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next:
            self.level_up()
            return True
        return False

    def level_up(self):
        self.level += 1
        self.xp = 0
        self.xp_to_next = 100 * self.level


class Reputation:
    def __init__(self):
        self.score = 0
        self.trust_level = 0

    def modify(self, delta):
        self.score = max(-100, min(100, self.score + delta))
        self.trust_level = min(5, (self.score + 100) // 40)

    @property
    def title(self):
        if self.score <= -80:
            return "Dishonored"
        if self.score <= -40:
            return "Suspicious"
        if self.score <= -10:
            return "Unknown"
        if self.score <= 30:
            return "Acquaintance"
        if self.score <= 70:
            return "Trusted Friend"
        return "Honored Guest"


class PhotoJournal:
    def __init__(self):
        self.photos = []
        self.max_photos = 50

    def capture(self, district_name, landmark_name):
        if len(self.photos) < self.max_photos:
            self.photos.append((district_name, landmark_name))
            return True
        return False

    @property
    def bonus_xp_per_photo(self):
        return 25