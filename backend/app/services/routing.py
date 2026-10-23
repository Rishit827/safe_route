import httpx

from app.config import settings # type: ignore
from app.services.geometry import circle_polygon, route_intersects_hazard # type: ignore


class RoutingError(RuntimeError):
    """Raised when a valid route cannot be calculated."""


def _stub(start, end, label):
    """
    Create a straight-line fallback for development when ORS is not configured.

    This is not a road-following route and must not be presented as a
    verified safe route.
    """
    coords = [
        [start.lng, start.lat],
        [end.lng, end.lat],
    ]

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "distance": 0,
            "duration": 0,
            "summary": {
                "distance": 0,
                "duration": 0,
            },
            "label": label,
            "stub": True,
        },
    }


async def _ors_route(start, end, avoid_polygons=None, alternatives=False):
    """
    Request a road route from OpenRouteService.

    When avoid_polygons is provided, request a route avoiding those areas.
    """
    if not settings.ors_api_key:
        if settings.use_mock_data:
            return [
                _stub(
                    start,
                    end,
                    "Mock route (ORS API key not configured)",
                )
            ]

        raise RoutingError(
            "OpenRouteService API key is not configured. "
            "Check ORS_API_KEY in your backend .env file."
        )

    base_url = settings.ors_base_url.rstrip("/")
    url = f"{base_url}/v2/directions/driving-car/geojson"

    body = {
        "coordinates": [
            [start.lng, start.lat],
            [end.lng, end.lat],
        ],
        "instructions": False,
    }

    if avoid_polygons:
        body["options"] = {
            "avoid_polygons": {
                "type": "MultiPolygon",
                "coordinates": [
                    polygon["coordinates"]
                    for polygon in avoid_polygons
                ],
            }
        }

    if alternatives:
        body["alternative_routes"] = {
            "target_count": 3,
            "weight_factor": 1.6,
            "share_factor": 0.6,
        }

    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": settings.ors_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/geo+json, application/json",
                },
                json=body,
            )

            if response.is_error:
                # Do not include request headers or the API key in errors.
                detail = response.text[:500]
                raise RoutingError(
                    f"OpenRouteService returned HTTP "
                    f"{response.status_code}: {detail}"
                )

            data = response.json()

    except RoutingError:
        raise

    except httpx.TimeoutException as exc:
        raise RoutingError(
            "OpenRouteService request timed out. Please try again."
        ) from exc

    except httpx.RequestError as exc:
        raise RoutingError(
            f"Could not connect to OpenRouteService: {exc}"
        ) from exc

    except ValueError as exc:
        raise RoutingError(
            "OpenRouteService returned an invalid JSON response."
        ) from exc

    features = data.get("features", [])

    if not features:
        raise RoutingError(
            "OpenRouteService returned no route for these coordinates."
        )

    return features


def _route_cost(feature, hazards):
    """
    Estimate route cost using travel duration and penalties for
    intersections with hazards classified as penalised.
    """
    properties = feature.get("properties", {})
    summary = properties.get("summary", {})

    duration = float(
        summary.get(
            "duration",
            properties.get("duration", 0),
        )
        or 0
    )

    coordinates = (
        feature.get("geometry", {}).get("coordinates", [])
    )

    penalty = 0.0

    for scored in hazards:
        if scored.get("treatment") != "penalised":
            continue

        hazard = scored["hazard"]

        if route_intersects_hazard(coordinates, hazard):
            penalty += (
                float(hazard.radius_m) / 100
                + float(scored.get("final_score", 0)) * 1000
            )

    return duration + penalty * settings.route_penalty_weight


def _intersects_blocked_hazard(feature, blocked):
    """
    Return True if the route intersects any hazard classified as blocked.
    """
    coordinates = (
        feature.get("geometry", {}).get("coordinates", [])
    )

    for scored in blocked:
        hazard = scored["hazard"]

        if route_intersects_hazard(coordinates, hazard):
            return True

    return False


async def calculate_routes(start, end, hazards):
    """
    Calculate a normal route and a safer alternative.

    Blocked hazards are submitted to ORS as avoidance polygons. Returned
    candidates are checked against blocked hazards before selection.

    If no verified safe alternative is available, raise RoutingError
    rather than silently labelling the normal route as safe.
    """

    # 1. Calculate the normal road route.
    normal_features = await _ors_route(start, end)

    normal_route = normal_features[0]

    # Do not claim a mock straight line is a real safe road route.
    if normal_route.get("properties", {}).get("stub"):
        return {
            "normal_route": normal_route,
            "safe_route": normal_route,
            "hazards_on_normal_route": [],
            "route_changed": False,
            "warnings": [
                "Mock routing is active. Configure OpenRouteService "
                "to calculate actual road routes and assess hazard avoidance."
            ],
        }

    # 2. Collect hazards that must be avoided.
    blocked = [
        scored
        for scored in hazards
        if scored.get("treatment") == "blocked"
    ]

    avoid_polygons = [
        circle_polygon(
            scored["hazard"].lng,
            scored["hazard"].lat,
            scored["hazard"].radius_m,
        )
        for scored in blocked
    ]

    # 3. Request safe-route candidates.
    if avoid_polygons:
        try:
            candidates = await _ors_route(
                start,
                end,
                avoid_polygons=avoid_polygons,
                alternatives=True,
            )
        except RoutingError as exc:
            raise RoutingError(
                "Could not calculate a route avoiding blocked hazards. "
                "The normal route is not being presented as safe. "
                f"Routing provider detail: {exc}"
            ) from exc
    else:
        # Without blocked hazards, the normal route can be considered
        # alongside any alternatives returned by ORS.
        try:
            candidates = await _ors_route(
                start,
                end,
                alternatives=True,
            )
        except RoutingError:
            candidates = normal_features

    if not candidates:
        raise RoutingError(
            "No safe-route candidates were returned by the routing provider."
        )

    # 4. Reject every candidate that intersects a blocked hazard.
    safe_candidates = [
        feature
        for feature in candidates
        if not _intersects_blocked_hazard(feature, blocked)
    ]

    # The normal route may also be considered if there are no blocked
    # hazards, but never as a fallback through a blocked hazard.
    if not safe_candidates:
        raise RoutingError(
            "No returned route could be verified to avoid all blocked "
            "hazards. Choose another destination or review the blocked areas."
        )

    # 5. Choose the lowest-cost route among the remaining candidates.
    safe_route = min(
        safe_candidates,
        key=lambda feature: _route_cost(feature, hazards),
    )

    # 6. Identify hazards intersecting the normal route.
    normal_coordinates = (
        normal_route.get("geometry", {}).get("coordinates", [])
    )

    hazards_on_normal_route = []

    for scored in hazards:
        if scored.get("treatment") == "ignored":
            continue

        hazard = scored["hazard"]

        if route_intersects_hazard(normal_coordinates, hazard):
            hazards_on_normal_route.append(
                {
                    "id": hazard.id,
                    "title": hazard.title,
                    "type": hazard.type,
                    "treatment": scored["treatment"],
                    "severity": hazard.severity,
                }
            )

    # 7. Compare route geometries.
    route_changed = (
        normal_route.get("geometry")
        != safe_route.get("geometry")
    )

    warnings = []

    if blocked and not route_changed:
        warnings.append(
            "The selected route geometry matches the normal route. "
            "Verify the blocked hazard locations and routing provider response."
        )

    if not blocked and not route_changed:
        warnings.append(
            "No blocked hazards required avoidance, and the selected route "
            "matches the normal route."
        )

    return {
        "normal_route": normal_route,
        "safe_route": safe_route,
        "hazards_on_normal_route": hazards_on_normal_route,
        "route_changed": route_changed,
        "warnings": warnings,
    }
