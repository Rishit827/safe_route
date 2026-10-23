from math import cos, radians
from shapely.geometry import Point, LineString, mapping

def circle_polygon(lng: float, lat: float, radius_m: float, points: int = 24) -> dict:
    """Return GeoJSON polygon coordinates; local degree approximation is adequate for small radii."""
    lat_delta = radius_m / 111320
    lon_delta = radius_m / max(1, 111320 * cos(radians(lat)))
    coords = []
    for i in range(points):
        import math
        angle = 2 * math.pi * i / points
        coords.append([lng + lon_delta * math.cos(angle), lat + lat_delta * math.sin(angle)])
    coords.append(coords[0])
    return {"type": "Polygon", "coordinates": [coords]}

def route_intersects_hazard(route_coords: list, hazard, padding_m: float = 0) -> bool:
    if len(route_coords) < 2:
        return False
    line = LineString([(float(c[0]), float(c[1])) for c in route_coords])
    # Buffer in a local metric approximation, centered at the hazard latitude.
    from shapely.affinity import scale
    point = Point(hazard.lng, hazard.lat)
    scale_x = max(0.01, cos(radians(hazard.lat)))
    metric_line = scale(line, xfact=scale_x, yfact=1, origin=(hazard.lng, hazard.lat))
    metric_point = scale(point, xfact=scale_x, yfact=1, origin=(hazard.lng, hazard.lat))
    radius_deg = (hazard.radius_m + padding_m) / 111320
    return metric_line.distance(metric_point) <= radius_deg
