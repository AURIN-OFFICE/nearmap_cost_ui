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


# Configure the Streamlit Page
# Sets up the main page configuration for the Nearmap Cost Estimator application
st.set_page_config(
    page_title="Nearmap Cost Estimator", 
    page_icon=":money:", 
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
        st.write("The estimated cost of requested query is as follows:")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label='Total Cost', value=f"{st.session_state['cost']}")
        with col2:
            # st.metric(label='Remaining Credits', value=f"{st.session_state['remaining_credits']}")
            st.write("Remaining Credits: To be implemented")
        st.session_state.pop('cost')

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
                # All validations passed, proceed with API request
                try:
                    with st.spinner("Waiting for API response..."):
                        # Initialize helper with user inputs
                        helper = NearMapHelper(api_key, str(since), str(until), ', '.join(selected_resources), st.session_state.dates_single)
                        # Make API request with the selected area
                        response = helper.get_transaction_content(st.session_state.geodata['geometry'])
                        # Extract cost estimate from response
                        cost = helper.get_cost_estimate(response)
                        time.sleep(3)  # Brief delay for user experience
                        st.session_state['cost'] = cost  # Store cost in session state
                        
                except Exception as e:
                    # Handle API errors with fallback calculation
                    if "INVALID_AREA" in str(e):
                        # Fallback: Calculate cost manually when API returns invalid area error
                        total_cost = 0  # Initialize total cost counter
                        ai_counter = 0  # Counter for AI packs (max 7)
                        # Calculate area in square meters
                        area_sqm = BoxDrawer.estimate_area(st.session_state.geodata)
                        all_resources = NearMapHelper.get_all_resources()['all_tuples']
                        
                        # Calculate cost for each selected resource
                        for resource in selected_resources:
                            resource_object = all_resources[resource]
                            namespace = resource.split(":")[0]  # Extract namespace (raster, aiPacks, etc.)
                            # Select appropriate cost based on date preference
                            unit_cost = resource_object['Credits (single survey)'] if st.session_state.dates_single == "single" else resource_object['Credits (all survey data)']
                            
                            # Apply cost calculation based on resource type
                            if (namespace != "aiPacks"):
                                # Standard cost calculation for non-AI resources
                                total_cost += round(unit_cost*area_sqm/1000)
                            elif (namespace == "aiPacks" and ai_counter < 7):
                                # AI packs limited to 7 maximum
                                ai_counter += 1
                                total_cost += round(unit_cost*area_sqm/1000)
                            else:
                                # Skip additional AI packs beyond limit
                                pass

                        st.session_state['cost'] = total_cost
                    else:
                        # Handle other API errors
                        st.session_state['latestErrorMessage'] = str(e)
                        OtherHelpers.seeErrorModal()
    with button_col2:
        # Secondary button to view the cost table
        if st.button("See Cost Table", type="secondary", help="See the cost table", icon="📊"):
            OtherHelpers.seeCostTable()


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
if ('cost' in st.session_state):
    OtherHelpers.seeResultModal()