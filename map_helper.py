# Map Helper Module
# This module provides functionality for creating interactive maps with drawing capabilities
# and handling GeoJSON data in Streamlit applications.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import shape, Point
from pyproj import Transformer, CRS
from shapely.ops import transform
import shapely

# Type aliases for better code readability
GeoJSON = Dict[str, Any]  # GeoJSON object structure
Feature = Dict[str, Any]  # Individual GeoJSON feature
FeatureCollection = Dict[str, Any]  # Collection of GeoJSON features


# --- coverage overlay (feature 2) --------------------------------------------

# Colour each tile by its coverage outcome so the "$0 for ocean" effect is visible.
STATUS_COLORS = {
    "covered": "#2ca02c",      # green — billed
    "no_coverage": "#9e9e9e",  # grey  — 404, genuinely $0 (ocean / outside dates)
    "errored": "#d62728",      # red   — failed, counted as 0 (may hide cost)
}


def coverage_tile_tooltip(tile: Dict[str, Any]) -> str:
    """Hover text for one tile in the coverage overlay."""
    status = tile.get("status", "covered")
    if status == "covered":
        cost = (tile.get("coverage") or {}).get("costOfTransaction", 0)
        return f"covered · {cost:,} credits"
    if status == "no_coverage":
        return "no coverage · 0 credits"
    if status == "errored":
        return "errored · counted as 0"
    return status


def coverage_bounds(tiles: List[Dict[str, Any]]) -> Optional[Tuple[float, float, float, float]]:
    """Bounding box over all tile geometries as (min_lat, min_lon, max_lat, max_lon).

    Returns None for an empty list. The lat/lon order matches folium's ``fit_bounds``.
    """
    geoms = [shape(t["geometry"]) for t in tiles if t.get("geometry")]
    if not geoms:
        return None
    minx = min(g.bounds[0] for g in geoms)
    miny = min(g.bounds[1] for g in geoms)
    maxx = max(g.bounds[2] for g in geoms)
    maxy = max(g.bounds[3] for g in geoms)
    return (miny, minx, maxy, maxx)


def tile_at_point(tiles: List[Dict[str, Any]], lat: float, lon: float) -> Optional[int]:
    """Flattened index of the first tile whose polygon contains a clicked point.

    Bridges an st_folium map click (which reports ``lat``/``lng``) back to a tile so its
    detail panel can be shown. Returns ``None`` when the click hit no tile (e.g. an ocean
    gap), so the caller can leave the current selection unchanged. Boundary clicks count
    as hits (``intersects``); for overlapping tiles the first in list order wins, keeping
    the result deterministic. Tiles with missing/invalid geometry are skipped, not fatal.
    """
    point = Point(lon, lat)  # shapely is (x=lon, y=lat)
    for idx, tile in enumerate(tiles):
        geom = tile.get("geometry")
        if not geom:
            continue
        try:
            polygon = shape(geom)
        except (TypeError, ValueError, KeyError):
            continue
        if polygon.intersects(point):
            return idx
    return None


class BoxDrawer:
    """
    A comprehensive helper class for creating interactive maps with drawing capabilities.
    
    This class provides functionality to:
    - Build Folium maps with customizable drawing tools
    - Render maps in Streamlit applications
    - Extract user drawings as GeoJSON FeatureCollection objects
    - Display existing GeoJSON data on maps
    - Calculate bounding boxes from drawn features
    
    The class is designed to work seamlessly with Streamlit's st_folium component
    and provides both interactive drawing and static display capabilities.
    """

    def __init__(
        self,
        center: Tuple[float, float] = (0.0, 0.0),
        zoom: int = 2,
        height: int = 500,
        width: Optional[int] = None,
        control_scale: bool = True,
        prefer_canvas: bool = True,
    ) -> None:
        """
        Initialize the BoxDrawer with map configuration parameters.
        
        Args:
            center (Tuple[float, float]): Center coordinates (latitude, longitude) for the map
            zoom (int): Initial zoom level for the map (1-18, higher = more zoomed in)
            height (int): Height of the map in pixels
            width (Optional[int]): Width of the map in pixels (None for auto-width)
            control_scale (bool): Whether to show scale control on the map
            prefer_canvas (bool): Whether to use canvas rendering for better performance
        """
        self.center = center  # Map center coordinates (lat, lon)
        self.zoom = zoom  # Initial zoom level
        self.height = height  # Map height in pixels
        self.width = width  # Map width in pixels (None for auto)
        self.control_scale = control_scale  # Show scale control
        self.prefer_canvas = prefer_canvas  # Use canvas rendering

        # Internal state variables
        self._map: Optional[folium.Map] = None  # Folium map instance
        self._render_result: Optional[Dict[str, Any]] = None  # Results from st_folium

    # --- public API ---------------------------------------------------------

    def render(self) -> None:
        """
        Create an interactive map with drawing controls and render it in Streamlit.
        
        This method creates a Folium map with drawing tools enabled, specifically
        configured for polygon drawing. The map is then rendered using st_folium
        and the results are stored for later extraction of drawn features.
        """
        # Create the base Folium map with specified configuration
        m = folium.Map(
            location=list(self.center),  # Convert tuple to list for Folium
            zoom_start=self.zoom,
            control_scale=self.control_scale,
            prefer_canvas=self.prefer_canvas,
        )

        # Add drawing controls to the map
        # Configured for polygon drawing only (no rectangles, circles, etc.)
        Draw(
            export=False,  # Disable export functionality
            position="topleft",  # Position of drawing controls
            draw_options={
                "polyline": False,  # Disable polyline drawing
                "polygon": True,    # Enable polygon drawing
                "circle": False,    # Disable circle drawing
                "circlemarker": False,  # Disable circle marker drawing
                "marker": False,    # Disable marker placement
                "rectangle": True,  # Enable rectangle / bounding-box drawing
            },
            edit_options={"edit": False, "remove": True},  # Allow removal but not editing
        ).add_to(m)

        # Store map instance and render in Streamlit
        self._map = m
        # st_folium returns a dictionary containing drawing results
        self._render_result = st_folium(m, height=self.height, width=self.width)

    def show_geojson(self, geojson: GeoJSON) -> None:
        """
        Display existing GeoJSON data on a map without drawing capabilities.
        
        This method creates a read-only map that displays the provided GeoJSON data.
        It's useful for visualizing uploaded or pre-existing geographic data.
        
        Args:
            geojson (GeoJSON): The GeoJSON data to display on the map
        """
        # Create a new Folium map with the same configuration
        m = folium.Map(
            location=list(self.center),
            zoom_start=self.zoom,
            control_scale=self.control_scale,
            prefer_canvas=self.prefer_canvas,
        )

        # Add the GeoJSON data as a layer
        folium.GeoJson(
            geojson,
            name="geojson_layer"  # Name for the layer control
        ).add_to(m)

        # Add layer control for toggling layers
        folium.LayerControl().add_to(m)

        # Render the map in Streamlit without capturing interactions
        st_folium(m, height=self.height, width=self.width, returned_objects=[])

    def show_coverage(
        self,
        tiles: List[Dict[str, Any]],
        key: str = "coverage_map",
        selected_index: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Render a map colouring each tile by coverage status; capture tile clicks.

        Args:
            tiles: plan tile records, each with ``geometry``, ``status`` and (for
                covered tiles) ``coverage.costOfTransaction``.
            key: st_folium widget key (must be unique on the page).
            selected_index: flattened index of the currently-inspected tile, drawn with a
                bold outline so the click-to-inspect selection is visible on the map.

        Returns:
            The ``st_folium`` result dict (``last_object_clicked`` / ``last_clicked`` carry
            the clicked point), or ``None`` when there are no tiles to draw.
        """
        if not tiles:
            return None

        bounds = coverage_bounds(tiles)
        center = self.center
        if bounds:
            center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)

        m = folium.Map(
            location=list(center),
            zoom_start=self.zoom,
            control_scale=self.control_scale,
            prefer_canvas=self.prefer_canvas,
        )
        for idx, tile in enumerate(tiles):
            color = STATUS_COLORS.get(tile.get("status", "covered"), STATUS_COLORS["no_coverage"])
            is_selected = idx == selected_index
            style = (
                {"color": "#111111", "weight": 4, "fillColor": color, "fillOpacity": 0.65}
                if is_selected
                else {"color": color, "weight": 1, "fillColor": color, "fillOpacity": 0.45}
            )
            folium.GeoJson(
                tile["geometry"],
                style_function=(lambda _f, s=style: s),
                tooltip=folium.Tooltip(f"Tile #{idx + 1} · {coverage_tile_tooltip(tile)}"),
            ).add_to(m)
        if bounds:
            m.fit_bounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])

        return st_folium(
            m,
            height=self.height,
            width=self.width,
            returned_objects=["last_object_clicked", "last_clicked"],
            key=key,
        )

    def feature_collection(self) -> FeatureCollection:
        """
        Get all drawings made on the map as a GeoJSON FeatureCollection.
        
        Returns:
            FeatureCollection: A GeoJSON FeatureCollection containing all drawn features
        """
        drawings = self._get_all_drawings()
        return self._as_feature_collection(drawings)

    def last_feature_collection(self) -> Optional[FeatureCollection]:
        """
        Get the most recently drawn feature as a GeoJSON FeatureCollection.
        
        This method returns only the last active drawing, which is useful when
        you only need the most recent user interaction with the map.
        
        Returns:
            Optional[FeatureCollection]: The last drawn feature as a FeatureCollection,
                                       or None if no drawings exist
        """
        if not isinstance(self._render_result, dict):
            return None

        # Get the last active drawing from the render result
        last = self._render_result.get("last_active_drawing")
        if not last:
            return None

        # Ensure the drawing is properly formatted as a Feature
        if isinstance(last, dict) and last.get("type") == "Feature":
            feat: Feature = last
        else:
            # Fallback: wrap geometry-like dicts as a Feature
            feat = {"type": "Feature", "properties": {}, "geometry": last}

        # Return as a FeatureCollection with a single feature
        return {"type": "FeatureCollection", "features": [feat]}

    def bbox(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Calculate the bounding box of the last drawn polygon.
        
        This convenience method extracts the bounding box coordinates from the
        most recently drawn polygon feature. The bounding box is returned as
        (min_lon, min_lat, max_lon, max_lat).
        
        Returns:
            Optional[Tuple[float, float, float, float]]: Bounding box coordinates
                                                       or None if no valid polygon exists
        """
        # Get the last drawn feature
        fc = self.last_feature_collection()
        if not fc or not fc["features"]:
            return None

        # Extract geometry from the first (and only) feature
        geom = fc["features"][0].get("geometry") or {}
        if geom.get("type") != "Polygon":
            return None

        # Get coordinates from the polygon
        # Leaflet rectangle emits a simple ring: [[lon, lat], ...]
        coords = geom.get("coordinates") or []
        if not coords or not coords[0]:
            return None

        # Extract longitude and latitude arrays from the exterior ring
        ring = coords[0]  # exterior ring
        lons = [c[0] for c in ring]  # Longitude values
        lats = [c[1] for c in ring]  # Latitude values
        
        # Return bounding box as (min_lon, min_lat, max_lon, max_lat)
        return (min(lons), min(lats), max(lons), max(lats))

    # --- internal helpers ---------------------------------------------------

    def _get_all_drawings(self) -> List[Feature]:
        """
        Extract all drawn features from the render result.
        
        This internal method normalizes the different response formats from
        st_folium across different versions and ensures all items are properly
        formatted as GeoJSON Features.
        
        Returns:
            List[Feature]: List of all drawn features as GeoJSON Features
        """
        if not isinstance(self._render_result, dict):
            return []

        # Handle different st_folium response formats
        drawings: List[Feature] = (
            self._render_result.get("all_drawings")  # Newer format
            or self._render_result.get("drawn_features")  # Older format
            or []
        )

        # Normalize all items to proper GeoJSON Features
        features: List[Feature] = []
        for item in drawings:
            if isinstance(item, dict) and item.get("type") == "Feature":
                # Already a proper Feature
                features.append(item)
            elif isinstance(item, dict):
                # Wrap geometry as a Feature
                features.append(
                    {"type": "Feature", "properties": {}, "geometry": item}
                )
        return features

    @staticmethod
    def _as_feature_collection(features: List[Feature]) -> FeatureCollection:
        """
        Convert a list of Features into a GeoJSON FeatureCollection.
        
        Args:
            features (List[Feature]): List of GeoJSON Features
            
        Returns:
            FeatureCollection: A properly formatted GeoJSON FeatureCollection
        """
        return {"type": "FeatureCollection", "features": features}

    # --- utilities ----------------------------------------------------------

    @staticmethod
    def to_bytes(fc: FeatureCollection, indent: int = 2) -> bytes:
        """
        Convert a FeatureCollection to JSON bytes.
        
        This utility method is useful for saving FeatureCollections to files
        or preparing them for transmission.
        
        Args:
            fc (FeatureCollection): The FeatureCollection to convert
            indent (int): JSON indentation level for pretty printing
            
        Returns:
            bytes: UTF-8 encoded JSON representation of the FeatureCollection
        """
        return json.dumps(fc, indent=indent).encode("utf-8")
    
    @staticmethod
    def estimate_area(geojson_feature):
        """
        Estimate the area of a GeoJSON feature in square meters using equal-area projection.
        
        This method uses a local Albers Equal Area projection centered on the
        feature's centroid to provide accurate area calculations.
        
        Args:
            geojson_feature (dict): A GeoJSON feature object containing geometry
            
        Returns:
            float: Area in square meters, or 0.0 if calculation fails
        """
        try:
            # Create a shapely geometry from the GeoJSON
            geom = shape(geojson_feature['geometry'])
            
            # Use an equal-area projection based on centroid of geometry
            lon, lat = geom.centroid.x, geom.centroid.y
            local_aea = CRS.from_proj4(
                f"+proj=aea +lat_0={lat} +lon_0={lon} +lat_1={lat-2} +lat_2={lat+2} +datum=WGS84 +units=m"
            )
            
            # Transformer from WGS84 (EPSG:4326) to local equal-area projection
            transformer = Transformer.from_crs("EPSG:4326", local_aea, always_xy=True)
            
            # Reproject geometry
            projected_geom = shapely.ops.transform(transformer.transform, geom)
            return projected_geom.area
                        
        except Exception as e:
            print(f"Error calculating area: {e}")
            return 0.0
