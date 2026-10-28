"""Client config files: one JSON file per business in clients/."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


def clean_domain(value):
    """'https://www.Example.com/about' -> 'example.com'"""
    value = (value or "").strip().lower()
    value = re.sub(r"^[a-z]+://", "", value)
    value = value.split("/", 1)[0].split("?", 1)[0]
    return value.removeprefix("www.")


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@dataclass
class Client:
    name: str
    domain: str
    maps_name: str
    lat: float
    lng: float
    location_label: str = ""
    place_id: str = ""
    slug: str = ""
    keywords: list = field(default_factory=list)
    heat_map_keywords: list = field(default_factory=list)
    heat_map_size: int = 5
    heat_map_step_miles: float = 2.0


def load_client(path):
    raw = json.loads(Path(path).read_text())
    center = raw["center"]
    heat = raw.get("heat_map", {})
    client = Client(
        name=raw["name"],
        domain=clean_domain(raw["domain"]),
        maps_name=raw.get("maps_name") or raw["name"],
        lat=float(center["lat"]),
        lng=float(center["lng"]),
        location_label=center.get("label", ""),
        place_id=raw.get("place_id", ""),
        slug=raw.get("slug") or slugify(raw["name"]),
        keywords=[k.strip() for k in raw.get("keywords", []) if k.strip()],
        heat_map_keywords=[k.strip() for k in heat.get("keywords", []) if k.strip()],
        heat_map_size=int(heat.get("size", 5)),
        heat_map_step_miles=float(heat.get("step_miles", 2.0)),
    )
    if not -90 <= client.lat <= 90 or not -180 <= client.lng <= 180:
        raise SystemExit(f"{path}: center lat/lng look wrong ({client.lat}, {client.lng}).")
    return client


def data_dir(client):
    folder = Path(__file__).resolve().parent.parent / "data" / client.slug
    folder.mkdir(parents=True, exist_ok=True)
    return folder
