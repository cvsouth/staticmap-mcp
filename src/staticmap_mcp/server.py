import math
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from PIL import ImageDraw, ImageFont
from staticmap import CircleMarker, Line, StaticMap

mcp = FastMCP("staticmap")

BASEMAPS = {
    "osm": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "topo": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
    "cycle": "https://a.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
    "humanitarian": "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
}


@mcp.tool()
async def render_route_map(
    coordinates: list[list[float]],
    output_path: str,
    markers: list[dict] | None = None,
    width: int = 800,
    height: int = 600,
    line_color: str = "black",
    line_width: int = 3,
    basemap: Literal["osm", "topo", "cycle", "humanitarian"] = "osm",
) -> str:
    """Render a route on an OpenStreetMap tile map and save as PNG.

    Args:
        coordinates: Route as list of [longitude, latitude] pairs, e.g. [[-17.1, 28.1], [-17.2, 28.2]]
        output_path: File path to save the PNG image (parent directories created automatically)
        markers: Optional list of named points, each with "lon", "lat", and "label" keys
        width: Image width in pixels (default 800)
        height: Image height in pixels (default 600)
        line_color: Route line colour (default "black")
        line_width: Route line width in pixels (default 3)
        basemap: Map tile style — "osm" (default), "topo" (terrain/hiking), "cycle" (cycling), "humanitarian"
    """
    if not coordinates or len(coordinates) < 2:
        return "Error: coordinates must contain at least 2 [lon, lat] pairs."

    tile_url = BASEMAPS.get(basemap, BASEMAPS["osm"])
    m = StaticMap(width, height, padding_x=20, padding_y=20, url_template=tile_url)

    # Draw route line
    line_coords = [(c[0], c[1]) for c in coordinates]
    m.add_line(Line(line_coords, line_color, line_width))

    # Add markers
    if markers:
        for marker in markers:
            lon = marker.get("lon")
            lat = marker.get("lat")
            if lon is not None and lat is not None:
                m.add_marker(CircleMarker((lon, lat), "red", 8))

    # Render map
    image = m.render()

    # Draw text labels on markers
    if markers:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()

        for marker in markers:
            lon = marker.get("lon")
            lat = marker.get("lat")
            label = marker.get("label", "")
            if lon is None or lat is None or not label:
                continue

            # Convert geo coordinates to pixel coordinates
            px, py = _geo_to_pixel(m, lon, lat)

            # Draw label with background for readability
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            label_x = px + 10
            label_y = py - th // 2

            # Keep label on screen
            label_x = min(label_x, width - tw - 4)
            label_y = max(4, min(label_y, height - th - 4))

            draw.rectangle(
                [label_x - 2, label_y - 2, label_x + tw + 2, label_y + th + 2],
                fill="white",
                outline="gray",
            )
            draw.text((label_x, label_y), label, fill="black", font=font)

    # Save
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(out), "PNG")

    return str(out)


def _geo_to_pixel(m: StaticMap, lon: float, lat: float) -> tuple[int, int]:
    """Convert geographic coordinates to pixel position on the rendered image.

    After render(), staticmap sets m.x_center and m.y_center (tile-space
    coordinates for the center of the image) and m.zoom.
    """
    zoom = m.zoom
    n = 2**zoom
    tile_size = m.tile_size

    # Convert lon/lat to tile-space coordinates (same formula staticmap uses)
    x_tile = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y_tile = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n

    # m.x_center / m.y_center are the tile-space coords of the image center
    px = int((x_tile - m.x_center) * tile_size + m.width / 2)
    py = int((y_tile - m.y_center) * tile_size + m.height / 2)
    return (px, py)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
