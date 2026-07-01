# Nearmap Cost Estimation Application
# This application provides a web interface for estimating the cost of Nearmap API requests
# based on geographic areas and selected resource types.
import streamlit as st
import pandas as pd
from map_helper import BoxDrawer, STATUS_COLORS, tile_at_point
from nearmap_helper import NearMapHelper
from tile_details import summarize_tile
from resource_labels import label_for, ordered_keys
import layer_config
from folium.plugins import Draw
import json
import time
from datetime import datetime, timezone
import quote_export
from api_cost_estimation.estimators import (
    estimate_cost,
    count_tiles,
    aggregate_results,
    DEFAULT_MAX_WORKERS,
)

# Tiling thresholds for the API-based ("by_api_return") estimate (see caveat E):
TILE_WARN_THRESHOLD = 50   # confirm before running more than this many preview calls
TILE_HARD_CAP = 2000       # refuse above this — ask the user to draw a smaller area
SECONDS_PER_TILE = 0.5     # approx wall-clock per preview call (network latency); the
                           # tiles run concurrently, so the time estimate divides by the
                           # worker-pool size (DEFAULT_MAX_WORKERS)


# Configure the Streamlit Page
# Sets up the main page configuration for the Nearmap Cost Estimator application
st.set_page_config(
    page_title="Nearmap Cost Estimator", 
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapses sidebar if present to save space
)

# Remove default padding in the UI
# Custom CSS to optimize the layout and reduce unnecessary spacing
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 3rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

class OtherHelpers:
    """
    Utility class containing helper methods for various operations.
    
    This class provides methods for:
    - JSON validation
    - Area calculation
    - UI dialog management
    """
    
    @staticmethod
    def is_valid_json(json_string: str) -> bool:
        """
        Validate if a string is valid JSON.
        
        Args:
            json_string (str): String to validate as JSON
            
        Returns:
            bool: True if valid JSON, False otherwise
        """
        try:
            json.loads(json_string)
            return True
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            return False

    @staticmethod
    @st.dialog("Cost Table", width="medium", dismissible=True, on_dismiss="ignore")
    def seeCostTable():
        """
        Display the cost table in a Streamlit dialog.
        
        Shows the cost table with credit consumption information for different
        content types per request or 1,000sqm, based on single or multiple captures.
        """
        st.write("The cost table displays the number of credits consumed for different content types per request or 1,000sqm whichever is less, based on whether you access a single capture or multiple captures.")
        st.dataframe(pd.DataFrame(json.load(open("cost_table.json"))))

    @staticmethod
    @st.dialog("Manage available layers", width="medium", dismissible=True, on_dismiss="ignore")
    def manageLayersModal():
        """View/edit which layers are selectable for this deployment (feature 3).

        The tool is account-irrelevant, so this is a manual, deployment-level list
        stored in ``layer_availability.json`` (which ships inside the Docker image).
        Layers turned off appear greyed-out in the selection list. Edits persist to
        that file; commit it (or mount a volume) to make changes permanent across
        image rebuilds / a Streamlit Cloud redeploy.
        """
        st.write(
            "Toggle which layers users can select. Layers turned off appear greyed-out "
            "in the selection list. Saved to `layer_availability.json`."
        )
        current = layer_config.load_availability()
        new_state = {
            resource: st.checkbox(label_for(resource), value=current[resource], key=f"avail_{resource}")
            for resource in layer_config.all_resource_keys()
        }

        def _close():
            # Drop the dialog's widget state so it re-seeds from the file next time.
            for resource in layer_config.all_resource_keys():
                st.session_state.pop(f"avail_{resource}", None)
            st.rerun()

        col1, col2 = st.columns(2)
        if col1.button("Save", type="primary", icon="💾", width="stretch"):
            layer_config.save_availability(new_state)
            _close()
        if col2.button("Cancel", icon="✖️", width="stretch"):
            _close()


    @staticmethod
    def render_outcome():
        """Render the estimation outcome inline (not a modal) so it shows alongside the
        coverage map (#3). Reads the persistent ``last_result`` / ``last_per_aoi``.
        """
        r = st.session_state['last_result']
        covered = r['tiles_with_coverage']
        no_coverage = r['tiles_no_coverage']
        errored = r['tiles_errored']

        # Only show ">=" when tiles ERRORED for a non-coverage reason (timeout, 5xx,
        # rate-limit, ...) — those could hide real cost. 404 "no coverage" tiles
        # (ocean / outside the date window) are genuinely $0, so they do NOT make the
        # figure a lower bound.
        if errored and covered == 0:
            api_value = "API error"
        elif errored:
            api_value = f"≥ {r['by_api_return']:,}"
        else:
            api_value = f"{r['by_api_return']:,}"

        st.markdown("#### Estimation outcome")
        # Show how many layers drove this estimate (feature 1).
        resources = r.get('resources', [])
        if resources:
            st.caption(f"**{len(resources)}** layer(s) selected: {', '.join(resources)}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="By API (tiled preview)", value=api_value)
            st.caption(
                f"{r['tiles']} tiles · {covered} covered · {no_coverage} no coverage · {errored} errored"
            )
        with col2:
            st.metric(label="By Area (legacy)", value=f"{r['by_area']:,}")
            st.caption("Original area-based estimate")

        if errored:
            detail = r.get('first_error')
            if covered == 0:
                msg = (
                    f"All {r['tiles']} tiles errored, so no cost could be computed. This is "
                    "usually a bad/over-long request (e.g. an unsupported resource in the "
                    "selection) or an auth/rate-limit issue — not random failures."
                )
            else:
                msg = (
                    f"Showing ≥ because {errored} of {r['tiles']} tiles errored and were "
                    "counted as 0 — the true cost may be higher. Re-submit to retry."
                )
            if detail:
                msg += f"\n\nFirst error returned by the API: `{detail}`"
            st.warning(msg)
        elif no_coverage:
            st.info(
                f"{no_coverage} of {r['tiles']} tiles had no coverage (e.g. ocean or "
                "outside the date range) and are correctly billed at 0 credits — "
                "this figure is exact."
            )

        # Per-polygon breakdown when several polygons were estimated (#4: it's one AOI
        # with multiple polygons, not multiple AOIs); totals above are the grand totals.
        per_poly = st.session_state.get('last_per_aoi', [])
        if len(per_poly) > 1:
            st.markdown(f"**Per-polygon breakdown** ({len(per_poly)} polygons)")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Polygon": i + 1,
                        "area (sqm)": round(p["area_sqm"]),
                        "tiles": p["tiles"],
                        "covered": p["tiles_with_coverage"],
                        "by API": p["by_api_return"],
                        "by area": p["by_area"],
                    }
                    for i, p in enumerate(per_poly)
                ]),
                hide_index=True,
            )

    @staticmethod
    def render_tile_details(tiles):
        """Show what the API returned for the selected tile as one property table + raw JSON.

        Selection is owned by the ``tile_select_box`` selectbox state; a map click writes the
        clicked tile's index into it. No API calls — everything comes from the tile record
        cached at estimation time. The how-to hint is shown at the top of the inspection
        section, so nothing is rendered here until a tile is selected.
        """
        idx = st.session_state.get('tile_select_box')
        if idx is None or not (0 <= idx < len(tiles)):
            return

        # The panel renders below the map, which can be off-screen — so when the selection
        # changes, pop a toast (shown regardless of scroll position) pointing to it.
        if st.session_state.get('_last_toasted') != idx:
            st.session_state['_last_toasted'] = idx
            st.toast(f"Showing details for Tile #{idx + 1} below ↓", icon="📍")

        tile = tiles[idx]
        s = summarize_tile(tile, idx)
        srcs = ", ".join(str(p + 1) for p in s["source_polygons"]) or "—"
        dates = ", ".join(sv["date"] for sv in s["surveys"] if sv.get("date")) or "—"
        # Unique content types across the tile's surveys, shown with human-readable names.
        seen, cts = set(), []
        for sv in s["surveys"]:
            for ct in sv["content_types"]:
                if ct not in seen:
                    seen.add(ct)
                    cts.append(label_for(ct))
        content = ", ".join(cts) or "—"

        # A bordered card with a status-coloured dot (matching the map legend) so the panel
        # reads as something that appeared, not just text flowing below.
        color = STATUS_COLORS.get(s["status"], "#888888")
        with st.container(border=True):
            st.markdown(
                f"#### <span style='color:{color};font-size:0.9em'>■</span> "
                f"Tile #{s['number']} — {s['status']}",
                unsafe_allow_html=True,
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        ("Credit", f"{s['credits']:,}"),
                        ("Area", f"{round(s['area_sqm']):,} m²"),
                        ("Polygon ID", srcs),
                        ("Capture date", dates),
                        ("Content types", content),
                    ],
                    columns=["Property", "Value"],
                ),
                hide_index=True,
                use_container_width=True,
            )
            if s["status"] == "errored" and s["error"]:
                st.warning(f"This tile errored and was counted as 0 credits: {s['error']}")
            with st.expander("Raw API response", expanded=True):
                st.json(tile.get("coverage") or {"status": s["status"], "error": s["error"]})

    @staticmethod
    def run_estimation(req):
        """Estimate every polygon in the request, rendering a single progress bar (feature 7).

        Runs ``estimate_cost`` per feature in ``st.session_state.geodata_features`` and
        persists the grand-total aggregate ('last_result', for the inline outcome panel +
        export), 'last_per_aoi' (per-polygon table) and 'last_coverage_tiles' (overlay).
        """
        features = st.session_state.geodata_features
        grand_total = req['n_tiles']  # summed tile count across all features (from the gate)
        progress = st.progress(0.0, text="Querying Nearmap preview API…")

        try:
            per_aoi = []
            base = 0  # tiles completed in earlier AOIs, for the overall progress fraction
            for i, feature in enumerate(features):
                def cb(done, total, total_cost, skipped, _base=base, _i=i):
                    overall = (_base + done) / grand_total if grand_total else 1.0
                    progress.progress(
                        min(overall, 1.0),
                        text=f"Polygon {_i + 1}/{len(features)} · tile {done}/{total} · {total_cost:,} credits",
                    )

                res = estimate_cost(
                    feature,
                    req['resources'],
                    req['api_key'],
                    since=req['since'],
                    until=req['until'],
                    dates_single=req['dates'],
                    progress_cb=cb,
                )
                per_aoi.append(res)
                base += res['tiles']

            aggregate = aggregate_results(per_aoi, req['resources'])
            aggregate['estimated_at'] = datetime.now(timezone.utc).isoformat()
            # Persist for the inline outcome panel + per-polygon table, the coverage
            # overlay (feature 2) and the quote export (feature 4).
            st.session_state['last_result'] = aggregate
            st.session_state['last_per_aoi'] = per_aoi
            st.session_state['last_coverage_tiles'] = [
                tile for r in per_aoi for tile in r['plan']['tiles']
            ]
            # New estimation -> drop any prior tile-inspection selection so a stale index
            # can't point at the wrong tile in the new result.
            st.session_state.pop('tile_select_box', None)
            st.session_state.pop('_last_processed_click', None)
            st.session_state.pop('_last_toasted', None)
        except Exception as e:
            st.session_state['latestErrorMessage'] = str(e)
            OtherHelpers.seeErrorModal()
        finally:
            progress.empty()

    @staticmethod
    @st.dialog("Error", width="small", dismissible=True, on_dismiss="ignore")
    def seeErrorModal():
        """
        Display error messages in a Streamlit dialog.
        
        Shows the latest error message from session state if available,
        otherwise displays a default message.
        """
        if ('latestErrorMessage' in st.session_state):
            st.error(st.session_state['latestErrorMessage'])
            st.session_state.pop('latestErrorMessage')
        else:
            st.write('Nothing to report, please close this dialog window.')


@st.fragment
def render_coverage_inspect(coverage_tiles):
    """Coverage map + tile inspection, isolated in a Streamlit fragment.

    Clicking a tile makes st_folium rerun the script to report the click. Wrapping this
    section in a fragment scopes that rerun to *only here*, so the rest of the page (the
    form, header and drawing map) no longer flashes on every click. A click is applied
    once — deduped on its lat/lng, which st_folium keeps returning across reruns — so a
    later selectbox choice isn't clobbered by the persisted last click.
    """
    map_result = BoxDrawer(height=500).show_coverage(coverage_tiles, key="coverage_map")

    # Map click -> tile index. Prefer the object click; fall back to any map click. A click
    # that hits no tile leaves the selection unchanged.
    clicked = None
    if isinstance(map_result, dict):
        clicked = map_result.get("last_object_clicked") or map_result.get("last_clicked")
    if clicked and clicked.get("lat") is not None:
        click_id = (clicked["lat"], clicked["lng"])
        if st.session_state.get("_last_processed_click") != click_id:
            st.session_state["_last_processed_click"] = click_id
            hit = tile_at_point(coverage_tiles, clicked["lat"], clicked["lng"])
            if hit is not None:
                st.session_state["tile_select_box"] = hit

    # Drop a stale selection (e.g. a re-estimation produced fewer tiles).
    sel = st.session_state.get("tile_select_box")
    if sel is not None and not (0 <= sel < len(coverage_tiles)):
        st.session_state.pop("tile_select_box", None)

    # ── Tile inspection ────────────────────────────────────────────────────────
    st.divider()
    st.caption("👆 Click a tile on the map, or pick one below, to see its API response.")
    st.selectbox(
        "Inspect tile #",
        options=list(range(len(coverage_tiles))),
        index=None,
        placeholder="Click a tile or pick one…",
        format_func=lambda i: f"#{i + 1} — {coverage_tiles[i].get('status', 'covered')}",
        key="tile_select_box",
    )
    OtherHelpers.render_tile_details(coverage_tiles)


# Main Application UI
# Create the main layout with header and logo columns
col1, col2, col3 = st.columns([10,1,1], gap="small")
with col1:
    # Application title
    st.markdown(
        """
        <div style='display: flex; align-items: center; height: 120px;'>
            <h1 style='margin: 0;'>Nearmap Cost Estimation</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    # AURIN logo
    st.markdown(
            "<div style='display: flex; align-items: center;'>"
            "<img src='https://data.aurin.org.au/assets/aurin-logo-400-D0zkc36m.png' style='height: 120px; margin: auto;'> "
            "</div>",
            unsafe_allow_html=True
        )
with col3:
    # Nearmap logo
    st.markdown(
            "<div style='display: flex; align-items: center;'>"
            "<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Nearmap-logo.png/1200px-Nearmap-logo.png' style='height: 120px; margin: auto;'> "
            "</div>",
            unsafe_allow_html=True
        )

# Main content area with left sidebar and right map area
left, right = st.columns([1, 3], gap="large")

# Initialize session state for tracking if geographic data is ready
if 'geodata_ready' not in st.session_state:
    st.session_state.geodata_ready = False


with left:
    # Left sidebar containing form controls
    # API Key Input - secure text input for Nearmap API key
    api_key = st.text_input("Enter Your Nearmap API Key", type="password", value="")
    
    # Resource Type Selection
    # Container for resource type checkboxes with scrollable area
    box_resource = st.container(height=320, border=True)
    with box_resource:
        st.write("Select Resource Type(s):")
        # Resources grouped by namespace (raster / AI packs / true-ortho / impact) so the
        # list is easier to navigate (#2).
        resources_object = NearMapHelper.get_all_resources()
        all_tuples = resources_object['all_tuples']  # full resource keys -> cost info
        # Deployment-level availability (feature 3): layers marked unavailable are shown
        # but disabled, so users can't order a pack this deployment hasn't enabled.
        availability = layer_config.load_availability()
        # A layer marked unavailable must not stay ticked (#8): clear its checkbox state
        # BEFORE the widget is instantiated this run (it can't be modified afterwards).
        for resource in all_tuples:
            if not availability.get(resource, True) and st.session_state.get(resource):
                st.session_state[resource] = False
        selected_resources = []  # List to store user-selected resources

        NAMESPACE_LABELS = {
            "raster": "Raster",
            "aiPacks": "AI packs",
            "trueOrthoAiPacks": "True Ortho AI packs",
            "aiImpactAssessment": "AI Impact Assessment",
        }
        # One collapsible group per namespace; the checkbox key stays the full resource
        # id (e.g. "raster:Vert") while the label shows the human-readable catalogue name.
        # Items are ordered to match the Nearmap website AI Packs catalogue.
        for namespace in resources_object['namespaces']:
            keys = [f"{namespace}:{n}" for n in resources_object['resources'].get(namespace, [])]
            keys = [k for k in keys if k in all_tuples]
            keys = ordered_keys(namespace, keys)
            if not keys:
                continue
            label = NAMESPACE_LABELS.get(namespace, namespace)
            with st.expander(f"{label} ({len(keys)})", expanded=namespace in ("raster", "aiPacks")):
                for resource in keys:
                    is_available = availability.get(resource, True)
                    checked = st.checkbox(
                        label_for(resource),
                        key=resource,
                        disabled=not is_available,
                        help=None if is_available else
                        "Marked unavailable for this deployment — enable it via “Manage layers”.",
                    )
                    if is_available and checked:
                        selected_resources.append(resource)

    # Open the editor for the deployment's available-layers list (feature 3).
    if st.button("⚙️ Manage layers", help="View / edit which layers are selectable"):
        OtherHelpers.manageLayersModal()
    
    # Date Range Selection
    box_date = st.container(height="content", border=True)
    with box_date:
        # Date inputs for query time range
        since = st.date_input("Start date", value="2024-01-01", format="YYYY-MM-DD")
        until = st.date_input("End date", value="2024-12-31", format="YYYY-MM-DD")

    # Capture Date Preference
    box_radio_button = st.container(height="content", border=True)
    with box_radio_button:
        st.write("Capture dates")
        # Toggle for selecting between latest capture only or all captures
        dates_single = st.toggle(
            "Latest capture only",
            value=True,
            help="If on: returns only the most recent capture. If off: returns all available captures."
    )

    # Map toggle value to API parameter
    st.session_state.dates_single = "single" if dates_single else "all"
    

    # Action buttons
    button_col1, button_col2 = st.columns(2, gap=None)
    with button_col1:
        # Primary button to submit the cost estimation request
        if st.button("Submit Estimation", type="primary", help="Submit the estimation to the API", icon="🔥"):
            # Validation checks before making API request
            if not api_key:
                st.session_state['latestErrorMessage'] = "Please enter an API key."
                OtherHelpers.seeErrorModal()
            elif not selected_resources:
                st.session_state['latestErrorMessage'] = "Please select at least one resource type."
                OtherHelpers.seeErrorModal()
            elif not st.session_state.geodata_ready:
                st.session_state['latestErrorMessage'] = "Either upload a geojson or select the extent on the map."
                OtherHelpers.seeErrorModal()
            else:
                # All validations passed. Tile every AOI locally first (no API calls)
                # so very large jobs are gated on the *combined* tile count (caveat E +
                # feature 7: a batch can blow the cap even if each AOI is under it).
                features = st.session_state.geodata_features
                try:
                    n_tiles = sum(count_tiles(f['geometry']) for f in features)
                except Exception as e:
                    st.session_state['latestErrorMessage'] = f"Could not read the drawn/uploaded area: {e}"
                    OtherHelpers.seeErrorModal()
                    n_tiles = None

                if n_tiles is not None and n_tiles > TILE_HARD_CAP:
                    st.session_state['latestErrorMessage'] = (
                        f"These {len(features)} polygon(s) tile into {n_tiles:,} API calls "
                        f"(cap {TILE_HARD_CAP:,}). Please draw or upload smaller area(s)."
                    )
                    OtherHelpers.seeErrorModal()
                elif n_tiles is not None:
                    # Stash the request; the handler below runs it (immediately if
                    # small, or after confirmation if it needs many calls).
                    st.session_state['pending_request'] = {
                        'api_key': api_key,
                        'resources': list(selected_resources),
                        'since': str(since),
                        'until': str(until),
                        'dates': st.session_state.dates_single,
                        'n_tiles': n_tiles,
                        'n_polygons': len(features),
                        'auto': n_tiles <= TILE_WARN_THRESHOLD,
                    }
    with button_col2:
        # Secondary button to view the cost table
        if st.button("See Cost Table", type="secondary", help="See the cost table", icon="📊"):
            OtherHelpers.seeCostTable()

    # Run a pending API estimation. Small jobs run immediately; large ones (many
    # tiles = many preview calls) ask for confirmation first (caveat E).
    if 'pending_request' in st.session_state:
        req = st.session_state['pending_request']
        if req.get('auto'):
            st.session_state.pop('pending_request', None)
            OtherHelpers.run_estimation(req)
        else:
            est_min = req['n_tiles'] * SECONDS_PER_TILE / DEFAULT_MAX_WORKERS / 60
            st.warning(
                f"{req.get('n_polygons', 1)} polygon(s) tile into {req['n_tiles']:,} preview "
                f"API calls (~{est_min:.1f} min at {DEFAULT_MAX_WORKERS} parallel). Proceed?"
            )
            confirm_col1, confirm_col2 = st.columns(2)
            if confirm_col1.button("Proceed", type="primary", icon="✅", width="stretch"):
                st.session_state.pop('pending_request', None)
                OtherHelpers.run_estimation(req)
            if confirm_col2.button("Cancel", icon="✖️", width="stretch"):
                st.session_state.pop('pending_request', None)

    # Export the last estimation as an auditable quote (feature 4): CSV / JSON with a
    # pricing snapshot + timestamp.
    if 'last_result' in st.session_state:
        quote = quote_export.build_quote(st.session_state['last_result'])
        st.markdown("**Export last quote**")
        export_col1, export_col2 = st.columns(2)
        export_col1.download_button(
            "⬇️ CSV", data=quote_export.quote_to_csv(quote),
            file_name="nearmap_quote.csv", mime="text/csv", width="stretch",
            help="Resources, area, tiles, cost, pricing snapshot + timestamp",
        )
        export_col2.download_button(
            "⬇️ JSON", data=quote_export.quote_to_json(quote),
            file_name="nearmap_quote.json", mime="application/json", width="stretch",
            help="Same quote as machine-readable JSON",
        )


with right:
    # Right side containing map and file upload functionality
    # File uploader for GeoJSON files
    uploaded_file = st.file_uploader('Upload GeoJSON', type=["geojson", "json"])
    
    # Initialize map drawer with Melbourne coordinates as default center
    drawer = BoxDrawer(center=(-37.8136, 144.9631), zoom=12, height=500)
    
    if uploaded_file:
        # Handle uploaded GeoJSON file
        geojson = uploaded_file.getvalue()
        if geojson and OtherHelpers.is_valid_json(geojson):
            # Valid GeoJSON uploaded
            fc = json.loads(geojson)
            # Keep ALL features (feature 7: multi-AOI), not just the first one.
            features = fc["features"] if fc.get("type") == "FeatureCollection" else [fc]
            if features:
                st.session_state.geodata_ready = True
                st.session_state.geodata_features = features
                drawer.show_geojson(fc)  # Display the GeoJSON on the map
                st.success(f"GeoJSON uploaded — {len(features)} feature(s).")
            else:
                st.info("Upload a GeoJSON with at least one feature.")
        else:
            st.info("Upload a valid GeoJSON.")
    else:
        # No file uploaded, show interactive map
        drawer.render()
        # Get ALL drawn features from the map (feature 7: estimate several at once).
        fc = drawer.feature_collection()
        if fc["features"]:
            # User has drawn one or more polygons
            st.session_state.geodata_ready = True
            st.session_state.geodata_features = fc["features"]
        else:
            # Nothing drawn / geometry cleared: hide the coverage overlay so it doesn't
            # linger on a removed AOI (#3). The last result is kept so the user can still
            # reopen / export the previous estimate.
            st.session_state.geodata_ready = False
            st.session_state.pop('last_coverage_tiles', None)
            st.session_state.pop('tile_select_box', None)  # clear tile inspection too
            st.session_state.pop('_last_processed_click', None)
            st.session_state.pop('_last_toasted', None)

    # After an estimation, show the outcome panel and the coverage map together (#3):
    # the numbers and the colour-coded tiles for the same run, inline in this pane. No
    # modal, so there's nothing to flash away and nothing to "reopen".
    coverage_tiles = st.session_state.get('last_coverage_tiles')
    if coverage_tiles:
        st.divider()  # separate the AOI/map-selection part from the estimation result
        OtherHelpers.render_outcome()
        st.markdown("**Coverage result**")
        legend = " &nbsp;&nbsp; ".join(
            f"<span style='color:{STATUS_COLORS[k]};font-size:1.2em'>■</span> {label}"
            for k, label in (
                ("covered", "covered"),
                ("no_coverage", "no coverage ($0)"),
                ("errored", "errored"),
            )
        )
        st.markdown(legend, unsafe_allow_html=True)
        # Map + tile inspection run inside a fragment so a tile click reruns only that
        # section (not the whole page — that full rerun is what made the UI flash).
        render_coverage_inspect(coverage_tiles)

# The estimation outcome now renders inline in the right pane (above the coverage map),
# so the numbers and the map are visible at the same time (#3) — no modal needed.