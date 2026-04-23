from PIL import Image
import numpy as np

img = Image.open(r'c:\Users\刘睿\yolo-forklift-safety-hub\map.jpg')
arr = np.array(img)
h, w = arr.shape[:2]
sx = w / 1920.0
sy = h / 1080.0

road_map = np.zeros((h, w), dtype=bool)
for y in range(h):
    for x in range(w):
        r, g, b = int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2])
        is_green = g > 100 and g > r * 1.2 and g > b * 1.2
        is_gray = abs(int(r) - int(g)) < 30 and abs(int(g) - int(b)) < 30 and r > 120 and r < 200
        is_brown = r > 120 and g > 80 and b < 80 and r > g
        if is_green or is_gray or is_brown:
            road_map[y, x] = True

def check_seg(x1, y1, x2, y2, step=2):
    total = 0
    on_road = 0
    if x1 == x2:
        for cy in range(min(y1, y2), max(y1, y2) + 1, step):
            ix, iy = int(x1 * sx), int(cy * sy)
            if ix < w and iy < h:
                total += 1
                if road_map[iy, ix]:
                    on_road += 1
    else:
        for cx in range(min(x1, x2), max(x1, x2) + 1, step):
            ix, iy = int(cx * sx), int(y1 * sy)
            if ix < w and iy < h:
                total += 1
                if road_map[iy, ix]:
                    on_road += 1
    return on_road, total

print("COMPREHENSIVE ROAD ANALYSIS")
print("=" * 70)

print("\n--- FORK-001: Left rectangle ---")
path1 = [[630, 760], [630, 150], [150, 150], [150, 760], [630, 760]]
for i in range(len(path1) - 1):
    x1, y1 = path1[i]
    x2, y2 = path1[i + 1]
    on, total = check_seg(x1, y1, x2, y2)
    pct = on / total * 100 if total else 0
    print(f"  ({x1},{y1})->({x2},{y2}): {on}/{total} = {pct:.1f}%")

print("\n--- FORK-002: Bottom rectangle ---")
path2 = [[630, 760], [1417, 760], [1417, 950], [630, 950], [630, 760]]
for i in range(len(path2) - 1):
    x1, y1 = path2[i]
    x2, y2 = path2[i + 1]
    on, total = check_seg(x1, y1, x2, y2)
    pct = on / total * 100 if total else 0
    print(f"  ({x1},{y1})->({x2},{y2}): {on}/{total} = {pct:.1f}%")

print("\n--- FORK-003: Large right rectangle ---")
path3 = [[630, 760], [1417, 760], [1417, 150], [630, 150], [630, 760]]
for i in range(len(path3) - 1):
    x1, y1 = path3[i]
    x2, y2 = path3[i + 1]
    on, total = check_seg(x1, y1, x2, y2)
    pct = on / total * 100 if total else 0
    print(f"  ({x1},{y1})->({x2},{y2}): {on}/{total} = {pct:.1f}%")

print("\n--- Find best horizontal roads ---")
for cy in range(50, 1080, 20):
    on, total = check_seg(100, cy, 1800, cy, step=5)
    pct = on / total * 100 if total else 0
    if pct > 40:
        print(f"  Y={cy}: {pct:.1f}% road from X=100 to X=1800")

print("\n--- Find best vertical roads ---")
for cx in range(50, 1920, 20):
    on, total = check_seg(cx, 50, cx, 1050, step=5)
    pct = on / total * 100 if total else 0
    if pct > 40:
        print(f"  X={cx}: {pct:.1f}% road from Y=50 to Y=1050")

print("\n--- Check FORK-002 bottom road Y=950 ---")
for cy in range(900, 1000, 5):
    on, total = check_seg(630, cy, 1417, cy, step=3)
    pct = on / total * 100 if total else 0
    print(f"  Y={cy}: {pct:.1f}% road from X=630 to X=1417")

print("\n--- Check FORK-002 right road X=1417 ---")
for cx in range(1390, 1460, 5):
    on, total = check_seg(cx, 760, cx, 950, step=3)
    pct = on / total * 100 if total else 0
    print(f"  X={cx}: {pct:.1f}% road from Y=760 to Y=950")

print("\n--- Check FORK-003 top road Y=150 ---")
for cy in range(100, 300, 10):
    on, total = check_seg(630, cy, 1417, cy, step=3)
    pct = on / total * 100 if total else 0
    if pct > 10:
        print(f"  Y={cy}: {pct:.1f}% road from X=630 to X=1417")

print("\n--- Alternative FORK-002: smaller rectangle in bottom area ---")
for y_bottom in range(850, 1000, 10):
    on, total = check_seg(630, y_bottom, 1417, y_bottom, step=3)
    pct = on / total * 100 if total else 0
    if pct > 50:
        print(f"  Y={y_bottom}: {pct:.1f}% road (bottom edge)")

print("\n--- Alternative FORK-003: check right area roads ---")
for cx in [1200, 1300, 1350, 1400, 1417, 1450]:
    for cy_top in [100, 150, 200, 250, 300]:
        on, total = check_seg(cx, 760, cx, cy_top, step=3)
        pct = on / total * 100 if total else 0
        if pct > 50:
            print(f"  X={cx} Y=760->Y={cy_top}: {pct:.1f}% road")
