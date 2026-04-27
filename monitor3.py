import requests
import math
import time

def point_to_segment_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)

def is_on_path(px, py, path, threshold=30):
    for i in range(len(path) - 1):
        d = point_to_segment_dist(px, py, path[i][0], path[i][1], path[i+1][0], path[i+1][1])
        if d < threshold:
            return True
    return False

paths = {
    'FORK-001': [[630,760],[630,150],[150,150],[150,760],[630,760]],
    'FORK-002': [[630,760],[1417,760],[1417,950],[630,950],[630,760]],
    'FORK-003': [[630,760],[1417,760],[1417,150],[630,150],[630,760]],
}

print("Monitoring forklift positions for 2 minutes...")
print("Note: API returns DB positions, frontend movement is in-memory only")
print("=" * 70)

start = time.time()
duration = 120
check_count = 0

while time.time() - start < duration:
    try:
        r = requests.get('http://localhost:5000/api/devices', timeout=5)
        data = r.json()
        devs = data.get('devices', [])
        
        elapsed = int(time.time() - start)
        check_count += 1
        
        if check_count % 10 == 1:
            print(f"\n[{elapsed}s] Check #{check_count}:")
            for d in devs:
                did = d['device_id']
                px, py = d.get('pos_x', 0), d.get('pos_y', 0)
                online = d.get('online_status', 0)
                if did in paths:
                    on_path = is_on_path(px, py, paths[did])
                    status = "ON PATH" if on_path else "OFF PATH"
                    print(f"  {did}: pos=({px:.0f},{py:.0f}) online={online} {status}")
    except Exception as e:
        print(f"  Error: {e}")
    
    time.sleep(5)

print(f"\nDone! Monitored for {duration}s, {check_count} checks")
print("IMPORTANT: API positions are DB-based (starting positions).")
print("Frontend movement happens in browser memory and is not reflected in API.")
print("To verify actual movement, observe the browser directly.")
