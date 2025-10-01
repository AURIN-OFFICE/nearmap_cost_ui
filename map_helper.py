from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

import folium
from folium.plugins import Draw
from streamlit_folium import st_folium


GeoJSON = Dict[str, Any]
Feature = Dict[str, Any]
FeatureCollection = Dict[str, Any]


class BoxDrawer:
    """
    A small helper to:
      - build a Folium map with a rectangle-only drawing tool
      - render it in Streamlit
      - extract drawings as GeoJSON FeatureCollection
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
        self.center = center
        self.zoom = zoom
        self.height = height
        self.width = width
        self.control_scale = control_scale
        self.prefer_canvas = prefer_canvas

        self._map: Optional[folium.Map] = None
        self._render_result: Optional[Dict[str, Any]] = None

    # --- public API ---------------------------------------------------------

    def render(self) -> None:
        """Create the map with rectangle draw control and render it via st_folium."""
        m = folium.Map(
            location=list(self.center),
            zoom_start=self.zoom,
            control_scale=self.control_scale,
            prefer_canvas=self.prefer_canvas,
        )

        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": False,
                "polygon": True,
                "circle": False,
                "circlemarker": False,
                "marker": False,
                "rectangle": False,
            },
            edit_options={"edit": False, "remove": True},
        ).add_to(m)

        self._map = m
        # st_folium returns a dict with draw results
        self._render_result = st_folium(m, height=self.height, width=self.width)

    def show_geojson(self, geojson: GeoJSON) -> None:
        """
        Create a Folium map, add the provided GeoJSON layer, and render it in Streamlit.
        """
        m = folium.Map(
            location=list(self.center),
            zoom_start=self.zoom,
            control_scale=self.control_scale,
            prefer_canvas=self.prefer_canvas,
        )

        # Add GeoJSON layer
        folium.GeoJson(
            geojson,
            name="geojson_layer"
        ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Render in Streamlit
        st_folium(m, height=self.height, width=self.width, returned_objects=[])
    
    
    def feature_collection(self) -> FeatureCollection:
        """Return all drawings as a GeoJSON FeatureCollection."""
        drawings = self._get_all_drawings()
        return self._as_feature_collection(drawings)

    def last_feature_collection(self) -> Optional[FeatureCollection]:
        """Return just the last active drawing as a FeatureCollection (or None)."""
        if not isinstance(self._render_result, dict):
            return None

        last = self._render_result.get("last_active_drawing")
        if not last:
            return None

        if isinstance(last, dict) and last.get("type") == "Feature":
            feat: Feature = last
        else:
            # Fallback: wrap geometry-like dicts as a Feature
            feat = {"type": "Feature", "properties": {}, "geometry": last}

        return {"type": "FeatureCollection", "features": [feat]}

    def bbox(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Convenience: if the last drawing is a rectangle (Polygon), return bbox as
        (min_lon, min_lat, max_lon, max_lat). Returns None if unavailable.
        """
        fc = self.last_feature_collection()
        if not fc or not fc["features"]:
            return None

        geom = fc["features"][0].get("geometry") or {}
        if geom.get("type") != "Polygon":
            return None

        # Leaflet rectangle emits a simple ring: [[lon, lat], ...]
        coords = geom.get("coordinates") or []
        if not coords or not coords[0]:
            return None

        ring = coords[0]  # exterior ring
        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        return (min(lons), min(lats), max(lons), max(lats))

    # --- internal helpers ---------------------------------------------------

    def _get_all_drawings(self) -> List[Feature]:
        """Normalize across st_folium versions: gather all features drawn."""
        if not isinstance(self._render_result, dict):
            return []

        drawings: List[Feature] = (
            self._render_result.get("all_drawings")
            or self._render_result.get("drawn_features")
            or []
        )

        # Ensure each item is a Feature
        features: List[Feature] = []
        for item in drawings:
            if isinstance(item, dict) and item.get("type") == "Feature":
                features.append(item)
            elif isinstance(item, dict):
                features.append(
                    {"type": "Feature", "properties": {}, "geometry": item}
                )
        return features

    @staticmethod
    def _as_feature_collection(features: List[Feature]) -> FeatureCollection:
        return {"type": "FeatureCollection", "features": features}

    # --- utilities ----------------------------------------------------------

    @staticmethod
    def to_bytes(fc: FeatureCollection, indent: int = 2) -> bytes:
        return json.dumps(fc, indent=indent).encode("utf-8")
