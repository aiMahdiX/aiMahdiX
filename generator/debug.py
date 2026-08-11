"""Debug the portrait pipeline: save intermediate previews for inspection."""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))
import generate as G

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

# 1. Crop
rgb = G.load_and_crop()
Image.fromarray(rgb).save(os.path.join(OUT, "1_crop.png"))
print("crop:", rgb.shape)

# 2. Segmentation
mask = G.segment_background(rgb)
print("subject mask fraction:", mask.mean().round(4))
Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(OUT, "2_mask.png"))

# 3. Monochrome tonal (dark)
gray_dark = G.monochrome_tonal(rgb, mask)
Image.fromarray(gray_dark.astype(np.uint8)).save(os.path.join(OUT, "3_gray_dark.png"))

# 4. Monochrome tonal (light, inverted)
gray_light = 255.0 - G.monochrome_tonal(rgb, None)
Image.fromarray(gray_light.astype(np.uint8)).save(os.path.join(OUT, "4_gray_light.png"))

# 5. After autocontrast + unsharp + contrast (dark)
g = G.autocontrast_cutoff(gray_dark, cutoff=1)
g = G.unsharp_mask(g, radius=3, percent=140)
g = G.contrast_boost(g, factor=1.3)
img = Image.fromarray(g.astype(np.uint8)).resize((G.C.PORTRAIT_W, G.C.PORTRAIT_H), Image.LANCZOS)
Image.fromarray(np.array(img)).save(os.path.join(OUT, "5_processed_dark.png"))
print("dark processed mean:", np.array(img).mean().round(1))

# 6. After processing (light)
g2 = G.autocontrast_cutoff(gray_light, cutoff=1)
g2 = G.unsharp_mask(g2, radius=3, percent=140)
g2 = G.contrast_boost(g2, factor=1.3)
img2 = Image.fromarray(g2.astype(np.uint8)).resize((G.C.PORTRAIT_W, G.C.PORTRAIT_H), Image.LANCZOS)
Image.fromarray(np.array(img2)).save(os.path.join(OUT, "6_processed_light.png"))
print("light processed mean:", np.array(img2).mean().round(1))

# 7. Dithered previews
dots_dark = G.floyd_steinberg(np.array(img, dtype=np.float32), threshold=128, serpentine=True)
Image.fromarray((dots_dark * 255).astype(np.uint8)).save(os.path.join(OUT, "7_dither_dark.png"))
print("dark dither dots:", int(dots_dark.sum()))

dots_light = G.floyd_steinberg(np.array(img2, dtype=np.float32), threshold=128, serpentine=True)
Image.fromarray((dots_light * 255).astype(np.uint8)).save(os.path.join(OUT, "8_dither_light.png"))
print("light dither dots:", int(dots_light.sum()))

print("\nPreviews saved to", OUT)