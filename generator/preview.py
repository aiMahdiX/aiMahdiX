"""ASCII brightness preview of the source photo to guide cropping decisions."""
from PIL import Image
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "photo.jpg")

COLS = 48
ROWS = 32

img = Image.open(SRC).convert("L").resize((COLS, ROWS))
px = img.load()

chars = " .:-=+*#%@"

print(f"Source: {SRC}  {Image.open(SRC).size}")
print(f"Brightness map ({COLS}x{ROWS}), bright = @, dark = space\n")
for y in range(ROWS):
    row = ""
    for x in range(COLS):
        v = px[x, y]
        idx = min(len(chars) - 1, v * len(chars) // 256)
        row += chars[idx]
    print(row)