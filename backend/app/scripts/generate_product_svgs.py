"""
Generate clean, scalable vector SVG product illustrations for VyapaarSetu.
Outputs to frontend/public/images/products/.
"""

import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "frontend", "public", "images", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Glucose Biscuit 75g (SKU-BS-075)
biscuit_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGlow" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="70%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#edf2f7"/>
    </radialGradient>
    <linearGradient id="pouchGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#eab308"/>
      <stop offset="25%" stop-color="#fde047"/>
      <stop offset="50%" stop-color="#eab308"/>
      <stop offset="85%" stop-color="#ca8a04"/>
      <stop offset="100%" stop-color="#a16207"/>
    </linearGradient>
    <linearGradient id="redBand" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#dc2626"/>
      <stop offset="50%" stop-color="#ef4444"/>
      <stop offset="100%" stop-color="#b91c1c"/>
    </linearGradient>
    <linearGradient id="biscuitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fed7aa"/>
      <stop offset="50%" stop-color="#f97316"/>
      <stop offset="100%" stop-color="#c2410c"/>
    </linearGradient>
    <filter id="dropShadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="16" stdDeviation="16" flood-color="#1e293b" flood-opacity="0.14"/>
    </filter>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#0f172a" flood-opacity="0.18"/>
    </filter>
  </defs>

  <!-- Studio Background -->
  <rect width="500" height="500" rx="20" fill="url(#bgGlow)"/>

  <!-- Ground Shadows -->
  <ellipse cx="250" cy="425" rx="170" ry="24" fill="#cbd5e1" opacity="0.6"/>
  <ellipse cx="230" cy="425" rx="130" ry="16" fill="#94a3b8" opacity="0.5"/>

  <!-- Biscuit Packet (Pouch) -->
  <g filter="url(#dropShadow)">
    <!-- Top & Bottom Crimp Seals -->
    <path d="M 120 120 L 340 120 L 340 135 L 120 135 Z" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1.5"/>
    <path d="M 120 375 L 340 375 L 340 390 L 120 390 Z" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1.5"/>

    <!-- Packet Main Body -->
    <rect x="120" y="130" width="220" height="250" rx="12" fill="url(#pouchGrad)"/>

    <!-- Highlights & Sheen -->
    <path d="M 160 130 L 190 130 L 190 380 L 160 380 Z" fill="#ffffff" opacity="0.25"/>

    <!-- Brand Red Banner -->
    <rect x="120" y="205" width="220" height="70" fill="url(#redBand)"/>
    <line x1="120" y1="205" x2="340" y2="205" stroke="#fef08a" stroke-width="2.5"/>
    <line x1="120" y1="275" x2="340" y2="275" stroke="#fef08a" stroke-width="2.5"/>

    <!-- Banner Typography -->
    <text x="230" y="246" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="28" fill="#ffffff" letter-spacing="2">GLUCOSE</text>
    <text x="230" y="268" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="13" fill="#fef08a" letter-spacing="1.5">BISCUITS</text>

    <!-- Net Weight Badge -->
    <rect x="135" y="145" width="75" height="26" rx="6" fill="#dc2626"/>
    <text x="172" y="162" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="800" font-size="11" fill="#ffffff">75g PACK</text>

    <!-- Subtitle on pack -->
    <text x="230" y="315" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="700" font-size="11" fill="#78350f">ENERGY &amp; NOURISHMENT</text>
    <text x="230" y="332" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="500" font-size="9" fill="#92400e">Traditional Malt Recipe</text>

    <!-- Vegetarian Mark -->
    <rect x="305" y="145" width="20" height="20" rx="3" fill="#ffffff" stroke="#16a34a" stroke-width="2"/>
    <circle cx="315" cy="155" r="5" fill="#16a34a"/>
  </g>

  <!-- Foreground Realistic Baked Glucose Biscuits -->
  <!-- Biscuit 1 (Standing / Leaning) -->
  <g transform="translate(260, 270) rotate(12)" filter="url(#softShadow)">
    <!-- Biscuit Base -->
    <rect x="0" y="0" width="150" height="105" rx="10" fill="#f59e0b" stroke="#b45309" stroke-width="2.5"/>
    <!-- Inner Rim -->
    <rect x="8" y="8" width="134" height="89" rx="6" fill="#fbbf24" stroke="#d97706" stroke-width="1.5"/>

    <!-- Embossed Border Dots -->
    <circle cx="20" cy="5" r="2.5" fill="#b45309"/>
    <circle cx="45" cy="5" r="2.5" fill="#b45309"/>
    <circle cx="75" cy="5" r="2.5" fill="#b45309"/>
    <circle cx="105" cy="5" r="2.5" fill="#b45309"/>
    <circle cx="130" cy="5" r="2.5" fill="#b45309"/>

    <circle cx="20" cy="100" r="2.5" fill="#b45309"/>
    <circle cx="45" cy="100" r="2.5" fill="#b45309"/>
    <circle cx="75" cy="100" r="2.5" fill="#b45309"/>
    <circle cx="105" cy="100" r="2.5" fill="#b45309"/>
    <circle cx="130" cy="100" r="2.5" fill="#b45309"/>

    <!-- Center Stamped Brand -->
    <text x="75" y="58" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="16" fill="#92400e" letter-spacing="1">GLUCOSE</text>
    
    <!-- Grid Perforations -->
    <circle cx="35" cy="30" r="2" fill="#92400e"/>
    <circle cx="115" cy="30" r="2" fill="#92400e"/>
    <circle cx="35" cy="75" r="2" fill="#92400e"/>
    <circle cx="115" cy="75" r="2" fill="#92400e"/>
  </g>

  <!-- Biscuit 2 (Foreground Flat) -->
  <g transform="translate(180, 340) rotate(-6)" filter="url(#softShadow)">
    <rect x="0" y="0" width="140" height="95" rx="8" fill="#d97706" stroke="#92400e" stroke-width="2"/>
    <rect x="7" y="7" width="126" height="81" rx="5" fill="#f59e0b" stroke="#b45309" stroke-width="1.2"/>
    <text x="70" y="54" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="900" font-size="14" fill="#78350f" letter-spacing="1">GLUCOSE</text>
  </g>

  <!-- Golden Crumbs -->
  <circle cx="160" cy="425" r="3" fill="#b45309"/>
  <circle cx="172" cy="430" r="2" fill="#d97706"/>
  <circle cx="380" cy="420" r="3.5" fill="#b45309"/>
  <circle cx="395" cy="426" r="2.5" fill="#f59e0b"/>
</svg>"""

# 2. Detergent Powder 1kg (SKU-DT-1KG)
detergent_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGlowDt" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="70%" stop-color="#f0f9ff"/>
      <stop offset="100%" stop-color="#e0f2fe"/>
    </radialGradient>
    <linearGradient id="pouchBlue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="40%" stop-color="#0369a1"/>
      <stop offset="80%" stop-color="#1e3a8a"/>
      <stop offset="100%" stop-color="#172554"/>
    </linearGradient>
    <linearGradient id="swirlGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <filter id="dropShadowDt" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="16" stdDeviation="16" flood-color="#0369a1" flood-opacity="0.18"/>
    </filter>
  </defs>

  <!-- Studio Background -->
  <rect width="500" height="500" rx="20" fill="url(#bgGlowDt)"/>

  <!-- Ground Shadows -->
  <ellipse cx="240" cy="430" rx="160" ry="22" fill="#93c5fd" opacity="0.45"/>
  <ellipse cx="370" cy="430" rx="80" ry="15" fill="#60a5fa" opacity="0.35"/>

  <!-- Stand-up Detergent Pouch -->
  <g filter="url(#dropShadowDt)">
    <!-- Top Heat Seal Notch -->
    <path d="M 140 100 L 320 100 L 315 125 L 145 125 Z" fill="#e0f2fe" stroke="#38bdf8" stroke-width="1.5"/>
    <line x1="160" y1="102" x2="160" y2="123" stroke="#0284c7" stroke-width="1.5"/>
    <line x1="180" y1="102" x2="180" y2="123" stroke="#0284c7" stroke-width="1.5"/>
    <line x1="280" y1="102" x2="280" y2="123" stroke="#0284c7" stroke-width="1.5"/>
    <line x1="300" y1="102" x2="300" y2="123" stroke="#0284c7" stroke-width="1.5"/>

    <!-- Pouch Body (tapered stand-up shape) -->
    <path d="M 145 125 L 315 125 L 340 375 L 325 400 L 135 400 L 120 375 Z" fill="url(#pouchBlue)" stroke="#0284c7" stroke-width="1.5"/>

    <!-- Surface Specular Light Sweep -->
    <path d="M 160 125 L 195 125 L 175 395 L 140 395 Z" fill="#ffffff" opacity="0.18"/>

    <!-- Wave / Splash Swirl -->
    <path d="M 125 240 Q 220 200 335 230 L 338 290 Q 230 260 125 300 Z" fill="url(#swirlGrad)"/>

    <!-- Typography -->
    <text x="230" y="165" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="700" font-size="13" fill="#bae6fd" letter-spacing="2">ACTIVE CLEAN</text>
    <text x="230" y="210" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="28" fill="#ffffff" letter-spacing="1">DETERGENT</text>
    <text x="230" y="235" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="800" font-size="18" fill="#fef08a" letter-spacing="2">POWDER</text>

    <!-- 1kg Badge -->
    <rect x="150" y="325" width="85" height="30" rx="8" fill="#ef4444"/>
    <text x="192" y="345" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="900" font-size="13" fill="#ffffff">1 kg PACK</text>

    <!-- Bullet Features -->
    <text x="245" y="335" font-family="system-ui, sans-serif" font-weight="600" font-size="9" fill="#ffffff">• Tough Stain Removal</text>
    <text x="245" y="352" font-family="system-ui, sans-serif" font-weight="600" font-size="9" fill="#ffffff">• Fresh Ocean Fragrance</text>

    <!-- Sparkles -->
    <!-- Sparkle 1 -->
    <path d="M 300 150 Q 300 165 315 165 Q 300 165 300 180 Q 300 165 285 165 Q 300 165 300 150 Z" fill="#ffffff"/>
    <circle cx="300" cy="165" r="3" fill="#fef08a"/>
    <!-- Sparkle 2 -->
    <path d="M 155 220 Q 155 230 165 230 Q 155 230 155 240 Q 155 230 145 230 Q 155 230 155 220 Z" fill="#ffffff"/>
  </g>

  <!-- Blue Plastic Measuring Scoop with Powder -->
  <g transform="translate(320, 330)">
    <!-- Scoop Handle -->
    <path d="M 50 40 L 120 10 L 125 18 L 55 48 Z" fill="#2563eb" stroke="#1d4ed8" stroke-width="1.5"/>
    <!-- Scoop Cup -->
    <ellipse cx="40" cy="55" rx="45" ry="32" fill="#1d4ed8" stroke="#60a5fa" stroke-width="2"/>
    <!-- Powder Inside Scoop -->
    <ellipse cx="40" cy="50" rx="40" ry="26" fill="#ffffff"/>
    <ellipse cx="40" cy="50" rx="36" ry="22" fill="#f8fafc"/>

    <!-- Oxygen Specks inside scoop -->
    <circle cx="25" cy="46" r="2" fill="#0284c7"/>
    <circle cx="45" cy="42" r="1.5" fill="#ef4444"/>
    <circle cx="55" cy="54" r="2" fill="#0284c7"/>
    <circle cx="35" cy="58" r="1.5" fill="#ef4444"/>
  </g>

  <!-- Spilled Powder Pile on Floor -->
  <ellipse cx="280" cy="425" rx="60" ry="16" fill="#ffffff"/>
  <circle cx="250" cy="422" r="1.5" fill="#0284c7"/>
  <circle cx="270" cy="426" r="1.5" fill="#ef4444"/>
  <circle cx="295" cy="423" r="1.5" fill="#0284c7"/>
  <circle cx="310" cy="428" r="1.5" fill="#ef4444"/>
</svg>"""

# 3. Tea Leaf 250g (SKU-TE-250)
tea_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGlowTe" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="70%" stop-color="#f0fdf4"/>
      <stop offset="100%" stop-color="#dcfce7"/>
    </radialGradient>
    <linearGradient id="teaPouch" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#047857"/>
      <stop offset="40%" stop-color="#065f46"/>
      <stop offset="80%" stop-color="#064e3b"/>
      <stop offset="100%" stop-color="#022c22"/>
    </linearGradient>
    <linearGradient id="goldSheen" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#d97706"/>
      <stop offset="50%" stop-color="#fde047"/>
      <stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
    <filter id="dropShadowTe" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="16" stdDeviation="16" flood-color="#064e3b" flood-opacity="0.22"/>
    </filter>
  </defs>

  <!-- Studio Background -->
  <rect width="500" height="500" rx="20" fill="url(#bgGlowTe)"/>

  <!-- Ground Shadows -->
  <ellipse cx="230" cy="430" rx="150" ry="22" fill="#86efac" opacity="0.35"/>
  <ellipse cx="360" cy="425" rx="85" ry="16" fill="#4ade80" opacity="0.3"/>

  <!-- Emerald Tea Foil Pouch -->
  <g filter="url(#dropShadowTe)">
    <!-- Top Heat Seal (Gold) -->
    <path d="M 140 105 L 320 105 L 315 125 L 145 125 Z" fill="url(#goldSheen)" stroke="#b45309" stroke-width="1.5"/>

    <!-- Pouch Body -->
    <path d="M 145 125 L 315 125 L 335 375 L 320 400 L 140 400 L 125 375 Z" fill="url(#teaPouch)" stroke="#059669" stroke-width="1.5"/>

    <!-- Gold Foil Frame Borders -->
    <rect x="155" y="145" width="150" height="235" rx="8" fill="none" stroke="url(#goldSheen)" stroke-width="2"/>

    <!-- Gold Emblem Circle -->
    <circle cx="230" cy="190" r="26" fill="none" stroke="url(#goldSheen)" stroke-width="2"/>
    <text x="230" y="194" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="800" font-size="9" fill="#fef08a" letter-spacing="1">100% PURE</text>

    <!-- Typography -->
    <text x="230" y="235" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="700" font-size="12" fill="#fef08a" letter-spacing="2">PREMIUM CTC</text>
    <text x="230" y="265" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="24" fill="#ffffff" letter-spacing="2">TEA LEAF</text>

    <!-- Net Weight Ribbon -->
    <rect x="165" y="285" width="130" height="28" rx="6" fill="#b91c1c" stroke="#fef08a" stroke-width="1.5"/>
    <text x="230" y="303" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="800" font-size="12" fill="#ffffff" letter-spacing="1">NET WT: 250g</text>

    <!-- Quality Claims -->
    <text x="230" y="335" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="600" font-size="9.5" fill="#bbf7d0">• Rich Amber Liquor</text>
    <text x="230" y="352" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="600" font-size="9.5" fill="#bbf7d0">• Strong Kadak Chai Blend</text>

    <!-- Vegetarian Mark -->
    <rect x="285" y="155" width="16" height="16" rx="2" fill="#ffffff" stroke="#16a34a" stroke-width="1.5"/>
    <circle cx="293" cy="163" r="4" fill="#16a34a"/>
  </g>

  <!-- Ceramic Tasting Bowl with Granular CTC Black Tea -->
  <g transform="translate(300, 350)">
    <!-- Dish Shadow & Body -->
    <ellipse cx="70" cy="55" rx="65" ry="32" fill="#1c1917" stroke="#44403c" stroke-width="3"/>
    <!-- Loose CTC Tea Grains inside dish -->
    <ellipse cx="70" cy="52" rx="58" ry="25" fill="#29180f"/>

    <!-- Grains -->
    <circle cx="45" cy="48" r="2" fill="#1c1917"/>
    <circle cx="65" cy="44" r="2.5" fill="#451a03"/>
    <circle cx="85" cy="52" r="2" fill="#1c1917"/>
    <circle cx="55" cy="58" r="2" fill="#451a03"/>
    <circle cx="75" cy="60" r="2.5" fill="#1c1917"/>
    <circle cx="95" cy="50" r="2" fill="#451a03"/>
  </g>

  <!-- Fresh Green Tea Leaves in Foreground -->
  <g transform="translate(230, 395) rotate(-15)">
    <!-- Leaf 1 -->
    <path d="M 0 20 Q 30 -5 65 10 Q 75 25 50 35 Q 20 40 0 20 Z" fill="#22c55e" stroke="#15803d" stroke-width="1.5"/>
    <path d="M 0 20 Q 30 15 65 10" fill="none" stroke="#86efac" stroke-width="1.5"/>
  </g>
  <g transform="translate(210, 420) rotate(20)">
    <!-- Leaf 2 -->
    <path d="M 0 15 Q 25 -5 50 8 Q 60 20 40 28 Q 15 30 0 15 Z" fill="#16a34a" stroke="#166534" stroke-width="1.2"/>
    <path d="M 0 15 Q 25 12 50 8" fill="none" stroke="#bbf7d0" stroke-width="1.2"/>
  </g>
</svg>"""

# 4. Neutral Placeholder (Commercial Wholesale Pack)
placeholder_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGlowPl" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="70%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#f1f5f9"/>
    </radialGradient>
  </defs>

  <rect width="500" height="500" rx="20" fill="url(#bgGlowPl)"/>
  <ellipse cx="250" cy="425" rx="140" ry="20" fill="#e2e8f0" opacity="0.8"/>

  <!-- Clean Minimalist FMCG Carton -->
  <rect x="160" y="140" width="180" height="250" rx="16" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>
  <rect x="180" y="170" width="140" height="85" rx="10" fill="#f1f5f9"/>

  <!-- Lines representing product pack details -->
  <rect x="195" y="280" width="110" height="12" rx="4" fill="#cbd5e1"/>
  <rect x="210" y="305" width="80" height="8" rx="4" fill="#e2e8f0"/>

  <!-- Quality Stamp -->
  <circle cx="250" cy="350" r="22" fill="#10b981"/>
  <path d="M 240 350 L 247 357 L 262 342" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

files = {
    "SKU-BS-075.svg": biscuit_svg,
    "glucose-biscuit-75g.svg": biscuit_svg,
    "SKU-DT-1KG.svg": detergent_svg,
    "detergent-powder-1kg.svg": detergent_svg,
    "SKU-TE-250.svg": tea_svg,
    "tea-leaf-250g.svg": tea_svg,
    "placeholder.svg": placeholder_svg,
    "packaged-food.svg": biscuit_svg,
    "home-care.svg": detergent_svg,
}

for filename, content in files.items():
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Generated {len(files)} SVG product assets successfully!")
