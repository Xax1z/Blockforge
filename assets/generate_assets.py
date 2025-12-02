"""
Pillow-based asset generator for Blockforge.
Generates all block textures, item textures, and food/meat textures.
"""

from PIL import Image, ImageDraw, ImageFilter
import os
import random


# Texture size (standard Minecraft-style 16x16)
TEXTURE_SIZE = 32


def ensure_directories():
    """Create asset subdirectories if they don't exist."""
    dirs = ['blocks', 'items', 'meat']
    for d in dirs:
        path = os.path.join(os.path.dirname(__file__), d)
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")


def add_noise(image, intensity=0.1):
    """Add subtle noise to an image for texture variety."""
    pixels = image.load()
    width, height = image.size
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            
            # Add random noise
            noise = random.randint(-int(255 * intensity), int(255 * intensity))
            r = max(0, min(255, r + noise))
            g = max(0, min(255, g + noise))
            b = max(0, min(255, b + noise))
            
            pixels[x, y] = (r, g, b, a)
    
    return image


def create_grass_texture():
    """Generate grass block texture (top view)."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (118, 189, 92, 255))
    
    # Add some darker green patches for variety
    draw = ImageDraw.Draw(img)
    for _ in range(20):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        darker = (97, 163, 74, 255)
        draw.point((x, y), fill=darker)
    
    img = add_noise(img, 0.08)
    return img


def create_dirt_texture():
    """Generate dirt block texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (143, 94, 61, 255))
    
    # Add some variation with different brown tones
    draw = ImageDraw.Draw(img)
    for _ in range(30):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = random.choice([(120, 80, 50, 255), (160, 100, 65, 255)])
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.1)
    return img


def create_stone_texture():
    """Generate stone block texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (140, 140, 143, 255))
    
    # Add darker spots
    draw = ImageDraw.Draw(img)
    for _ in range(25):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = random.choice([(120, 120, 123, 255), (150, 150, 153, 255)])
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.12)
    return img


def create_bedrock_texture():
    """Generate bedrock block texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (51, 51, 56, 255))
    
    # Very dark with some lighter spots
    draw = ImageDraw.Draw(img)
    for _ in range(15):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = (70, 70, 75, 255)
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.08)
    return img


def create_sand_texture():
    """Generate sand block texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (237, 227, 179, 255))
    
    # Add sandy grains
    draw = ImageDraw.Draw(img)
    for _ in range(35):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = random.choice([(230, 220, 170, 255), (245, 235, 190, 255)])
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.06)
    return img


def create_wood_texture():
    """Generate wood log texture (side view with bark)."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (140, 89, 51, 255))
    
    # Add vertical bark lines
    draw = ImageDraw.Draw(img)
    for x in range(0, TEXTURE_SIZE, 2):
        for y in range(TEXTURE_SIZE):
            if random.random() > 0.3:
                shade = random.choice([(120, 75, 40, 255), (150, 95, 55, 255)])
                draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.1)
    return img


def create_wood_top_texture():
    """Generate wood log texture (top view with rings)."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (166, 115, 64, 255))
    
    # Draw tree rings
    draw = ImageDraw.Draw(img)
    center = TEXTURE_SIZE // 2
    for radius in range(2, center, 2):
        color = (140 + radius * 3, 95 + radius * 2, 50 + radius, 255)
        draw.ellipse([center - radius, center - radius, 
                     center + radius, center + radius], 
                     outline=color)
    
    img = add_noise(img, 0.08)
    return img


def create_leaves_texture():
    """Generate leaves texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (51, 153, 51, 255))
    
    # Add leaf variation
    draw = ImageDraw.Draw(img)
    for _ in range(40):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = random.choice([(40, 130, 40, 255), (60, 170, 60, 255), (0, 0, 0, 0)])
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.1)
    return img


def create_cobblestone_texture():
    """Generate cobblestone texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (127, 127, 133, 255))
    
    # Create cobble pattern
    draw = ImageDraw.Draw(img)
    for _ in range(8):
        x = random.randint(1, TEXTURE_SIZE - 3)
        y = random.randint(1, TEXTURE_SIZE - 3)
        size = random.randint(2, 4)
        shade = random.choice([(110, 110, 115, 255), (140, 140, 145, 255)])
        draw.ellipse([x, y, x + size, y + size], fill=shade, outline=(90, 90, 95, 255))
    
    img = add_noise(img, 0.15)
    return img


def create_brick_texture():
    """Generate brick block texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (179, 77, 64, 255))
    
    # Draw brick pattern
    draw = ImageDraw.Draw(img)
    brick_height = 3
    brick_width = 5
    mortar = (140, 140, 140, 255)
    
    for y in range(0, TEXTURE_SIZE, brick_height + 1):
        offset = brick_width // 2 if (y // (brick_height + 1)) % 2 == 0 else 0
        for x in range(-brick_width, TEXTURE_SIZE + brick_width, brick_width + 1):
            draw.line([(x + offset, y), (x + brick_width + offset, y)], fill=mortar)
    
    for x in range(0, TEXTURE_SIZE, brick_width + 1):
        draw.line([(x, 0), (x, TEXTURE_SIZE)], fill=mortar)
    
    img = add_noise(img, 0.08)
    return img


def create_sandstone_texture():
    """Generate sandstone texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (232, 212, 156, 255))
    
    # Add horizontal layers
    draw = ImageDraw.Draw(img)
    for y in range(0, TEXTURE_SIZE, 3):
        shade = random.choice([(220, 200, 145, 255), (240, 220, 165, 255)])
        draw.line([(0, y), (TEXTURE_SIZE, y)], fill=shade)
    
    img = add_noise(img, 0.08)
    return img


def create_cactus_texture():
    """Generate cactus texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (92, 163, 64, 255))
    
    # Add vertical lines and spikes
    draw = ImageDraw.Draw(img)
    for x in range(0, TEXTURE_SIZE, 4):
        draw.line([(x, 0), (x, TEXTURE_SIZE)], fill=(70, 140, 50, 255))
    
    # Add some spike dots
    for _ in range(10):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        draw.point((x, y), fill=(50, 100, 40, 255))
    
    img = add_noise(img, 0.08)
    return img


def create_planks_texture():
    """Generate wooden planks texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (156, 117, 71, 255))
    
    # Add plank lines
    draw = ImageDraw.Draw(img)
    for y in range(0, TEXTURE_SIZE, 4):
        draw.line([(0, y), (TEXTURE_SIZE, y)], fill=(130, 100, 60, 255))
    
    # Add some wood grain
    for _ in range(20):
        x = random.randint(0, TEXTURE_SIZE - 1)
        y = random.randint(0, TEXTURE_SIZE - 1)
        shade = random.choice([(140, 105, 65, 255), (170, 130, 80, 255)])
        draw.point((x, y), fill=shade)
    
    img = add_noise(img, 0.08)
    return img


def create_crafting_table_texture():
    """Generate crafting table texture."""
    # Base is planks
    img = create_planks_texture()
    
    # Add crafting grid in center
    draw = ImageDraw.Draw(img)
    center = TEXTURE_SIZE // 2
    grid_size = 6
    draw.rectangle([center - grid_size // 2, center - grid_size // 2,
                   center + grid_size // 2, center + grid_size // 2],
                   outline=(100, 70, 40, 255))
    
    # Add cross for grid
    draw.line([(center, center - grid_size // 2), (center, center + grid_size // 2)],
              fill=(100, 70, 40, 255))
    draw.line([(center - grid_size // 2, center), (center + grid_size // 2, center)],
              fill=(100, 70, 40, 255))
    
    return img


def create_furnace_texture():
    """Generate furnace texture."""
    img = create_cobblestone_texture()
    
    # Add dark opening in center
    draw = ImageDraw.Draw(img)
    center = TEXTURE_SIZE // 2
    draw.rectangle([center - 3, center - 2, center + 3, center + 3],
                   fill=(30, 30, 30, 255), outline=(20, 20, 20, 255))
    
    return img


def create_chest_texture():
    """Generate chest texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (130, 85, 50, 255))
    
    # Add wood planks
    draw = ImageDraw.Draw(img)
    for y in range(0, TEXTURE_SIZE, 3):
        draw.line([(0, y), (TEXTURE_SIZE, y)], fill=(110, 70, 40, 255))
    
    # Add latch/lock in center
    center = TEXTURE_SIZE // 2
    draw.rectangle([center - 2, center - 1, center + 2, center + 2],
                   fill=(200, 180, 100, 255), outline=(150, 130, 70, 255))
    
    img = add_noise(img, 0.08)
    return img


def create_stick_item():
    """Generate stick item texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw diagonal stick
    stick_color = (120, 80, 50, 255)
    for i in range(TEXTURE_SIZE - 4):
        x = 4 + i
        y = TEXTURE_SIZE - 4 - i
        draw.point((x, y), fill=stick_color)
        draw.point((x + 1, y), fill=stick_color)
    
    return img


def create_tool_item(tool_type, material):
    """Generate tool item texture (pickaxe, axe, shovel, sword)."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Material colors
    material_colors = {
        'wood': (120, 80, 50, 255),
        'stone': (120, 120, 123, 255),
        'iron': (200, 200, 210, 255)
    }
    
    tool_color = material_colors.get(material, (150, 150, 150, 255))
    stick_color = (120, 80, 50, 255)
    
    center = TEXTURE_SIZE // 2
    
    if tool_type == 'pickaxe':
        # Draw pickaxe head
        draw.polygon([(center - 4, 4), (center + 4, 4), (center + 2, 6), (center - 2, 6)],
                    fill=tool_color, outline=(0, 0, 0, 255))
        # Draw handle
        for y in range(6, TEXTURE_SIZE - 2):
            draw.point((center, y), fill=stick_color)
    
    elif tool_type == 'axe':
        # Draw axe head
        draw.polygon([(center - 1, 4), (center + 4, 4), (center + 4, 7), (center - 1, 7)],
                    fill=tool_color, outline=(0, 0, 0, 255))
        # Draw handle
        for y in range(7, TEXTURE_SIZE - 2):
            draw.point((center - 1, y), fill=stick_color)
    
    elif tool_type == 'shovel':
        # Draw shovel head
        draw.polygon([(center - 2, 4), (center + 2, 4), (center + 1, 7), (center - 1, 7)],
                    fill=tool_color, outline=(0, 0, 0, 255))
        # Draw handle
        for y in range(7, TEXTURE_SIZE - 2):
            draw.point((center, y), fill=stick_color)
    
    elif tool_type == 'sword':
        # Draw blade
        draw.polygon([(center - 1, 3), (center + 1, 3), (center + 1, 10), (center - 1, 10)],
                    fill=tool_color, outline=(0, 0, 0, 255))
        # Draw guard
        draw.line([(center - 3, 10), (center + 3, 10)], fill=(100, 70, 40, 255), width=2)
        # Draw handle
        for y in range(11, TEXTURE_SIZE - 2):
            draw.point((center, y), fill=stick_color)
    
    return img


def create_iron_ingot():
    """Generate iron ingot texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw ingot shape
    center_x = TEXTURE_SIZE // 2
    center_y = TEXTURE_SIZE // 2
    
    ingot_color = (200, 200, 210, 255)
    dark_edge = (150, 150, 160, 255)
    
    # Main ingot body
    draw.rectangle([center_x - 4, center_y - 2, center_x + 4, center_y + 2],
                  fill=ingot_color, outline=dark_edge)
    
    # Add shine
    draw.line([(center_x - 3, center_y - 1), (center_x + 3, center_y - 1)],
             fill=(230, 230, 240, 255))
    
    return img


def create_raw_meat():
    """Generate raw meat texture (beef/mutton)."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw meat blob
    meat_color = (179, 77, 77, 255)
    dark_meat = (150, 60, 60, 255)
    
    center = TEXTURE_SIZE // 2
    
    # Irregular meat shape
    points = [
        (center - 4, center - 2),
        (center - 3, center - 4),
        (center + 1, center - 4),
        (center + 4, center - 1),
        (center + 3, center + 3),
        (center - 1, center + 4),
        (center - 4, center + 2)
    ]
    
    draw.polygon(points, fill=meat_color, outline=dark_meat)
    
    # Add some texture
    for _ in range(8):
        x = random.randint(center - 3, center + 3)
        y = random.randint(center - 3, center + 3)
        draw.point((x, y), fill=dark_meat)
    
    return img


def create_raw_chicken():
    """Generate raw chicken texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw chicken meat
    chicken_color = (222, 194, 171, 255)
    dark_chicken = (200, 170, 150, 255)
    
    center = TEXTURE_SIZE // 2
    
    # Chicken drumstick shape
    # Body
    draw.ellipse([center - 3, center - 3, center + 3, center + 2],
                fill=chicken_color, outline=dark_chicken)
    
    # Leg bone
    draw.line([(center, center + 2), (center, center + 5)],
             fill=(230, 230, 230, 255), width=2)
    
    return img


def create_raw_pork():
    """Generate raw pork texture."""
    img = Image.new('RGBA', (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw pork chop
    pork_color = (242, 175, 175, 255)
    dark_pork = (220, 150, 150, 255)
    
    center = TEXTURE_SIZE // 2
    
    # Pork chop shape
    points = [
        (center - 3, center - 3),
        (center + 3, center - 3),
        (center + 4, center + 1),
        (center + 2, center + 4),
        (center - 2, center + 4),
        (center - 4, center + 1)
    ]
    
    draw.polygon(points, fill=pork_color, outline=dark_pork)
    
    # Add fat marbling
    for _ in range(5):
        x = random.randint(center - 2, center + 2)
        y = random.randint(center - 2, center + 2)
        draw.point((x, y), fill=(255, 255, 255, 255))
    
    return img


def generate_all_assets():
    """Generate all game assets."""
    print("=" * 50)
    print("Blockforge Asset Generator")
    print("=" * 50)
    
    # Ensure directories exist
    ensure_directories()
    
    base_path = os.path.dirname(__file__)
    
    # Block textures
    print("\n[BLOCKS] Generating block textures...")
    blocks = {
        'grass.png': create_grass_texture(),
        'dirt.png': create_dirt_texture(),
        'stone.png': create_stone_texture(),
        'bedrock.png': create_bedrock_texture(),
        'sand.png': create_sand_texture(),
        'wood.png': create_wood_texture(),
        'wood_top.png': create_wood_top_texture(),
        'leaves.png': create_leaves_texture(),
        'cobblestone.png': create_cobblestone_texture(),
        'brick.png': create_brick_texture(),
        'sandstone.png': create_sandstone_texture(),
        'cactus.png': create_cactus_texture(),
        'planks.png': create_planks_texture(),
        'crafting_table.png': create_crafting_table_texture(),
        'furnace.png': create_furnace_texture(),
        'chest.png': create_chest_texture(),
    }
    
    for filename, texture in blocks.items():
        path = os.path.join(base_path, 'blocks', filename)
        texture.save(path)
        print(f"  ✓ Created: blocks/{filename}")
    
    # Item textures
    print("\n[ITEMS] Generating item textures...")
    items = {
        'stick.png': create_stick_item(),
        'pickaxe_wood.png': create_tool_item('pickaxe', 'wood'),
        'pickaxe_stone.png': create_tool_item('pickaxe', 'stone'),
        'pickaxe_iron.png': create_tool_item('pickaxe', 'iron'),
        'axe_wood.png': create_tool_item('axe', 'wood'),
        'axe_stone.png': create_tool_item('axe', 'stone'),
        'axe_iron.png': create_tool_item('axe', 'iron'),
        'shovel_wood.png': create_tool_item('shovel', 'wood'),
        'shovel_stone.png': create_tool_item('shovel', 'stone'),
        'shovel_iron.png': create_tool_item('shovel', 'iron'),
        'sword_wood.png': create_tool_item('sword', 'wood'),
        'sword_stone.png': create_tool_item('sword', 'stone'),
        'sword_iron.png': create_tool_item('sword', 'iron'),
        'iron_ingot.png': create_iron_ingot(),
    }
    
    for filename, texture in items.items():
        path = os.path.join(base_path, 'items', filename)
        texture.save(path)
        print(f"  ✓ Created: items/{filename}")
    
    # Meat/Food textures
    print("\n[MEAT] Generating meat/food textures...")
    meats = {
        'raw_meat.png': create_raw_meat(),
        'raw_chicken.png': create_raw_chicken(),
        'raw_pork.png': create_raw_pork(),
    }
    
    for filename, texture in meats.items():
        path = os.path.join(base_path, 'meat', filename)
        texture.save(path)
        print(f"  ✓ Created: meat/{filename}")
    
    print("\n" + "=" * 50)
    print(f"Asset generation complete!")
    print(f"Total blocks: {len(blocks)}")
    print(f"Total items: {len(items)}")
    print(f"Total meat/food: {len(meats)}")
    print(f"Grand total: {len(blocks) + len(items) + len(meats)} textures")
    print("=" * 50)


if __name__ == '__main__':
    # Set random seed for consistent generation
    random.seed(42)
    generate_all_assets()
