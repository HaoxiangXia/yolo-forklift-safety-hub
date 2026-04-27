import math

def simulate_forklift(path, speed, steps=5000):
    pos_x = float(path[0][0])
    pos_y = float(path[0][1])
    current_point = 0
    visited_vertices = set()
    visited_vertices.add((path[0][0], path[0][1]))
    
    positions = []
    
    for step in range(steps):
        next_idx = (current_point + 1) % len(path)
        next_point = path[next_idx]
        
        dx = next_point[0] - pos_x
        dy = next_point[1] - pos_y
        dist_to_next = math.sqrt(dx * dx + dy * dy)
        
        if dist_to_next < 0.5:
            pos_x = float(next_point[0])
            pos_y = float(next_point[1])
            current_point = next_idx
            visited_vertices.add((next_point[0], next_point[1]))
        else:
            step_size = min(speed, dist_to_next)
            pos_x += (dx / dist_to_next) * step_size
            pos_y += (dy / dist_to_next) * step_size
        
        positions.append((pos_x, pos_y))
    
    return positions, visited_vertices

def check_rect_path(positions, path, tolerance=5):
    errors = []
    for i, (px, py) in enumerate(positions):
        on_path = False
        for j in range(len(path) - 1):
            x1, y1 = path[j]
            x2, y2 = path[j + 1]
            dx, dy = x2 - x1, y2 - y1
            seg_len = math.sqrt(dx * dx + dy * dy)
            if seg_len == 0:
                continue
            t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)
            if dist < tolerance:
                on_path = True
                break
        if not on_path:
            errors.append((i, px, py))
    return errors

print("FORKLIFT MOVEMENT SIMULATION")
print("=" * 70)

path1 = [[630, 760], [630, 150], [150, 150], [150, 760], [630, 760]]
path2 = [[630, 760], [1417, 760], [1417, 950], [630, 950], [630, 760]]
path3 = [[630, 760], [1417, 760], [1417, 150], [630, 150], [630, 760]]

for name, path, speed in [("FORK-001", path1, 1.5), ("FORK-002", path2, 1.8), ("FORK-003", path3, 2.0)]:
    print(f"\n--- {name} ---")
    print(f"Path: {path}")
    print(f"Speed: {speed}")
    
    positions, visited = simulate_forklift(path, speed, steps=10000)
    
    print(f"Visited vertices: {sorted(visited)}")
    expected_vertices = set(tuple(p) for p in path)
    missing = expected_vertices - visited
    if missing:
        print(f"MISSING VERTICES: {missing}")
    else:
        print(f"All vertices visited! OK")
    
    errors = check_rect_path(positions, path, tolerance=3)
    if errors:
        print(f"OFF-PATH positions: {len(errors)} out of {len(positions)}")
        for step, px, py in errors[:5]:
            print(f"  Step {step}: ({px:.1f}, {py:.1f})")
    else:
        print(f"All positions on path! OK")
    
    if len(positions) > 10:
        print(f"Sample positions:")
        for i in [0, 100, 500, 1000, 2000, 5000, 9999]:
            if i < len(positions):
                px, py = positions[i]
                print(f"  Step {i}: ({px:.1f}, {py:.1f})")

print("\n" + "=" * 70)
print("DIAGNOSIS: If all vertices are visited and all positions are on path,")
print("the movement logic is correct. The issue must be elsewhere.")
