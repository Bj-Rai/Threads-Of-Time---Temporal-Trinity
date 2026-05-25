import pygame
import sys
import math
import random

# Initialize Pygame core subsystems
pygame.init()

# --- COLOR PALETTE ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (30, 64, 175)
GOLD = (255, 215, 0)
SCROLL_BG = (254, 243, 199)    
DARK_GRAY = (55, 65, 81)        
PATH_COLOR = (217, 119, 6)    
ROOF_RED = (185, 28, 28)
GROUND_COLOR = (34, 139, 34)

# Gho Fabric Tones
GHO_BURGUNDY = (127, 29, 29)
GHO_FABRIC_PATTERN = (185, 28, 28)
KERA_BELT = (234, 179, 8)

# Map Region Tones
WEST_GREEN = (34, 197, 94)       
CENTRAL_LIGHT = (134, 239, 172)  
SOUTH_YELLOW = (234, 224, 76)    
EAST_PASTEL = (187, 247, 208)    

# Environment Colors
PRAYER_RED = (220, 38, 38)
PRAYER_YELLOW = (234, 179, 8)
PRAYER_GREEN = (22, 163, 74)
PRAYER_BLUE = (37, 99, 235)

# Window Configuration Setup
WIDTH = 1000
HEIGHT = 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Kingdom Chronicles: Authentic Bhutan Map")

# --- LOAD AND SCALE REAL MAP ASSET ---
try:
    raw_map_image = pygame.image.load("Bhutan_Map_en_dz.png")
    bhutan_map_surface = pygame.transform.smoothscale(raw_map_image, (790, 510))
except Exception as e:
    print(f"Error loading Bhutan_Map_en_dz.png: {e}")
    bhutan_map_surface = pygame.Surface((790, 510))
    bhutan_map_surface.fill((219, 234, 254))

# --- FONTS ---
title_font = pygame.font.SysFont("arial", 26, bold=True)
text_font = pygame.font.SysFont("arial", 20, bold=True)
small_font = pygame.font.SysFont("arial", 12, bold=True)

# --- TRUE GEOGRAPHIC COORDINATES ---
dzongkhags = [
    # --- WESTERN BHUTAN ---
    {"name": "Samtse", "region": "West", "color": WEST_GREEN, "type": "dzong",
     "poly": [(40, 460), (45, 410), (105, 420), (100, 475), (45, 490)],
     "question": "Which prominent religious landmark was reconstructed in Samtse?", "options": ["Chorten Kora", "Shivalaya Mandir", "Memorial Chorten", "Kyichu Lhakhang"], "answer": 1},
    
    {"name": "Haa", "region": "West", "color": WEST_GREEN, "type": "dzong",
     "poly": [(45, 340), (115, 335), (105, 385), (45, 410)],
     "question": "Which twin temples are located at the base of Meri Puensum in Haa?", "options": ["Jambay & Kurjey", "Lhakhang Karpo & Nagpo", "Chimi & Tamshing", "Tango & Cheri"], "answer": 1},
    
    {"name": "Paro", "region": "West", "color": WEST_GREEN, "type": "taktsang",
     "poly": [(115, 335), (170, 290), (190, 355), (105, 385)],
     "question": "Which iconic cliffside monastery is located in Paro?", "options": ["Punakha Dzong", "Tashichho Dzong", "Paro Taktsang", "Trongsa Dzong"], "answer": 2},
    
    {"name": "Chhukha", "region": "West", "color": WEST_GREEN, "type": "dzong",
     "poly": [(105, 385), (190, 355), (215, 455), (160, 490), (100, 475), (105, 420)],
     "question": "Which famous gateway town acts as Chhukha's primary border link to India?", "options": ["Gelephu", "Phuentsholing", "Samdrup Jongkhar", "Panbang"], "answer": 1},
    
    {"name": "Thimphu", "region": "West", "color": WEST_GREEN, "type": "tashichho",
     "poly": [(170, 290), (225, 230), (255, 300), (220, 360), (190, 355)],
     "question": "Which fortress in Thimphu serves as the main seat of government?", "options": ["Simtokha Dzong", "Tashichho Dzong", "Punakha Dzong", "Daga Dzong"], "answer": 1},
    
    {"name": "Gasa", "region": "West", "color": WEST_GREEN, "type": "dzong",
     "poly": [(225, 230), (310, 155), (390, 220), (330, 280), (255, 300)],
     "question": "What famous therapeutic hot spring is located at the foot of Gasa Dzong?", "options": ["Chimi Tsachhu", "Gasa Tsachhu", "Gelephu Tsachhu", "Dhur Tsachhu"], "answer": 1},

    # --- CENTRAL BHUTAN ---
    {"name": "Punakha", "region": "Central", "color": CENTRAL_LIGHT, "type": "dzong",
     "poly": [(255, 300), (330, 280), (330, 335), (275, 345)],
     "question": "Punakha Dzong is built directly at the convergence of which two rivers?", "options": ["Wang Chhu & Pa Chhu", "Pho Chhu & Mo Chhu", "Mangde Chhu & Drangme Chhu", "Kuri Chhu & Chamkhar Chhu"], "answer": 1},
    
    {"name": "Wangdue Phodrang", "region": "Central", "color": CENTRAL_LIGHT, "type": "dzong",
     "poly": [(330, 280), (390, 220), (440, 280), (420, 415), (345, 415), (330, 335)],
     "question": "Which famous 17th-century monastery overlooks the crane-filled Phobjikha Valley?", "options": ["Tango Goemba", "Gangtey Goemba", "Kurjey Lhakhang", "Tamshing Lhakhang"], "answer": 1},
    
    {"name": "Dagana", "region": "Central", "color": CENTRAL_LIGHT, "type": "dzong",
     "poly": [(220, 360), (255, 300), (275, 345), (345, 415), (305, 480), (215, 455)],
     "question": "What is the name of the prominent historic fortress located in Dagana?", "options": ["Daga Trashiyangste Dzong", "Lhuentse Dzong", "Zhemgang Dzong", "Simtokha Dzong"], "answer": 0},
    
    {"name": "Tsirang", "region": "Central", "color": CENTRAL_LIGHT, "type": "dzong",
     "poly": [(345, 415), (395, 415), (385, 490), (305, 480)],
     "question": "What is the primary administrative and urban town hub of Tsirang?", "options": ["Damphu", "Jakar", "Gelephu", "Khonsana"], "answer": 0},

    # --- SOUTHERN BHUTAN ---
    {"name": "Trongsa", "region": "South", "color": SOUTH_YELLOW, "type": "dzong",
     "poly": [(440, 280), (500, 285), (490, 390), (420, 415)],
     "question": "Which massive compound holds the historical title of being Bhutan's largest Dzong?", "options": ["Tashichho Dzong", "Trongsa Dzong", "Punakha Dzong", "Rinpung Dzong"], "answer": 1},
    
    {"name": "Sarpang", "region": "South", "color": SOUTH_YELLOW, "type": "dzong",
     "poly": [(385, 490), (395, 415), (420, 415), (490, 390), (520, 485), (445, 515)],
     "question": "Which fast-growing commercial border city is located within Sarpang district?", "options": ["Samtse", "Gelephu", "Phuentsholing", "Nganglam"], "answer": 1},
    
    {"name": "Zhemgang", "region": "South", "color": SOUTH_YELLOW, "type": "dzong",
     "poly": [(490, 390), (565, 380), (565, 475), (520, 485)],
     "question": "Zhemgang forms the critical historical and ecological gateway to which national park?", "options": ["Jigme Dorji National Park", "Royal Manas National Park", "Centennial Park", "Phrumsengla Park"], "answer": 1},
    
    {"name": "Bumthang", "region": "South", "color": SOUTH_YELLOW, "type": "mebartsho",
     "poly": [(390, 220), (510, 230), (560, 275), (565, 380), (490, 390), (500, 285), (440, 280)],
     "question": "What is the name of the famous sacred water site located in Bumthang valley?", "options": ["Pho Chhu", "Mebar Tsho (Burning Lake)", "Mo Chhu", "Gasa Tsachhu"], "answer": 1},

    # --- EASTERN BHUTAN ---
    {"name": "Lhuentse", "region": "East", "color": EAST_PASTEL, "type": "dzong",
     "poly": [(510, 230), (605, 210), (645, 270), (605, 325), (560, 275)],
     "question": "Which textile village in Lhuentse is renowned for weaving Kishuthara silk?", "options": ["Khoma", "Radhi", "Sombaykha", "Nabji"], "answer": 0},
    
    {"name": "Mongar", "region": "East", "color": EAST_PASTEL, "type": "dzong",
     "poly": [(565, 380), (560, 275), (605, 325), (670, 345), (655, 410), (605, 410)],
     "question": "The ruins of which legendary, massive historical stone fortress lie in Mongar?", "options": ["Drukgyel Dzong", "Zhongar Dzong", "Chakhar Dzong", "Ta Dzong"], "answer": 1},
    
    {"name": "Pemagatshel", "region": "East", "color": EAST_PASTEL, "type": "dzong",
     "poly": [(655, 410), (710, 400), (745, 445), (705, 485), (650, 465)],
     "question": "Pemagatshel is historically famous across Bhutan for crafting which items?", "options": ["Handmade Bronze Bells (Tsangli)", "Bamboo Bows", "Wooden Bowls", "Clay Pots"], "answer": 0},
    
    {"name": "Trashigang", "region": "East", "color": EAST_PASTEL, "type": "dzong",
     "poly": [(670, 345), (735, 290), (780, 335), (765, 410), (710, 400), (655, 410)],
     "question": "Trashigang Dzong sits dramatically positioned over the edge of which river?", "options": ["Drangme Chhu", "Gamri River", "Kuri Chhu", "Amo Chhu"], "answer": 1},
    
    {"name": "Trashi Yangtse", "region": "East", "color": EAST_PASTEL, "type": "chortenkora",
     "poly": [(605, 325), (645, 270), (705, 220), (745, 260), (735, 290), (670, 345)],
     "question": "Which famous Nepalese-style stupa is located in Trashi Yangtse?", "options": ["Chorten Kora", "Memorial Chorten", "National Monument", "Changangkha Lhakhang"], "answer": 0},
    
    {"name": "Samdrup Jongkhar", "region": "East", "color": EAST_PASTEL, "type": "dzong",
     "poly": [(650, 465), (705, 485), (765, 410), (795, 445), (775, 505), (715, 505)],
     "question": "Samdrup Jongkhar serves as the primary trade gateway to which Indian state?", "options": ["Sikkim", "Assam", "West Bengal", "Bihar"], "answer": 1}
]

# Decor elements (Fixed in absolute 3D world space)
street_decorations = []
random.seed(108)  
for i in range(25):
    side = -3.5 if i % 2 == 0 else 3.5
    z_pos = 3.0 + (i * 2.2)
    rand_type = random.choice(["flower", "prayer_flag", "willow_tree"])
    flag_color = random.choice([PRAYER_RED, PRAYER_YELLOW, PRAYER_GREEN, PRAYER_BLUE, WHITE])
    street_decorations.append({"x": side, "z": z_pos, "type": rand_type, "color": flag_color})

# Game Engine States
game_state = "start"
selected_dzongkhag = dzongkhags[4] 
walk_timer, animation_pulse = 0.0, 0.0
score = 10
unlocked_valleys = set(["Thimphu"])
quiz_feedback = ""

# CHARACTER SIMULATION SETTINGS
char_world_x = 0.0     # Horizontal position tracking
char_world_z = 16.0    # Starts further back (small) and moves toward the player (large)
char_facing_angle = 0.0 
is_moving = False

# Interactive Node Boxes
start_button = pygame.Rect(350, 530, 300, 55)  
option_rects = [pygame.Rect(220, 240 + i * 75, 550, 55) for i in range(4)]

sidebar_rects = []
for idx, dz in enumerate(dzongkhags):
    col = idx // 10
    row = idx % 10
    bx = 825 + (col * 82)
    by = 130 + (row * 45)
    sidebar_rects.append((pygame.Rect(bx, by, 78, 40), dz))

def draw_text(text, font, color, x, y):
    screen.blit(font.render(text, True, color), (x, y))

def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xints:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def draw_bhutanese_gho_character(x, y, scale=1.0, is_walking=False, angle=0.0):
    """Draws a complete stylized 2D sprite wearing a Bhutanese Gho configuration"""
    leg_swing = math.sin(walk_timer * 14) * 12 if is_walking else 0
    arm_swing = math.sin(walk_timer * 14) * 10 if is_walking else 0
    
    w_head = int(14 * scale)
    w_body = int(28 * scale)
    h_body = int(45 * scale)
    
    # Render legs below the wrapped tunic hemline
    pygame.draw.line(screen, (30, 41, 59), (x - 6*scale, y + h_body), (x - 6*scale + leg_swing, y + h_body + 18*scale), int(5*scale))
    pygame.draw.line(screen, (30, 41, 59), (x + 6*scale, y + h_body), (x + 6*scale - leg_swing, y + h_body + 18*scale), int(5*scale))
    
    # Main Body: The Gho tunic garment body box
    gho_rect = pygame.Rect(x - w_body//2, y, w_body, h_body)
    pygame.draw.rect(screen, GHO_BURGUNDY, gho_rect, border_radius=int(5*scale))
    
    # Internal traditional fabric fold stripes
    for i in range(2, w_body, 6):
        pygame.draw.line(screen, GHO_FABRIC_PATTERN, (gho_rect.x + i, y), (gho_rect.x + i, y + h_body), 2)
        
    # The Kera (Traditional woven belt wrap segment)
    pygame.draw.rect(screen, KERA_BELT, (x - w_body//2, y + int(24*scale), w_body, int(7*scale)))
    
    face_offset = int(math.sin(angle) * 4 * scale)
    
    # Head & Neck
    pygame.draw.circle(screen, (244, 210, 186), (x + face_offset, y - int(10*scale)), w_head)
    # Hair Topcap
    pygame.draw.arc(screen, BLACK, (x - w_head + face_offset, y - int(24*scale), w_head*2, w_head*2), 0, math.pi, int(6*scale))
    
    left_arm_y = y + int(14*scale) + arm_swing
    right_arm_y = y + int(14*scale) - arm_swing
    
    # Left Arm
    pygame.draw.line(screen, GHO_BURGUNDY, (x - w_body//2, y + int(10*scale)), (x - w_body//2 - int(10*scale), left_arm_y), int(6*scale))
    pygame.draw.circle(screen, WHITE, (x - w_body//2 - int(10*scale), left_arm_y), int(5*scale)) 
    pygame.draw.circle(screen, (244, 210, 186), (x - w_body//2 - int(12*scale), left_arm_y), int(3*scale)) 
    
    # Right Arm
    pygame.draw.line(screen, GHO_BURGUNDY, (x + w_body//2, y + int(10*scale)), (x + w_body//2 + int(10*scale), right_arm_y), int(6*scale))
    pygame.draw.circle(screen, WHITE, (x + w_body//2 + int(10*scale), right_arm_y), int(5*scale)) 
    pygame.draw.circle(screen, (244, 210, 186), (x + w_body//2 + int(12*scale), right_arm_y), int(3*scale)) 

def render_dynamic_landmark_3d(bx, by, scale_factor, place_type, name):
    w, h = int(85 * scale_factor), int(55 * scale_factor)
    pygame.draw.rect(screen, WHITE, (bx - w//2, by - h, w, h), border_radius=3)
    pygame.draw.rect(screen, ROOF_RED, (bx - w//2, by - h, w, h//4), border_radius=1)
    
    lbl_font = pygame.font.SysFont("arial", max(11, int(14 * scale_factor)), bold=True)
    lbl = lbl_font.render(name, True, WHITE)
    bg_box = pygame.Rect(bx - lbl.get_width()//2 - 6, by + 8, lbl.get_width() + 12, lbl.get_height() + 4)
    pygame.draw.rect(screen, BLACK, bg_box, border_radius=4)
    screen.blit(lbl, (bx - lbl.get_width()//2, bg_box.y + 2))

# --- MAIN CYCLE LOOP ---
running = True
clock = pygame.time.Clock()

while running:
    dt = clock.tick(60) / 1000.0  
    animation_pulse += dt
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "start":
                if start_button.collidepoint(event.pos): 
                    game_state = "map"

            elif game_state == "map":
                clicked_target = False
                for rect, dz in sidebar_rects:
                    if rect.collidepoint(event.pos):
                        selected_dzongkhag = dz
                        quiz_feedback = "" 
                        game_state = "info"
                        clicked_target = True
                        break
                
                if not clicked_target:
                    for dz in dzongkhags:
                        if point_in_poly(mouse_pos[0], mouse_pos[1], dz["poly"]):
                            selected_dzongkhag = dz
                            quiz_feedback = "" 
                            game_state = "info"
                            break

            elif game_state == "info":
                if start_button.collidepoint(event.pos):
                    # Reset character to spawn deep near the landmark horizon line
                    char_world_x, char_world_z = 0.0, 16.0
                    char_facing_angle = 0.0
                    game_state = "3d_world"

            elif game_state == "quiz":
                clicked_an_option = False
                for idx, rect in enumerate(option_rects):
                    if rect.collidepoint(event.pos):
                        clicked_an_option = True
                        if idx == selected_dzongkhag["answer"]:
                            score += 5
                            unlocked_valleys.add(selected_dzongkhag["name"])
                            game_state = "win_screen"
                        else:
                            score = max(0, score - 5)
                            quiz_feedback = "Chronicle mismatch! Try matching again."
                
                if not clicked_an_option and not pygame.Rect(220, 240, 550, 300).collidepoint(event.pos):
                    game_state = "map"

            elif game_state == "win_screen":
                game_state = "map"

    # --- CHARACTER WALKING CALCULATIONS (Fixed Scenery Matrix) ---
    if game_state == "3d_world":
        keys = pygame.key.get_pressed()
        move_speed = 4.5 * dt
        is_moving = False

        # Independent directional tracking map 
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            char_world_x -= move_speed
            char_facing_angle = -math.pi / 2
            is_moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            char_world_x += move_speed
            char_facing_angle = math.pi / 2
            is_moving = True
            
        # FIXED PROJECTION LOGIC:
        # W decreases depth 'z' value -> smaller 'z' creates a larger scaling factor -> character moves forward/closer to screen view
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            char_world_z -= move_speed * 1.5  
            char_facing_angle = math.pi     # Facing forward towards camera viewpoint
            is_moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            char_world_z = min(17.5, char_world_z + move_speed * 1.5)
            char_facing_angle = 0.0         # Facing away toward horizon background
            is_moving = True

        if is_moving: 
            walk_timer += dt  
        
        # Trigger point criteria upon hitting valley thresholds closest to the screen viewport bounds
        if char_world_z <= 3.2: 
            game_state = "quiz"
        if keys[pygame.K_ESCAPE]: 
            game_state = "map"

    # --- DRAWING LAYERS ---
    if game_state == "start":
        screen.fill((125, 211, 252))
        draw_text("BHUTAN MAP SIMULATION ENGINE", title_font, BLUE, 280, 60)
        draw_text("Accurate 4-Region Interlocking Geographical Boundary Verification Corridor", small_font, DARK_GRAY, 230, 110)
        draw_bhutanese_gho_character(WIDTH // 2, 320, scale=1.8, is_walking=True)
        pygame.draw.rect(screen, (34, 197, 94), start_button, border_radius=12)
        draw_text("INITIALIZE MAP CANVAS", text_font, WHITE, start_button.x + 36, start_button.y + 14)

    elif game_state == "map":
        screen.fill(SCROLL_BG)
        draw_text("Bhutan Map with States and Cities", title_font, BLACK, 30, 20)
        draw_text(f"Score: {score} | Explored: {len(unlocked_valleys)}/20", text_font, DARK_GRAY, 30, 65)
        
        map_box = pygame.Rect(20, 110, 790, 510)
        pygame.draw.rect(screen, WHITE, map_box, border_radius=10)
        screen.blit(bhutan_map_surface, (20, 110))

        hovered_dz = None
        for dz in dzongkhags:
            is_hovered = point_in_poly(mouse_pos[0], mouse_pos[1], dz["poly"])
            if is_hovered:
                hovered_dz = dz
                glow_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(glow_surface, (255, 215, 0, 85), dz["poly"]) 
                screen.blit(glow_surface, (0, 0))
                pygame.draw.polygon(screen, GOLD, dz["poly"], width=2)

        pygame.draw.rect(screen, BLUE, map_box, width=2, border_radius=10)

        sidebar_box = pygame.Rect(820, 110, 160, 510)
        pygame.draw.rect(screen, WHITE, sidebar_box, border_radius=8)
        pygame.draw.rect(screen, BLUE, sidebar_box, width=2, border_radius=8)

        for rect, dz in sidebar_rects:
            bg_color = (219, 234, 254)
            if rect.collidepoint(mouse_pos) or (hovered_dz and hovered_dz["name"] == dz["name"]):
                bg_color = GOLD
            
            pygame.draw.rect(screen, bg_color, rect, border_radius=5)
            pygame.draw.rect(screen, BLACK, rect, width=1, border_radius=5)
            draw_text(dz["name"][:8], small_font, BLACK, rect.x + 6, rect.y + 12)

    elif game_state == "info":
        screen.fill(DARK_GRAY)
        scroll_rect = pygame.Rect(80, 40, 840, 440)
        pygame.draw.rect(screen, SCROLL_BG, scroll_rect, border_radius=12)
        draw_text(f"Target Destination: {selected_dzongkhag['name']}", title_font, ROOF_RED, 120, 80)
        draw_text(f"Geographic Sector Grouping: {selected_dzongkhag['region']}ern Zone Corridor", text_font, BLACK, 120, 160)
        draw_text("Control your Bhutanese character using W, A, S, D or Arrow keys to cross the highway valley.", small_font, BLACK, 120, 240)
        
        pygame.draw.rect(screen, (34, 197, 94), start_button, border_radius=12)
        draw_text("START SIMULATION", text_font, WHITE, start_button.x + 50, start_button.y + 14)

    elif game_state == "3d_world":
        screen.fill((125, 211, 252)) # Sky
        
        # Draw Stationary Terrace Farming Step Blocks
        pygame.draw.rect(screen, (22, 101, 52), (0, HEIGHT//2, WIDTH, HEIGHT//2))
        for level in range(6):
            ty = (HEIGHT // 2) + (level * 25)
            tw = WIDTH + 200
            terr_points = []
            for tx in range(0, tw, 40):
                wave = math.sin(tx * 0.02 + level) * 15  
                terr_points.append((tx - 100, ty + int(wave)))
            terr_points.append((WIDTH, HEIGHT))
            terr_points.append((0, HEIGHT))
            if len(terr_points) > 2:
                pygame.draw.polygon(screen, (34, 197, 94 - level * 10), terr_points)

        # Draw Stationary highway path lines pointing to horizon
        pygame.draw.polygon(screen, (100, 110, 120), [(WIDTH//2-55, HEIGHT//2), (WIDTH//2+55, HEIGHT//2), (WIDTH//2+390, HEIGHT), (WIDTH//2-390, HEIGHT)])
        pygame.draw.polygon(screen, PATH_COLOR, [(WIDTH//2-18, HEIGHT//2), (WIDTH//2+18, HEIGHT//2), (WIDTH//2+95, HEIGHT), (WIDTH//2-95, HEIGHT)])

        # Construct projection sorting matrix for static decor assets
        all_3d_objects = []
        for decor in street_decorations:
            all_3d_objects.append({"x": decor["x"], "z": decor["z"], "type": decor["type"], "color": decor["color"]})
        
        # Fixed destination landmark positioned at the deep center horizon block
        all_3d_objects.append({"x": 0.0, "z": 18.0, "type": "landmark", "color": None})
        
        # Inject our character directly into world depth configuration index array for depth sorting
        all_3d_objects.append({"x": char_world_x, "z": char_world_z, "type": "player_character", "color": None})
        all_3d_objects.sort(key=lambda o: o["z"], reverse=True)

        # Render 3D Engine objects array sequentially from back to front
        for obj in all_3d_objects:
            if obj["z"] > 0.4:
                scale_factor = 450 / obj["z"]
                bx = int((WIDTH / 2) + (obj["x"] * scale_factor))
                by = int((HEIGHT / 2) + (0.14 * scale_factor))

                if -200 < bx < WIDTH + 200:
                    if obj["type"] == "flower":
                        pygame.draw.circle(screen, obj["color"], (bx, by), max(2, int(6 * (scale_factor / 90))))
                    elif obj["type"] == "prayer_flag":
                        pygame.draw.line(screen, BLACK, (bx, by + 40), (bx, by - 40), 2)
                    elif obj["type"] == "willow_tree":
                        pygame.draw.rect(screen, (115, 70, 35), (bx - 4, by, 8, 30))
                        pygame.draw.circle(screen, (22, 163, 74), (bx, by), 20)
                    elif obj["type"] == "landmark":
                        render_dynamic_landmark_3d(bx, by, scale_factor / 90, selected_dzongkhag["type"], selected_dzongkhag["name"])
                    elif obj["type"] == "player_character":
                        # Render our moving Gho character scaling dynamically based on inverted depth position
                        draw_bhutanese_gho_character(bx, by - int(40 * (scale_factor / 90)), scale=scale_factor/90, is_walking=is_moving, angle=char_facing_angle)

    elif game_state == "quiz":
        screen.fill(SCROLL_BG)
        draw_text("DISTRICT CHRONICLE SYNCHRONIZATION", title_font, BLUE, 180, 50)
        draw_text(selected_dzongkhag["question"], text_font, BLACK, 80, 130)
        draw_text("Click outside the selections to exit back to the map.", small_font, DARK_GRAY, 80, 175)

        if quiz_feedback:
            draw_text(quiz_feedback, text_font, ROOF_RED, 220, 550)

        for idx, option in enumerate(selected_dzongkhag["options"]):
            box = option_rects[idx]
            pygame.draw.rect(screen, BLUE, box, border_radius=8)
            draw_text(f"{idx + 1}. {option}", text_font, WHITE, box.x + 20, box.y + 12)

    elif game_state == "win_screen":
        screen.fill((34, 197, 94))
        draw_text("REGION SYNC COMPLETE!", title_font, WHITE, 130, 200)
        draw_text("Click anywhere on screen to switch back to your geographic map interface frame...", text_font, GOLD, 130, 410)

    pygame.display.update()

pygame.quit()
sys.exit()
