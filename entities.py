# entities.py
import random
import math
import time

import db

# 全局配置（与原版Dashboard一致）
MAP_RECT_WIDTH  = 1920
MAP_RECT_HEIGHT = 1080

FORKLIFT_WARN_RADIUS  = 60
FORKLIFT_DANGER_RADIUS = 30
FORKLIFT_MOVE_SPEED = 1.2
PERSON_MOVE_SPEED   = 0.3

FORKLIFT_BORDER_MARGIN = 30
PERSON_BORDER_MARGIN = 15

FORKLIFT_ROADS = [
    {
        "name": "主干道A-上横道",
        "points": [(460, 200), (1500, 200)],
    },
    {
        "name": "主干道B-下横道",
        "points": [(290, 880), (1340, 880)],
    },
    {
        "name": "主干道C-中横道",
        "points": [(130, 710), (860, 710)],
    },
]

class MapZone:
    def __init__(self, zone_id, x, y, width, height, name="", color="#e8f4f8"):
        self.id = zone_id
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        self.color = color

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "name": self.name,
            "color": self.color
        }

class Obstacle:
    def __init__(self, o_id, x, y, width, height):
        self.id = o_id
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }

class Forklift:
    MODE_AUTO = 0
    MODE_MANUAL = 1
    MODE_STOPPED = 2

    def __init__(self, f_id, x, y, path=None):
        self.id = f_id
        self.x = x
        self.y = y
        self.warn_radius = FORKLIFT_WARN_RADIUS
        self.danger_radius = FORKLIFT_DANGER_RADIUS
        self.mode = self.MODE_AUTO
        self.dx = random.choice([-FORKLIFT_MOVE_SPEED, FORKLIFT_MOVE_SPEED])
        self.dy = random.choice([-FORKLIFT_MOVE_SPEED, FORKLIFT_MOVE_SPEED])
        self.path = path
        self.path_index = 0
        self.path_direction = 1
        self.speed = FORKLIFT_MOVE_SPEED

    def move(self, rect_w, rect_h, margin):
        if self.mode == self.MODE_AUTO:
            if self.path and len(self.path["points"]) >= 2:
                self._move_along_path()
            else:
                self._move_random(rect_w, rect_h, margin)

    def _move_random(self, rect_w, rect_h, margin):
        self.x += self.dx
        self.y += self.dy

        if self.x < margin or self.x > rect_w - margin:
            self.dx *= -1
            self.x = max(margin, min(rect_w - margin, self.x))
        if self.y < margin or self.y > rect_h - margin:
            self.dy *= -1
            self.y = max(margin, min(rect_h - margin, self.y))

    def _move_along_path(self):
        points = self.path["points"]
        target_x, target_y = points[self.path_index]

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < self.speed:
            self.x = target_x
            self.y = target_y
            if self.path_direction == 1:
                if self.path_index >= len(points) - 1:
                    self.path_direction = -1
                    self.path_index = len(points) - 2
                else:
                    self.path_index += 1
            else:
                if self.path_index <= 0:
                    self.path_direction = 1
                    self.path_index = 1
                else:
                    self.path_index -= 1
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.mode = self.MODE_MANUAL

    def set_mode(self, mode):
        self.mode = mode

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "warn_radius": self.warn_radius,
            "danger_radius": self.danger_radius,
            "mode": self.mode
        }

class Person:
    def __init__(self, p_id, x, y):
        self.id = p_id
        self.x = x
        self.y = y
        self.dx = random.choice([-PERSON_MOVE_SPEED, PERSON_MOVE_SPEED])
        self.dy = random.choice([-PERSON_MOVE_SPEED, PERSON_MOVE_SPEED])

    def move(self, rect_w, rect_h, margin):
        self.x += self.dx
        self.y += self.dy

        if self.x < margin or self.x > rect_w - margin:
            self.dx *= -1
            self.x = max(margin, min(rect_w - margin, self.x))
        if self.y < margin or self.y > rect_h - margin:
            self.dy *= -1
            self.y = max(margin, min(rect_h - margin, self.y))

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y
        }

class SceneManager:
    def __init__(self, forklift_cnt=2, person_cnt=1, obstacle_cnt=0):
        self.forklifts = []
        self.persons = []
        self.obstacles = []
        self.zones = []
        self.alert_level = 0
        self.danger_type = ""
        self.person_alert = False
        self.active_alarms = {}
        self.last_alert_level = 0

        self.init_default_zones()
        self.init_forklifts(forklift_cnt)
        self.init_persons(person_cnt)
        self.init_obstacles(obstacle_cnt)

    def init_default_zones(self):
        self.zones = []

    def init_forklifts(self, count):
        self.forklifts = []
        for i in range(count):
            road = FORKLIFT_ROADS[i % len(FORKLIFT_ROADS)]
            points = road["points"]
            start_x, start_y = points[0]
            f = Forklift(i, start_x, start_y, path=road)
            f.path_index = 0
            self.forklifts.append(f)

    def init_persons(self, count):
        self.persons = []
        m = PERSON_BORDER_MARGIN
        for i in range(count):
            x = random.randint(m, MAP_RECT_WIDTH - m)
            y = random.randint(m, MAP_RECT_HEIGHT - m)
            self.persons.append(Person(i, x, y))

    def init_obstacles(self, count):
        self.obstacles = []
        for i in range(count):
            x = random.randint(50, MAP_RECT_WIDTH - 150)
            y = random.randint(50, MAP_RECT_HEIGHT - 100)
            width = random.randint(30, 80)
            height = random.randint(30, 80)
            self.obstacles.append(Obstacle(i, x, y, width, height))

    def set_obstacle_count(self, count):
        self.init_obstacles(count)

    def update_obstacle(self, o_id, x, y, width, height):
        for o in self.obstacles:
            if o.id == o_id:
                o.x = x
                o.y = y
                o.width = width
                o.height = height
                break

    def set_counts(self, forklift_cnt, person_cnt):
        self.init_forklifts(forklift_cnt)
        self.init_persons(person_cnt)

    def set_forklift_pos(self, f_id, x, y):
        for f in self.forklifts:
            if f.id == f_id:
                f.set_position(x, y)
                break

    def set_forklift_mode(self, f_id, mode):
        for f in self.forklifts:
            if f.id == f_id:
                f.set_mode(mode)
                break

    def set_person_pos(self, p_id, x, y):
        for p in self.persons:
            if p.id == p_id:
                p.set_position(x, y)
                break

    def add_zone(self, zone_id, x, y, width, height, name="", color="#e8f4f8"):
        zone = MapZone(zone_id, x, y, width, height, name, color)
        self.zones.append(zone)
        return zone

    def update_zone(self, zone_id, x=None, y=None, width=None, height=None, name=None, color=None):
        for zone in self.zones:
            if zone.id == zone_id:
                if x is not None:
                    zone.x = x
                if y is not None:
                    zone.y = y
                if width is not None:
                    zone.width = width
                if height is not None:
                    zone.height = height
                if name is not None:
                    zone.name = name
                if color is not None:
                    zone.color = color
                break

    def remove_zone(self, zone_id):
        self.zones = [z for z in self.zones if z.id != zone_id]

    def clear_zones(self):
        self.zones = []

    def add_obstacle(self, x, y, radius):
        obs_id = len(self.obstacles)
        obs = Obstacle(obs_id, x, y, radius, radius)
        self.obstacles.append(obs)
        return obs

    def remove_obstacle(self, obs_id):
        for i, obs in enumerate(self.obstacles):
            if obs.id == obs_id:
                del self.obstacles[i]
                return True
        return False

    def move_all(self):
        for f in self.forklifts:
            f.move(MAP_RECT_WIDTH, MAP_RECT_HEIGHT, FORKLIFT_BORDER_MARGIN)
        for p in self.persons:
            p.move(MAP_RECT_WIDTH, MAP_RECT_HEIGHT, PERSON_BORDER_MARGIN)

    def check_any_person_alert(self):
        max_level = 0
        alert_details = []
        for p in self.persons:
            for f in self.forklifts:
                dist_sq = (p.x - f.x)**2 + (p.y - f.y)**2
                if dist_sq <= f.danger_radius**2:
                    return 2, f"行人P{p.id}与叉车FL{f.id}危险接近"
                if dist_sq <= f.warn_radius**2:
                    max_level = max(max_level, 1)
                    alert_details.append(f"行人P{p.id}与叉车FL{f.id}")
        if max_level == 1:
            return 1, f"行人警戒: {', '.join(alert_details[:3])}"
        return 0, "状态安全"

    def check_forklift_to_forklift(self):
        n = len(self.forklifts)
        for i in range(n):
            f1 = self.forklifts[i]
            for j in range(i + 1, n):
                f2 = self.forklifts[j]
                dist_sq = (f1.x - f2.x)**2 + (f1.y - f2.y)**2
                if dist_sq <= f1.danger_radius**2:
                    return True, 2, f"叉车FL{f1.id}与FL{f2.id}危险接近"
                if dist_sq <= f1.warn_radius**2:
                    return True, 1, f"叉车FL{f1.id}与FL{f2.id}警戒接近"
        return False, 0, ""

    def _check_forklift_forklift_alerts(self):
        alerts = []
        n = len(self.forklifts)
        for i in range(n):
            f1 = self.forklifts[i]
            for j in range(i + 1, n):
                f2 = self.forklifts[j]
                dist = math.sqrt((f1.x - f2.x)**2 + (f1.y - f2.y)**2)
                if dist <= f1.danger_radius:
                    alerts.append({
                        "level": 2,
                        "forklift_id": f1.id,
                        "forklift2_id": f2.id,
                        "forklift_x": f1.x,
                        "forklift_y": f1.y,
                        "forklift2_x": f2.x,
                        "forklift2_y": f2.y,
                        "distance": dist,
                        "danger_type": f"叉车FL{f1.id}与FL{f2.id}危险接近",
                        "alarm_category": "forklift_forklift"
                    })
                elif dist <= f1.warn_radius:
                    alerts.append({
                        "level": 1,
                        "forklift_id": f1.id,
                        "forklift2_id": f2.id,
                        "forklift_x": f1.x,
                        "forklift_y": f1.y,
                        "forklift2_x": f2.x,
                        "forklift2_y": f2.y,
                        "distance": dist,
                        "danger_type": f"叉车FL{f1.id}与FL{f2.id}警戒接近",
                        "alarm_category": "forklift_forklift"
                    })
        return alerts

    def _check_person_forklift_alerts(self):
        alerts = []
        for p in self.persons:
            for f in self.forklifts:
                dist = math.sqrt((p.x - f.x)**2 + (p.y - f.y)**2)
                if dist <= f.danger_radius:
                    alerts.append({
                        "level": 2,
                        "forklift_id": f.id,
                        "person_id": p.id,
                        "forklift_x": f.x,
                        "forklift_y": f.y,
                        "person_x": p.x,
                        "person_y": p.y,
                        "distance": dist,
                        "danger_type": f"行人P{p.id}与叉车FL{f.id}危险接近"
                    })
                elif dist <= f.warn_radius:
                    alerts.append({
                        "level": 1,
                        "forklift_id": f.id,
                        "person_id": p.id,
                        "forklift_x": f.x,
                        "forklift_y": f.y,
                        "person_x": p.x,
                        "person_y": p.y,
                        "distance": dist,
                        "danger_type": f"行人P{p.id}与叉车FL{f.id}警戒接近"
                    })
        return alerts

    def update_alert_status(self):
        person_forklift_alerts = self._check_person_forklift_alerts()
        forklift_forklift_alerts = self._check_forklift_forklift_alerts()
        all_alerts = person_forklift_alerts + forklift_forklift_alerts

        max_level = 0
        danger_texts = []

        for alert in all_alerts:
            category = alert.get("alarm_category", "person_forklift")

            if category == "forklift_forklift":
                key = ("ff", alert["forklift_id"], alert["forklift2_id"])
            else:
                key = ("pf", alert["forklift_id"], alert["person_id"])

            if alert["level"] == 2:
                max_level = 2
                danger_texts.append(alert["danger_type"])

                if key not in self.active_alarms:
                    if category == "forklift_forklift":
                        alarm_id = db.save_scene_alarm(
                            alert["level"],
                            alert["danger_type"],
                            alert["forklift_id"],
                            alarm_category="forklift_forklift",
                            forklift_x=alert["forklift_x"],
                            forklift_y=alert["forklift_y"],
                            distance=alert["distance"],
                            forklift2_id=alert["forklift2_id"],
                            forklift2_x=alert["forklift2_x"],
                            forklift2_y=alert["forklift2_y"]
                        )
                    else:
                        alarm_id = db.save_scene_alarm(
                            alert["level"],
                            alert["danger_type"],
                            alert["forklift_id"],
                            person_id=alert["person_id"],
                            forklift_x=alert["forklift_x"],
                            forklift_y=alert["forklift_y"],
                            person_x=alert["person_x"],
                            person_y=alert["person_y"],
                            distance=alert["distance"],
                            alarm_category="person_forklift"
                        )
                    self.active_alarms[key] = alarm_id

            elif alert["level"] == 1:
                if max_level < 2:
                    max_level = 1
                danger_texts.append(alert["danger_type"])

                if key not in self.active_alarms:
                    if category == "forklift_forklift":
                        alarm_id = db.save_scene_alarm(
                            alert["level"],
                            alert["danger_type"],
                            alert["forklift_id"],
                            alarm_category="forklift_forklift",
                            forklift_x=alert["forklift_x"],
                            forklift_y=alert["forklift_y"],
                            distance=alert["distance"],
                            forklift2_id=alert["forklift2_id"],
                            forklift2_x=alert["forklift2_x"],
                            forklift2_y=alert["forklift2_y"]
                        )
                    else:
                        alarm_id = db.save_scene_alarm(
                            alert["level"],
                            alert["danger_type"],
                            alert["forklift_id"],
                            person_id=alert["person_id"],
                            forklift_x=alert["forklift_x"],
                            forklift_y=alert["forklift_y"],
                            person_x=alert["person_x"],
                            person_y=alert["person_y"],
                            distance=alert["distance"],
                            alarm_category="person_forklift"
                        )
                    self.active_alarms[key] = alarm_id

        ended_keys = []
        for key in list(self.active_alarms.keys()):
            still_active = False
            for alert in all_alerts:
                category = alert.get("alarm_category", "person_forklift")
                if category == "forklift_forklift":
                    alert_key = ("ff", alert["forklift_id"], alert["forklift2_id"])
                else:
                    alert_key = ("pf", alert["forklift_id"], alert["person_id"])
                if alert_key == key:
                    still_active = True
                    break

            if not still_active:
                alarm_id = self.active_alarms[key]
                db.end_scene_alarm(alarm_id)
                ended_keys.append(key)

        for key in ended_keys:
            del self.active_alarms[key]

        self.alert_level = max_level
        self.danger_type = danger_texts[0] if danger_texts else "状态安全"
        self.person_alert = len(all_alerts) > 0
        self.last_alert_level = max_level

    def get_scene_data(self):
        active_alerts = []
        for key, alarm_id in self.active_alarms.items():
            if key[0] == "ff":
                active_alerts.append({
                    "alarm_category": "forklift_forklift",
                    "forklift_id": key[1],
                    "forklift2_id": key[2],
                })
            else:
                active_alerts.append({
                    "alarm_category": "person_forklift",
                    "forklift_id": key[1],
                    "person_id": key[2],
                })

        return {
            "forklifts": [f.to_dict() for f in self.forklifts],
            "persons": [p.to_dict() for p in self.persons],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "zones": [z.to_dict() for z in self.zones],
            "alert_level": self.alert_level,
            "danger_type": self.danger_type,
            "person_alert": self.person_alert,
            "active_alerts": active_alerts,
            "map_size": {
                "width": MAP_RECT_WIDTH,
                "height": MAP_RECT_HEIGHT
            }
        }