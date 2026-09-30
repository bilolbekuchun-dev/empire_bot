import math
import os
import subprocess
import shutil

# Make frames dir
os.makedirs("/root/Empire/emoji_frames_diamond", exist_ok=True)
os.makedirs("/root/Empire/emoji_frames_dollar", exist_ok=True)

from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE = 512
TOTAL_FRAMES = 60
FPS = 30

print("Rendering Diamond animation frames...")
# 1. DIAMOND ANIMATION (3D Rotating Brilliant Cut Diamond with Sparkles)
for frame in range(TOTAL_FRAMES):
    angle = (frame / TOTAL_FRAMES) * 2 * math.pi
    
    # 512x512 transparent RGBA image
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    
    cx, cy = SIZE // 2, SIZE // 2
    r_outer = 160
    
    # 3D rotation math
    # Vertices of a faceted brilliant-cut diamond
    top_y = cy - 120
    girdle_y = cy + 10
    bottom_y = cy + 150
    
    num_pts = 8
    pts_girdle = []
    pts_table = []
    
    for i in range(num_pts):
        th = angle + (i * 2 * math.pi / num_pts)
        cos_t = math.cos(th)
        sin_t = math.sin(th)
        
        # Elliptical projection for 3D perspective
        gx = cx + r_outer * cos_t
        gy = girdle_y + (r_outer * 0.25) * sin_t
        pts_girdle.append((gx, gy, sin_t))
        
        tx = cx + (r_outer * 0.6) * cos_t
        ty = top_y + (r_outer * 0.15) * sin_t
        pts_table.append((tx, ty, sin_t))
        
    bottom_pt = (cx, bottom_y, 0)
    
    # Draw facets sorted by Z depth
    facets = []
    
    # Table (top face)
    table_poly = [(p[0], p[1]) for p in pts_table]
    avg_z_table = sum(p[2] for p in pts_table) / num_pts
    facets.append(('table', table_poly, avg_z_table, 0))
    
    # Crown facets (between table and girdle)
    for i in range(num_pts):
        next_i = (i + 1) % num_pts
        poly = [
            (pts_table[i][0], pts_table[i][1]),
            (pts_table[next_i][0], pts_table[next_i][1]),
            (pts_girdle[next_i][0], pts_girdle[next_i][1]),
            (pts_girdle[i][0], pts_girdle[i][1])
        ]
        avg_z = (pts_table[i][2] + pts_table[next_i][2] + pts_girdle[next_i][2] + pts_girdle[i][2]) / 4
        facets.append(('crown', poly, avg_z, i))
        
    # Pavilion facets (between girdle and bottom point)
    for i in range(num_pts):
        next_i = (i + 1) % num_pts
        poly = [
            (pts_girdle[i][0], pts_girdle[i][1]),
            (pts_girdle[next_i][0], pts_girdle[next_i][1]),
            bottom_pt[:2]
        ]
        avg_z = (pts_girdle[i][2] + pts_girdle[next_i][2] + 0) / 3
        facets.append(('pavilion', poly, avg_z, i))
        
    # Sort back-to-front
    facets.sort(key=lambda x: x[2])
    
    for f_type, poly, z, idx in facets:
        # Lighting calculation
        # Normal based on index & angle
        light = 0.5 + 0.45 * math.sin(angle * 2 + idx * (math.pi / 4))
        
        if f_type == 'table':
            base_color = (180, 240, 255, 240)
            edge_color = (255, 255, 255, 255)
        elif f_type == 'crown':
            r = int(50 + 190 * light)
            g = int(180 + 75 * light)
            b = int(240 + 15 * light)
            base_color = (r, g, b, 230)
            edge_color = (220, 250, 255, 250)
        else: # pavilion
            r = int(20 + 140 * light)
            g = int(120 + 110 * light)
            b = int(220 + 35 * light)
            base_color = (r, g, b, 220)
            edge_color = (170, 230, 255, 230)
            
        draw.polygon(poly, fill=base_color, outline=edge_color)
        
    # Add sparkle star effect that glints periodically
    sparkle_phase = (frame % 30) / 30.0
    if sparkle_phase < 0.5:
        sparkle_scale = math.sin(sparkle_phase * 2 * math.pi) * 35
        sp_x = cx + 80 * math.cos(angle * 3)
        sp_y = top_y + 20
        # Draw 4-point star
        draw.line([(sp_x - sparkle_scale, sp_y), (sp_x + sparkle_scale, sp_y)], fill=(255, 255, 255, 255), width=3)
        draw.line([(sp_x, sp_y - sparkle_scale), (sp_x, sp_y + sparkle_scale)], fill=(255, 255, 255, 255), width=3)
        draw.ellipse([(sp_x - 5, sp_y - 5), (sp_x + 5, sp_y + 5)], fill=(255, 255, 255, 255))
        
    im.save(f"/root/Empire/emoji_frames_diamond/frame_{frame:03d}.png")

print("Rendering Dollar Gold Coin animation frames...")
# 2. GOLD DOLLAR COIN ANIMATION (3D Spinning Gold Coin with '$' symbol)
for frame in range(TOTAL_FRAMES):
    angle = (frame / TOTAL_FRAMES) * 2 * math.pi
    
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    
    cx, cy = SIZE // 2, SIZE // 2
    r_coin = 180
    thickness = 35
    
    # 3D spin: width oscillates with cos(angle)
    scale_x = math.cos(angle)
    w = max(abs(scale_x) * r_coin, 4)
    h = r_coin
    
    # Edge extrusion when coin is turning
    edge_dir = 1 if scale_x < 0 else -1
    edge_steps = 15
    for s in range(edge_steps, 0, -1):
        offset_x = edge_dir * (thickness * math.sin(angle) * (s / edge_steps))
        shade = int(180 - 60 * abs(scale_x))
        gold_edge = (shade, int(shade * 0.75), 20, 255)
        draw.ellipse(
            [(cx + offset_x - w, cy - h), (cx + offset_x + w, cy + h)],
            fill=gold_edge
        )
        
    # Main coin face
    is_front = math.cos(angle) >= 0
    light = 0.5 + 0.5 * math.sin(angle + math.pi/4)
    
    # Gold face gradient
    gold_r = int(220 + 35 * light)
    gold_g = int(180 + 40 * light)
    gold_b = int(30 + 40 * light)
    face_color = (gold_r, gold_g, gold_b, 255)
    border_color = (255, 235, 120, 255)
    
    draw.ellipse([(cx - w, cy - h), (cx + w, cy + h)], fill=face_color, outline=border_color, width=6)
    
    # Inner decorative ring
    inner_w = max(w - 20 * abs(scale_x), 2)
    inner_h = h - 20
    draw.ellipse([(cx - inner_w, cy - inner_h), (cx + inner_w, cy + inner_h)], outline=(200, 150, 20, 200), width=4)
    
    # Draw '$' symbol on both faces
    if w > 30:
        symbol_scale_w = max(w * 0.5, 5)
        # Vertical spine
        draw.line([(cx, cy - 90), (cx, cy + 90)], fill=(120, 80, 10, 255), width=max(int(10 * abs(scale_x)), 2))
        
        # Upper & Lower curve of S
        s_shade = (140, 95, 15, 255)
        lw = max(int(14 * abs(scale_x)), 2)
        # Top loop
        draw.arc([(cx - symbol_scale_w, cy - 80), (cx + symbol_scale_w, cy)], start=90, end=270, fill=s_shade, width=lw)
        # Bottom loop
        draw.arc([(cx - symbol_scale_w, cy - 10), (cx + symbol_scale_w, cy + 70)], start=270, end=90, fill=s_shade, width=lw)
        # Middle cross
        draw.line([(cx - symbol_scale_w * 0.7, cy - 5), (cx + symbol_scale_w * 0.7, cy - 5)], fill=s_shade, width=lw)

    # Gold glint sparkle
    sparkle_phase = ((frame + 15) % 30) / 30.0
    if sparkle_phase < 0.4:
        sp_scale = math.sin(sparkle_phase * 2.5 * math.pi) * 30
        sp_x = cx + w * 0.7
        sp_y = cy - h * 0.7
        draw.line([(sp_x - sp_scale, sp_y), (sp_x + sp_scale, sp_y)], fill=(255, 255, 255, 255), width=3)
        draw.line([(sp_x, sp_y - sp_scale), (sp_x, sp_y + sp_scale)], fill=(255, 255, 255, 255), width=3)
        draw.ellipse([(sp_x - 4, sp_y - 4), (sp_x + 4, sp_y + 4)], fill=(255, 255, 255, 255))

    im.save(f"/root/Empire/emoji_frames_dollar/frame_{frame:03d}.png")

print("Encoding WEBM VP9 transparent animated emojis via ffmpeg...")

# Encode Diamond WebM (VP9, transparent background, <256KB, 512x512)
cmd_diamond = [
    "ffmpeg", "-y", "-framerate", "30",
    "-i", "/root/Empire/emoji_frames_diamond/frame_%03d.png",
    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
    "-b:v", "200k", "-crf", "30",
    "-metadata:s:v:0", "alpha_mode=1",
    "-an", "/root/Empire/diamond_emoji.webm"
]
subprocess.run(cmd_diamond, check=True)

# Encode Dollar WebM (VP9, transparent background, <256KB, 512x512)
cmd_dollar = [
    "ffmpeg", "-y", "-framerate", "30",
    "-i", "/root/Empire/emoji_frames_dollar/frame_%03d.png",
    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
    "-b:v", "200k", "-crf", "30",
    "-metadata:s:v:0", "alpha_mode=1",
    "-an", "/root/Empire/dollar_emoji.webm"
]
subprocess.run(cmd_dollar, check=True)

# Also generate animated GIF and APNG previews for user review!
subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", "/root/Empire/emoji_frames_diamond/frame_%03d.png", "-gifflags", "+transdiff", "/root/Empire/diamond_emoji.gif"], check=True)
subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", "/root/Empire/emoji_frames_dollar/frame_%03d.png", "-gifflags", "+transdiff", "/root/Empire/dollar_emoji.gif"], check=True)

print("✅ Successfully generated diamond_emoji.webm and dollar_emoji.webm!")
