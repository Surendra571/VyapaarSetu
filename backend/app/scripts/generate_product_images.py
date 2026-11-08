"""
Generate high-quality, professional commercial FMCG product images for VyapaarSetu.
Outputs both modern WebP images and SVG vectors to frontend/public/images/products/.
"""

import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "frontend", "public", "images", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH = 800
HEIGHT = 800

def create_studio_background():
    """Create a soft, neutral professional studio gradient background."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Radial studio lighting: slightly brighter at center, soft cool grey at corners
    for r in range(int(WIDTH * 0.8), 0, -5):
        alpha = int(255 - (r / (WIDTH * 0.8)) * 18)
        color = (248, 250, 252, alpha)
        # soft circle
        cx, cy = WIDTH // 2, HEIGHT // 2 - 40
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    
    # Ground shadow plane at the bottom
    ground = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(ground)
    gdraw.ellipse([100, 620, 700, 720], fill=(210, 218, 226, 120))
    ground = ground.filter(ImageFilter.GaussianBlur(radius=25))
    img.alpha_composite(ground)
    return img


def generate_biscuit_image():
    """
    SKU-BS-075: Glucose biscuit 75g
    Realistic biscuit packet (red/gold FMCG packaging) and golden embossed glucose biscuits.
    """
    img = create_studio_background()
    
    # Overlay layer for drawing
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # --- 1. PACKET GROUND SHADOW ---
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([140, 560, 560, 650], fill=(40, 50, 60, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22))
    img.alpha_composite(shadow)
    
    # --- 2. PACKET BODY (Parle-G / Glucose style packaging) ---
    # Tilted/perspective rectangular pouch: [180, 220] to [520, 580]
    px0, py0, px1, py1 = 180, 200, 520, 560
    
    # Packet Main Background (Yellow/Golden gradient)
    packet_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(packet_layer)
    
    # Rounded rectangular packet
    pdraw.rounded_rectangle([px0, py0, px1, py1], radius=16, fill=(245, 190, 35, 255))
    
    # Realistic shading / packaging curve
    for i in range(px0, px1, 2):
        rel = (i - px0) / (px1 - px0)
        # Specular highlight on left third
        highlight = math.sin(rel * math.pi) ** 2
        col = (255, 235, 120, int(highlight * 70))
        pdraw.line([(i, py0), (i, py1)], fill=col, width=2)
    
    # Top and Bottom crimp seals
    # Top crimp (silver/white foil serrated edge)
    crimp_top = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(crimp_top)
    cdraw.rectangle([px0 - 10, py0 - 15, px1 + 10, py0 + 5], fill=(225, 230, 235, 255))
    for x in range(px0 - 10, px1 + 10, 6):
        cdraw.line([(x, py0 - 15), (x, py0 + 5)], fill=(160, 170, 180, 180), width=2)
    
    # Bottom crimp
    cdraw.rectangle([px0 - 10, py1 - 5, px1 + 10, py1 + 15], fill=(225, 230, 235, 255))
    for x in range(px0 - 10, px1 + 10, 6):
        cdraw.line([(x, py1 - 5), (x, py1 + 15)], fill=(160, 170, 180, 180), width=2)
    
    packet_layer.alpha_composite(crimp_top)
    
    # Red brand banner across packet
    pdraw.rectangle([px0, 310, px1, 410], fill=(205, 30, 40, 255))
    # Golden borders on red banner
    pdraw.line([(px0, 310), (px1, 310)], fill=(255, 220, 80, 255), width=4)
    pdraw.line([(px0, 410), (px1, 410)], fill=(255, 220, 80, 255), width=4)
    
    # Text on banner: "GLUCOSE"
    # Using clean bitmap font / fallback or default
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 46)
        font_sub = ImageFont.truetype("arialbd.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_biscuit = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font_large = font_sub = font_small = font_biscuit = ImageFont.load_default()
        
    pdraw.text((px0 + 50, 325), "GLUCOSE", fill=(255, 255, 255, 255), font=font_large)
    pdraw.text((px0 + 75, 375), "BISCUITS", fill=(255, 235, 140, 255), font=font_sub)
    
    # Weight badge (75g)
    pdraw.rounded_rectangle([px0 + 20, py0 + 20, px0 + 130, py0 + 65], radius=10, fill=(205, 30, 40, 255))
    pdraw.text((px0 + 35, py0 + 28), "NET WT 75g", fill=(255, 255, 255, 255), font=font_small)
    
    # Wheat / energy icon indicator
    pdraw.text((px0 + 30, 440), "ENERGY & NOURISHMENT", fill=(150, 90, 10, 255), font=font_small)
    pdraw.text((px0 + 30, 465), "Original Malt & Milk Recipe", fill=(120, 70, 10, 220), font=font_small)
    
    # Veg icon (Green square + circle)
    pdraw.rectangle([px1 - 45, py0 + 20, px1 - 20, py0 + 45], outline=(22, 101, 52, 255), width=2, fill=(255, 255, 255, 255))
    pdraw.ellipse([px1 - 38, py0 + 27, px1 - 27, py0 + 38], fill=(22, 101, 52, 255))
    
    # Composite packet onto main image
    img.alpha_composite(packet_layer)
    
    # --- 3. REALISTIC BAKED GLUCOSE BISCUITS IN FRONT ---
    # Biscuit 1 (standing tilted against packet)
    # Biscuit 2 (lying flat on ground)
    
    biscuit_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(biscuit_layer)
    
    # Shadow under biscuit 1
    sdraw2 = ImageDraw.Draw(shadow)
    sdraw2.ellipse([430, 600, 730, 690], fill=(40, 45, 50, 120))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(radius=16)))
    
    def draw_single_biscuit(bx0, by0, bx1, by1, angle=0):
        # Biscuit surface: Warm baked biscuit color #D89F53 with soft bevel
        b_surf = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
        d = ImageDraw.Draw(b_surf)
        w, h = bx1 - bx0, by1 - by0
        
        # Base biscuit dough
        d.rounded_rectangle([2, 2, w - 2, h - 2], radius=14, fill=(218, 160, 85, 255), outline=(175, 115, 45, 255), width=2)
        # Inner baked rim
        d.rounded_rectangle([8, 8, w - 8, h - 8], radius=8, outline=(190, 130, 55, 255), width=2)
        
        # Scalloped fluted dots around border
        for x in range(16, w - 16, 18):
            d.ellipse([x - 2, 5, x + 2, 9], fill=(160, 100, 40, 255))
            d.ellipse([x - 2, h - 9, x + 2, h - 5], fill=(160, 100, 40, 255))
        for y in range(16, h - 16, 16):
            d.ellipse([5, y - 2, 9, y + 2], fill=(160, 100, 40, 255))
            d.ellipse([w - 9, y - 2, w - 5, y + 2], fill=(160, 100, 40, 255))
            
        # Characteristic lattice perforations / dots in center
        for rx in range(35, w - 35, 28):
            for ry in range(25, h - 25, 22):
                d.ellipse([rx - 2, ry - 2, rx + 2, ry + 2], fill=(150, 90, 35, 255))
                
        # Center stamped brand label: "GLUCOSE"
        d.text((w // 2 - 45, h // 2 - 10), "GLUCOSE", fill=(150, 90, 35, 255), font=font_biscuit)
        
        # Subtle bake texture
        return b_surf

    # Biscuit 1 (leaning in front right)
    b1 = draw_single_biscuit(0, 0, 240, 160)
    b1_rot = b1.rotate(14, expand=True, resample=Image.BICUBIC)
    biscuit_layer.paste(b1_rot, (440, 450), b1_rot)
    
    # Biscuit 2 (lying flat in foreground left)
    b2 = draw_single_biscuit(0, 0, 220, 150)
    b2_rot = b2.rotate(-8, expand=True, resample=Image.BICUBIC)
    biscuit_layer.paste(b2_rot, (320, 540), b2_rot)
    
    # Few golden biscuit crumbs on the floor
    crumbs = [(300, 640, 5), (312, 645, 3), (330, 655, 4), (560, 630, 4), (575, 635, 6), (590, 625, 3), (480, 660, 5)]
    for cx, cy, cr in crumbs:
        bdraw.ellipse([cx, cy, cx + cr, cy + cr], fill=(195, 135, 60, 240))
        
    img.alpha_composite(biscuit_layer)
    return img.convert("RGB")


def generate_detergent_image():
    """
    SKU-DT-1KG: Detergent powder 1kg
    Realistic detergent powder pouch in vibrant ocean blue/cyan with fresh sparkles & scoop of white powder.
    """
    img = create_studio_background()
    
    # Ground shadow for pouch
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([140, 570, 600, 670], fill=(30, 45, 65, 95))
    # Scoop shadow
    sdraw.ellipse([450, 600, 720, 680], fill=(30, 45, 65, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
    img.alpha_composite(shadow)
    
    # Stand-up Detergent Pouch: [200, 160] to [520, 570]
    pouch = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pouch)
    
    px0, py0, px1, py1 = 200, 160, 510, 570
    
    # Pouch base contour (stand-up pouch shape: slightly wider base, tapered top with rounded edges)
    # Background gradient: Deep cobalt blue to bright cyan
    pouch_shape = [
        (px0 + 35, py0),
        (px1 - 35, py0),
        (px1, py1 - 30),
        (px1 - 20, py1),
        (px0 + 20, py1),
        (px0, py1 - 30),
    ]
    pdraw.polygon(pouch_shape, fill=(2, 132, 199, 255))
    
    # Pouch shading & gradient curves
    for y in range(py0, py1):
        rel_y = (y - py0) / (py1 - py0)
        # Deep blue at bottom, dynamic royal blue at top
        r = int(14 + rel_y * 10)
        g = int(80 + rel_y * 70)
        b = int(190 + (1 - rel_y) * 40)
        pdraw.line([(px0 + 10, y), (px1 - 10, y)], fill=(r, g, b, 255), width=2)
        
    # Cylindrical specular light sweep
    for x in range(px0 + 40, px0 + 150):
        highlight = math.sin((x - px0 - 40) / 110 * math.pi) ** 2
        pdraw.line([(x, py0 + 15), (x, py1 - 15)], fill=(255, 255, 255, int(highlight * 70)), width=2)
        
    # Top heat seal strip (metallic silver / dark blue ridged)
    pdraw.rectangle([px0 + 25, py0, px1 - 25, py0 + 24], fill=(224, 231, 255, 255))
    for x in range(px0 + 25, px1 - 25, 5):
        pdraw.line([(x, py0), (x, py0 + 24)], fill=(147, 197, 253, 200), width=1)
    # Notch
    pdraw.polygon([(px0 + 20, py0 + 12), (px0 + 28, py0 + 8), (px0 + 28, py0 + 16)], fill=(248, 250, 252, 255))
    
    # Graphic Burst / Wave on Pouch
    pdraw.ellipse([px0 - 60, py0 + 140, px1 + 60, py1 + 20], fill=(255, 255, 255, 240))
    pdraw.ellipse([px0 - 50, py0 + 160, px1 + 50, py1 + 10], fill=(238, 246, 255, 255))
    
    # Dynamic swirl / ocean splash ribbon
    splash_poly = [
        (px0 + 10, 340),
        (px1 - 10, 310),
        (px1 - 10, 420),
        (px0 + 10, 450),
    ]
    pdraw.polygon(splash_poly, fill=(14, 165, 233, 255))
    
    try:
        f_hero = ImageFont.truetype("arialbd.ttf", 44)
        f_sub = ImageFont.truetype("arialbd.ttf", 26)
        f_badge = ImageFont.truetype("arialbd.ttf", 20)
        f_small = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        f_hero = f_sub = f_badge = f_small = ImageFont.load_default()
        
    # Pouch Typography
    pdraw.text((px0 + 40, py0 + 45), "ACTIVE CLEAN", fill=(255, 255, 255, 255), font=f_sub)
    pdraw.text((px0 + 35, 330), "DETERGENT", fill=(255, 255, 255, 255), font=f_hero)
    pdraw.text((px0 + 55, 385), "POWDER", fill=(254, 240, 138, 255), font=f_sub)
    
    # Weight Tag (1 kg)
    pdraw.rounded_rectangle([px0 + 35, 470, px0 + 155, 520], radius=12, fill=(239, 68, 68, 255))
    pdraw.text((px0 + 52, 482), "1 kg PACK", fill=(255, 255, 255, 255), font=f_badge)
    
    # Feature badges: "Tough Stain Removal"
    pdraw.text((px0 + 175, 485), "• Tough Stain Removal", fill=(15, 23, 42, 255), font=f_small)
    pdraw.text((px0 + 175, 508), "• Fresh Floral Fragrance", fill=(15, 23, 42, 255), font=f_small)
    
    # Sparkling stars / crystal icons on pouch
    sparkles = [(px1 - 70, py0 + 75, 12), (px0 + 60, py0 + 100, 8), (px1 - 50, 330, 14), (px1 - 90, 430, 10)]
    for sx, sy, sr in sparkles:
        pdraw.line([(sx - sr, sy), (sx + sr, sy)], fill=(255, 255, 255, 255), width=3)
        pdraw.line([(sx, sy - sr), (sx, sy + sr)], fill=(255, 255, 255, 255), width=3)
        pdraw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 255, 255, 255))
        
    img.alpha_composite(pouch)
    
    # --- 3. BLUE MEASURING SCOOP & HEAP OF WHITE POWDER IN FOREGROUND ---
    scoop_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sdraw2 = ImageDraw.Draw(scoop_layer)
    
    # Blue translucent plastic scoop
    # Handle: [560, 520] to [670, 480]
    sdraw2.line([(550, 540), (660, 480)], fill=(37, 99, 235, 240), width=16)
    # Scoop Cup: Oval bowl filled with powder
    sdraw2.ellipse([430, 520, 580, 630], fill=(29, 78, 216, 255), outline=(147, 197, 253, 255), width=3)
    
    # Granular white washing powder inside scoop and spilled gracefully
    sdraw2.ellipse([440, 525, 570, 615], fill=(255, 255, 255, 255))
    # Soft powder gradient inside scoop
    sdraw2.ellipse([450, 535, 560, 605], fill=(241, 245, 249, 255))
    
    # Spilled powder mound on the table
    sdraw2.ellipse([340, 610, 530, 665], fill=(255, 255, 255, 255))
    sdraw2.ellipse([360, 620, 510, 655], fill=(248, 250, 252, 255))
    
    # Blue and red active oxygen speckles in the detergent powder
    import random
    random.seed(42)
    for _ in range(70):
        gx = random.randint(350, 560)
        gy = random.randint(535, 650)
        col = random.choice([
            (2, 132, 199, 240),  # Blue speckle
            (239, 68, 68, 220),   # Red speckle
            (203, 213, 225, 255), # Grey speckle
        ])
        sdraw2.ellipse([gx, gy, gx + 3, gy + 3], fill=col)
        
    img.alpha_composite(scoop_layer)
    return img.convert("RGB")


def generate_tea_image():
    """
    SKU-TE-250: Tea leaf 250g
    Realistic tea packet (rich emerald/gold foil pouch) and loose CTC black tea granules with fresh tea leaves.
    """
    img = create_studio_background()
    
    # Ground shadows
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    # Pouch shadow
    sdraw.ellipse([160, 560, 560, 660], fill=(30, 45, 35, 95))
    # Bowl & leaf shadow
    sdraw.ellipse([420, 590, 710, 680], fill=(30, 45, 35, 115))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
    img.alpha_composite(shadow)
    
    # Stand-up Emerald Tea Foil Pouch: [200, 170] to [510, 570]
    pouch = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pouch)
    
    px0, py0, px1, py1 = 200, 170, 510, 570
    
    # Pouch contour
    pouch_shape = [
        (px0 + 30, py0),
        (px1 - 30, py0),
        (px1, py1 - 25),
        (px1 - 20, py1),
        (px0 + 20, py1),
        (px0, py1 - 25),
    ]
    pdraw.polygon(pouch_shape, fill=(6, 78, 59, 255))
    
    # Rich emerald metallic green gradient
    for y in range(py0, py1):
        rel_y = (y - py0) / (py1 - py0)
        r = int(4 + rel_y * 12)
        g = int(60 + (1 - abs(rel_y - 0.5) * 2) * 55)
        b = int(35 + rel_y * 15)
        pdraw.line([(px0 + 8, y), (px1 - 8, y)], fill=(r, g, b, 255), width=2)
        
    # Vertical golden satin sheen
    for x in range(px0 + 50, px0 + 160):
        highlight = math.sin((x - px0 - 50) / 110 * math.pi) ** 2
        pdraw.line([(x, py0 + 10), (x, py1 - 10)], fill=(245, 190, 40, int(highlight * 60)), width=2)
        
    # Gold foil frame & borders
    pdraw.rectangle([px0 + 25, py0 + 25, px1 - 25, py1 - 25], outline=(217, 119, 6, 255), width=3)
    pdraw.rectangle([px0 + 30, py0 + 30, px1 - 30, py1 - 30], outline=(245, 190, 40, 200), width=1)
    
    # Top heat seal
    pdraw.rectangle([px0 + 20, py0, px1 - 20, py0 + 22], fill=(217, 119, 6, 255))
    for x in range(px0 + 20, px1 - 20, 6):
        pdraw.line([(x, py0), (x, py0 + 22)], fill=(254, 240, 138, 220), width=1)
        
    try:
        f_title = ImageFont.truetype("arialbd.ttf", 36)
        f_brand = ImageFont.truetype("arialbd.ttf", 26)
        f_sub = ImageFont.truetype("arial.ttf", 16)
        f_badge = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        f_title = f_brand = f_sub = f_badge = ImageFont.load_default()
        
    # Gold decorative emblem / tea cup icon
    pdraw.ellipse([px0 + 120, py0 + 55, px1 - 120, py0 + 125], outline=(245, 190, 40, 255), width=2)
    pdraw.text((px0 + 128, py0 + 78), "100% PURE", fill=(254, 240, 138, 255), font=f_badge)
    
    # Typography
    pdraw.text((px0 + 55, py0 + 150), "PREMIUM CTC", fill=(245, 190, 40, 255), font=f_brand)
    pdraw.text((px0 + 70, py0 + 195), "TEA LEAF", fill=(255, 255, 255, 255), font=f_title)
    
    # Red & gold banner for 250g
    pdraw.rounded_rectangle([px0 + 40, 290, px1 - 40, 345], radius=10, fill=(185, 28, 28, 255), outline=(245, 190, 40, 255), width=2)
    pdraw.text((px0 + 75, 305), "NET WEIGHT: 250g", fill=(255, 255, 255, 255), font=f_badge)
    
    pdraw.text((px0 + 45, 375), "• Rich Amber Liquor", fill=(240, 253, 244, 255), font=f_sub)
    pdraw.text((px0 + 45, 405), "• Authentic Strong Kadak Chai", fill=(240, 253, 244, 255), font=f_sub)
    pdraw.text((px0 + 45, 435), "• Harvested from Fresh Gardens", fill=(240, 253, 244, 255), font=f_sub)
    
    # Veg Mark
    pdraw.rectangle([px1 - 55, py0 + 35, px1 - 35, py0 + 55], outline=(34, 197, 94, 255), width=2, fill=(255, 255, 255, 255))
    pdraw.ellipse([px1 - 49, py0 + 41, px1 - 41, py0 + 49], fill=(34, 197, 94, 255))
    
    img.alpha_composite(pouch)
    
    # --- 3. LOOSE CTC TEA GRANULES & FRESH GREEN TEA LEAF IN FOREGROUND ---
    tea_elements = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tea_elements)
    
    # Black ceramic tasting dish with tea grains
    tdraw.ellipse([420, 520, 680, 640], fill=(28, 25, 23, 255), outline=(68, 64, 60, 255), width=4)
    # Inside bowl (pile of granular CTC black tea)
    tdraw.ellipse([435, 530, 665, 625], fill=(35, 20, 12, 255))
    
    # Grain texture
    import random
    random.seed(99)
    for _ in range(400):
        tx = random.randint(440, 660)
        ty = random.randint(535, 620)
        t_col = random.choice([
            (24, 14, 8, 255),
            (50, 26, 12, 255),
            (68, 42, 18, 255),
            (15, 8, 4, 255),
        ])
        tdraw.ellipse([tx, ty, tx + 4, ty + 4], fill=t_col)
        
    # Scattered granules outside the bowl
    for _ in range(120):
        sx = random.randint(350, 520)
        sy = random.randint(600, 670)
        tdraw.ellipse([sx, sy, sx + 3, sy + 3], fill=(30, 18, 10, 240))
        
    # Two fresh green tea leaves lying beside the bowl
    # Leaf 1 (Fresh vibrant green)
    leaf1 = [
        (350, 560), (390, 530), (440, 545), (460, 590), (420, 610), (370, 590)
    ]
    tdraw.polygon(leaf1, fill=(22, 163, 74, 255), outline=(21, 128, 61, 255))
    # Leaf vein
    tdraw.line([(350, 560), (460, 590)], fill=(134, 239, 172, 255), width=2)
    
    # Leaf 2 (Smaller bud)
    leaf2 = [
        (330, 595), (360, 575), (395, 590), (375, 625), (340, 615)
    ]
    tdraw.polygon(leaf2, fill=(34, 197, 94, 255), outline=(22, 101, 52, 255))
    tdraw.line([(330, 595), (395, 590)], fill=(187, 247, 208, 255), width=2)
    
    img.alpha_composite(tea_elements)
    return img.convert("RGB")


def generate_placeholder_image():
    """Generic representative FMCG packaging silhouette on neutral background."""
    img = create_studio_background()
    box_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(box_layer)
    
    # Ground shadow
    sdraw = ImageDraw.Draw(img)
    sdraw.ellipse([200, 580, 600, 670], fill=(200, 210, 220, 180))
    
    # Stylized clean product packaging carton
    bx0, py0, bx1, py1 = 260, 220, 540, 580
    bdraw.rounded_rectangle([bx0, py0, bx1, py1], radius=24, fill=(241, 245, 249, 255), outline=(203, 213, 225, 255), width=3)
    
    # Minimalist product silhouette
    bdraw.rounded_rectangle([bx0 + 40, py0 + 50, bx1 - 40, py0 + 170], radius=16, fill=(226, 232, 240, 255))
    bdraw.rounded_rectangle([bx0 + 60, py0 + 200, bx1 - 60, py0 + 225], radius=6, fill=(203, 213, 225, 255))
    bdraw.rounded_rectangle([bx0 + 80, py0 + 240, bx1 - 80, py0 + 258], radius=6, fill=(226, 232, 240, 255))
    
    # FMCG Wholesale seal badge
    bdraw.ellipse([bx0 + 100, py1 - 120, bx1 - 100, py1 - 40], fill=(16, 185, 129, 255))
    try:
        f_seal = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        f_seal = ImageFont.load_default()
    bdraw.text((bx0 + 105, py1 - 88), "VYAPAARSETU", fill=(255, 255, 255, 255), font=f_seal)
    
    img.alpha_composite(box_layer)
    return img.convert("RGB")


# Generate and save WebP files
print(f"Generating WebP commercial product images in {OUTPUT_DIR}...")
biscuit = generate_biscuit_image()
biscuit.save(os.path.join(OUTPUT_DIR, "SKU-BS-075.webp"), "WEBP", quality=92)
biscuit.save(os.path.join(OUTPUT_DIR, "glucose-biscuit-75g.webp"), "WEBP", quality=92)

detergent = generate_detergent_image()
detergent.save(os.path.join(OUTPUT_DIR, "SKU-DT-1KG.webp"), "WEBP", quality=92)
detergent.save(os.path.join(OUTPUT_DIR, "detergent-powder-1kg.webp"), "WEBP", quality=92)

tea = generate_tea_image()
tea.save(os.path.join(OUTPUT_DIR, "SKU-TE-250.webp"), "WEBP", quality=92)
tea.save(os.path.join(OUTPUT_DIR, "tea-leaf-250g.webp"), "WEBP", quality=92)

placeholder = generate_placeholder_image()
placeholder.save(os.path.join(OUTPUT_DIR, "placeholder.webp"), "WEBP", quality=92)
placeholder.save(os.path.join(OUTPUT_DIR, "packaged-food.webp"), "WEBP", quality=92)
placeholder.save(os.path.join(OUTPUT_DIR, "home-care.webp"), "WEBP", quality=92)

print("Product images generated successfully!")
