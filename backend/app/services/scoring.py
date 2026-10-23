from math import radians, sin, cos, asin, sqrt
from app.config import settings

def distance_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    r = 6371000
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*r*asin(sqrt(min(1, a)))

def score_hazard(hazard, agreement_sources: int = 1) -> dict:
    severity = max(1, min(5, int(hazard.severity or 1)))
    confidence = max(0.0, min(1.0, float(hazard.confidence or 0)))
    # Agreement across independent sources increases confidence, with diminishing returns.
    confidence = min(0.99, confidence + max(0, agreement_sources-1)*0.12)
    final_score = round((severity / 5) * confidence, 4)
    if hazard.admin_status == "dismissed":
        treatment = "ignored"
    elif hazard.admin_rating is not None:
        treatment = "flagged" if hazard.admin_rating <= 2 else "penalised" if hazard.admin_rating <= 4 else "blocked"
        final_score = hazard.admin_rating / 5
    elif hazard.admin_status == "confirmed" and severity >= 4 and confidence >= 0.75:
        treatment = "penalised"
    else:
        treatment = "flagged"
    return {"final_score": final_score, "confidence": confidence, "treatment": treatment}

def scored_hazards(hazards):
    results = []
    for hazard in hazards:
        neighbors = [h for h in hazards if h.type == hazard.type and h.source != hazard.source and
                     distance_m(h.lat, h.lng, hazard.lat, hazard.lng) <= settings.hazard_group_distance_m]
        source_count = len({h.source for h in neighbors} | {hazard.source})
        result = score_hazard(hazard, source_count)
        result["hazard"] = hazard
        results.append(result)
    return results
