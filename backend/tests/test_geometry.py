from types import SimpleNamespace
from app.services.geometry import circle_polygon, route_intersects_hazard

def test_circle_polygon_closed_ring():
    polygon = circle_polygon(74.87, 31.63, 300)
    ring = polygon["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) == 25

def test_route_intersection():
    hazard = SimpleNamespace(lat=31.63, lng=74.87, radius_m=300)
    assert route_intersects_hazard([[74.86,31.63],[74.88,31.63]], hazard)
