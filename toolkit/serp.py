"""Reading search results. Pure functions, no API calls, so they are easy to test."""
import math
import urllib.parse

from .config import clean_domain


def is_client(item, client, check_name=True):
    """True when a search result belongs to the client.

    Domains must match exactly or as a subdomain, so 'example.com' never matches
    'notexample.com'. The Maps name is a fallback for results with no website.
    """
    domain = clean_domain(item.get("domain") or item.get("url") or "")
    if client.domain and (domain == client.domain or domain.endswith("." + client.domain)):
        return True
    if client.place_id and item.get("place_id") == client.place_id:
        return True
    title = (item.get("title") or "").lower()
    return bool(check_name and client.maps_name and client.maps_name.lower() in title)


def read_organic(items, client, leaders=3):
    """Pull the client's positions out of one organic results page.

    web          position in the regular results (None if not in the depth checked)
    page         which page of the client's site ranked
    map          position in the Maps pack on the results page
    panel        whether the client's Business Profile panel showed
    map_leaders  who held the top Maps pack spots, for the competitor view
    """
    web = page = map_pos = None
    panel = False
    pack = []
    for item in items:
        kind = item.get("type")
        if kind == "organic" and web is None and is_client(item, client, check_name=False):
            web = item.get("rank_group")
            page = urllib.parse.urlparse(item.get("url") or "").path or "/"
        elif kind == "local_pack":
            pack.append(item.get("title") or "")
            if map_pos is None and is_client(item, client):
                map_pos = len(pack)
        elif kind == "knowledge_graph" and is_client(item, client):
            panel = True
    return {"web": web, "page": page, "map": map_pos, "panel": panel, "map_leaders": pack[:leaders]}


def read_maps(items, client):
    """Client's position in one Maps search, plus who was #1 there."""
    position = None
    leader = None
    for item in items:
        if item.get("type") != "maps_search":
            continue
        if leader is None:
            leader = item.get("title")
        if position is None and is_client(item, client):
            position = item.get("rank_group")
    return {"position": position, "leader": leader}


def change(now, before):
    """Movement since last check. Positive means the client moved up."""
    if now is None and before is None:
        return ""
    if before is None:
        return "new"
    if now is None:
        return "lost"
    diff = before - now
    if diff > 0:
        return f"+{diff}"
    return str(diff) if diff < 0 else "="


def grid_points(lat, lng, size, step_miles):
    """size x size points centered on lat,lng, spaced step_miles apart.

    Row 0 is the north edge, column 0 is the west edge.
    """
    if size < 1:
        raise ValueError("grid size must be at least 1")
    dlat = step_miles / 69.0
    dlng = step_miles / (69.0 * math.cos(math.radians(lat)))
    half = (size - 1) / 2
    return [
        {"row": r, "col": c,
         "lat": round(lat + (half - r) * dlat, 5),
         "lng": round(lng + (c - half) * dlng, 5)}
        for r in range(size) for c in range(size)
    ]
