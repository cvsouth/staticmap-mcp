import os
import tempfile
from unittest.mock import patch

import pytest
from PIL import Image

from staticmap_mcp.server import render_route_map


def _mock_render(self, zoom=None):
    """Return a blank image instead of downloading tiles."""
    self.zoom = zoom or 10
    n = 2**self.zoom
    # Set center tile coordinates (needed for _geo_to_pixel)
    extent = self.determine_extent(self.zoom)
    if extent:
        min_lon, min_lat, max_lon, max_lat = extent
        cx = (min_lon + max_lon) / 2
        cy = (min_lat + max_lat) / 2
        import math

        self.x_center = (cx + 180.0) / 360.0 * n
        lat_rad = math.radians(cy)
        self.y_center = (
            (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        )
    else:
        self.x_center = n / 2
        self.y_center = n / 2
    return Image.new("RGB", (self.width, self.height), "white")


SAMPLE_COORDS = [[-17.1, 28.1], [-17.2, 28.2], [-17.3, 28.15]]
SAMPLE_MARKERS = [
    {"lon": -17.1, "lat": 28.1, "label": "Start"},
    {"lon": -17.3, "lat": 28.15, "label": "End"},
]


@pytest.mark.asyncio
async def test_basic_route():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "route.png")
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(coordinates=SAMPLE_COORDS, output_path=out)
        assert result == os.path.realpath(out)
        assert os.path.exists(result)
        img = Image.open(result)
        assert img.size == (800, 600)


@pytest.mark.asyncio
async def test_route_with_markers():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "route.png")
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(
                coordinates=SAMPLE_COORDS, output_path=out, markers=SAMPLE_MARKERS
            )
        assert os.path.exists(result)
        img = Image.open(result)
        assert img.size == (800, 600)


@pytest.mark.asyncio
async def test_custom_dimensions():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "route.png")
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(
                coordinates=SAMPLE_COORDS, output_path=out, width=1200, height=900
            )
        img = Image.open(result)
        assert img.size == (1200, 900)


@pytest.mark.asyncio
async def test_empty_coordinates():
    result = await render_route_map(coordinates=[], output_path="/tmp/nope.png")
    assert "Error" in result


@pytest.mark.asyncio
async def test_single_point():
    result = await render_route_map(coordinates=[[-17.1, 28.1]], output_path="/tmp/nope.png")
    assert "Error" in result


@pytest.mark.asyncio
async def test_creates_parent_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "sub", "dir", "route.png")
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(coordinates=SAMPLE_COORDS, output_path=out)
        assert os.path.exists(result)


@pytest.mark.asyncio
async def test_basemap_topo():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "route.png")
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(
                coordinates=SAMPLE_COORDS, output_path=out, basemap="topo"
            )
        assert os.path.exists(result)


@pytest.mark.asyncio
async def test_markers_without_labels():
    """Markers with no label should still render (circle only, no text)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "route.png")
        markers = [{"lon": -17.1, "lat": 28.1}]
        with patch("staticmap_mcp.server.StaticMap.render", _mock_render):
            result = await render_route_map(
                coordinates=SAMPLE_COORDS, output_path=out, markers=markers
            )
        assert os.path.exists(result)
