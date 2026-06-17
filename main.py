# Nearmap Cost Estimation Application
# This application provides a web interface for estimating the cost of Nearmap API requests
# based on geographic areas and selected resource types.
import streamlit as st
import pandas as pd
from map_helper import BoxDrawer
from nearmap_helper import NearMapHelper
from folium.plugins import Draw
import json
import time
from api_cost_estimation.estimators import estimate_cost, count_tiles

# Tiling thresholds for the API-based ("by_api_return") estimate (see caveat E):
TILE_WARN_THRESHOLD = 50   # confirm before running more than this many preview calls
TILE_HARD_CAP = 2000       # refuse above this — ask the user to draw a smaller area
SECONDS_PER_TILE = 0.5     # inter-call sleep; used only to estimate wall-clock time


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
            padding-bottom: 0rem;
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
    @st.dialog("Estimation Outcome", width="medium", dismissible=True, on_dismiss="ignore")
    def seeResultModal():
        """
        Display the cost estimation results in a Streamlit dialog.
        
        Shows the total estimated cost and remaining credits (if available)
        from the session state.
        """
        r = st.session_state['result']
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

        st.write("Estimated credit cost for the requested query (two methods):")
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
        st.session_state.pop('result')

    @staticmethod
    def run_estimation(req):
        """Run both estimators for a pending request, rendering a progress bar.

        Stores the combined result (by_area + by_api_return + tile counts) in
        ``st.session_state['result']`` for the outcome dialog to display.
        """
        progress = st.progress(0.0, text="Querying Nearmap preview API…")

        def cb(done, total, total_cost, skipped):
            frac = (done / total) if total else 1.0
            progress.progress(
                frac,
                text=f"Tile {done}/{total} · {total_cost:,} credits · {skipped} skipped",
            )

        try:
            st.session_state['result'] = estimate_cost(
                st.session_state.geodata,
                req['resources'],
                req['api_key'],
                since=req['since'],
                until=req['until'],
                dates_single=req['dates'],
                progress_cb=cb,
            )
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
    box_resource = st.container(height=260, border=True)
    with box_resource:
        st.write("Select Resource Type(s):")
        # Get all available resources and their cost information
        resources_object = NearMapHelper.get_all_resources()
        resource_type = resources_object['all_tuples']  # Dictionary of resource:cost mappings
        selected_resources = []  # List to store user-selected resources
        
        # Create checkboxes for each available resource type
        for resource in resource_type:
            if st.checkbox(resource, key=resource):
                selected_resources.append(resource)
    
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
                # All validations passed. Tile the AOI locally first (no API calls)
                # so very large jobs can be gated before spending time (caveat E).
                try:
                    n_tiles = count_tiles(st.session_state.geodata['geometry'])
                except Exception as e:
                    st.session_state['latestErrorMessage'] = f"Could not read the drawn/uploaded area: {e}"
                    OtherHelpers.seeErrorModal()
                    n_tiles = None

                if n_tiles is not None and n_tiles > TILE_HARD_CAP:
                    st.session_state['latestErrorMessage'] = (
                        f"This area tiles into {n_tiles:,} API calls (cap {TILE_HARD_CAP:,}). "
                        "Please draw or upload a smaller area."
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
            est_min = req['n_tiles'] * SECONDS_PER_TILE / 60
            st.warning(
                f"This area tiles into {req['n_tiles']:,} preview API calls "
                f"(~{est_min:.1f} min). Proceed?"
            )
            confirm_col1, confirm_col2 = st.columns(2)
            if confirm_col1.button("Proceed", type="primary", icon="✅"):
                st.session_state.pop('pending_request', None)
                OtherHelpers.run_estimation(req)
            if confirm_col2.button("Cancel", icon="✖️"):
                st.session_state.pop('pending_request', None)


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
            st.session_state.geodata_ready = True
            fc = json.loads(geojson)
            st.session_state.geodata = fc["features"][0]  # Store first feature
            drawer.show_geojson(fc)  # Display the GeoJSON on the map
            st.success("GeoJSON successfully uploaded.")            
        else:
            st.info("Upload a valid GeoJSON.")
    else:
        # No file uploaded, show interactive map
        drawer.render()   
        # Get any drawn features from the map
        fc = drawer.last_feature_collection() or {"type": "FeatureCollection", "features": []}
        if fc["features"]:
            # User has drawn on the map
            st.session_state.geodata_ready = True
            st.session_state.geodata = fc["features"][0]  # Store first drawn feature
        else:
            st.info("Draw a rectangle on the map to see the GeoJSON here.")
            
# Display Results
# Show cost estimation results if available in session state
if ('result' in st.session_state):
    OtherHelpers.seeResultModal()