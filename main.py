import streamlit as st
import requests
import pandas as pd
import folium
from map_helper import BoxDrawer
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import time
from shapely.geometry import shape
from shapely.ops import transform
import pyproj
from functools import partial
from pyproj import Transformer, CRS
import shapely

# Configure the Streamlit Page
st.set_page_config(
    page_title="Nearmap Cost Estimator", 
    page_icon=":money:", 
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapses sidebar if present to save space
)

# Remove default padding in the UI
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

class NearMapHelper:
    @staticmethod
    def get_all_resources():
        return {
            "namespaces": ["raster", "aiPacks", "trueOrthoAiPacks", "aiImpactAssessment"],
            "resources": {
                "raster": [
                "Vert",
                "DetailDtm",
                "DetailDsm",
                "TrueOrtho",
                "North",
                "East",
                "South",
                "West"
                ],
                "aiPacks": [
                "building",
                "building_char",
                "construction",
                "debris",
                "pavement_marking",
                "poles",
                "pool",
                "postcat",
                "roof_char",
                "roof_cond",
                "roof_objects",
                "solar",
                "surface_permeability",
                "surfaces",
                "trampoline",
                "vegetation"
                ],
                "trueOrthoAiPacks": [
                "building",
                "building_char"
                ],
                "aiImpactAssessment": [
                "postcat"
                ]
            },
            "all_tuples": {
                "raster:Vert": {
                    "Credits (single survey)": 10,
                    "Credits (all survey data)": 15.0,
                    "matched_content_type": "Vertical"
                },
                "raster:DetailDtm": {
                    "Credits (single survey)": 20,
                    "Credits (all survey data)": 30.0,
                    "matched_content_type": "DEM/DTM"
                },
                "raster:DetailDsm": {
                    "Credits (single survey)": 30,
                    "Credits (all survey data)": 45.0,
                    "matched_content_type": "DSM"
                },
                "raster:TrueOrtho": {
                    "Credits (single survey)": 20,
                    "Credits (all survey data)": 30.0,
                    "matched_content_type": "True Ortho"
                },
                "raster:North": {
                    "Credits (single survey)": 4,
                    "Credits (all survey data)": 6.0,
                    "matched_content_type": "Panorama (north)"
                },
                "raster:East": {
                    "Credits (single survey)": 4,
                    "Credits (all survey data)": 6.0,
                    "matched_content_type": "Panorama (east)"
                },
                "raster:South": {
                    "Credits (single survey)": 4,
                    "Credits (all survey data)": 6.0,
                    "matched_content_type": "Panorama (south)"
                },
                "raster:West": {
                    "Credits (single survey)": 4,
                    "Credits (all survey data)": 6.0,
                    "matched_content_type": "Panorama (west)"
                },
                "aiPacks:building": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:building_char": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:construction": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:debris": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:pavement_marking": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:poles": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:pool": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:postcat": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:roof_char": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:roof_cond": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:roof_objects": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:solar": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:surface_permeability": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:surfaces": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:trampoline": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiPacks:vegetation": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "trueOrthoAiPacks:building": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "trueOrthoAiPacks:building_char": {
                    "Credits (single survey)": 5,
                    "Credits (all survey data)": 7.5,
                    "matched_content_type": "AI (1 pack)"
                },
                "aiImpactAssessment:postcat": {
                    "Credits (single survey)": 35,
                    "Credits (all survey data)": 52.5,
                    "matched_content_type": "Nearmap ImpactAssessment AI"
                }
                }
        }

    def __init__(self, API_KEY, since, until, resources, dates_single):
        self.API_KEY = API_KEY
        self.since = since
        self.until = until
        self.resources = resources
        self.dates_single = dates_single
    def get_data(self, url, headers):
        response = requests.get(url, headers=headers)
        
        # Debug: Print response details
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text[:500]}...")
        
        # Check if response is successful
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
        
        # Check if response has content
        if not response.text.strip():
            raise Exception("API returned empty response")
        
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response. Response content: {response.text[:200]}...")
    
    def post_data(self, url, payload, headers):
        response = requests.post(url, json=payload, headers=headers)
        
        # Debug: Print response details
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Content: {response.text[:500]}...")  # First 500 chars
        
        # Check if response is successful
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
        
        # Check if response has content
        if not response.text.strip():
            raise Exception("API returned empty response")
        
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response. Response content: {response.text[:200]}...")
    
    def get_transaction_content(self, AOI):
        url = f"https://api.nearmap.com/coverage/v2/tx/aoi?apikey={self.API_KEY}"
        payload = {
            "preview": "true",
            "aiOn3dCoverage": "false",
            "resources": self.resources,
            "dates": self.dates_single,
            "since": self.since,
            "until": self.until,
            "overlap": "all",
            "aoi": AOI
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }   
        return self.post_data(url, payload, headers)
    
    @staticmethod
    def get_cost_estimate(response):
        return response["costOfTransaction"]
    
    @staticmethod
    def get_surveys(response):
        return response["surveys"]
    
    def get_remaining_credits(self):
        url = "https://api.betterview.net/api/properties/quota"
        headers = {"accept": "application/json", "authorization": f"Bearer {self.API_KEY}"}
        return self.get_data(url, headers)


class OtherHelpers:
    @staticmethod
    def is_valid_json(json_string: str) -> bool:
        try:
            json.loads(json_string)
            return True
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            return False

    @staticmethod
    def estimate_area(geojson_feature):
        """
        Estimate the area of a GeoJSON feature in square meters.
        
        Args:
            geojson_feature: A GeoJSON feature object
            
        Returns:
            float: Area in square meters
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

    @staticmethod
    @st.dialog("Cost Table", width="medium", dismissible=True, on_dismiss="ignore")
    def seeCostTable():
        st.write("The cost table displays the number of credits consumed for different content types per request or 1,000sqm whichever is less, based on whether you access a single capture or multiple captures.")
        st.dataframe(pd.DataFrame(json.load(open("cost_table.json"))))


    @staticmethod
    @st.dialog("Estimation Outcome", width="medium", dismissible=True, on_dismiss="ignore")
    def seeResultModal():
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
        if ('latestErrorMessage' in st.session_state):
            st.error(st.session_state['latestErrorMessage'])
            st.session_state.pop('latestErrorMessage')
        else:
            st.write('Nothing to report, please close this dialog window.')
    

# # Main body
col1, col2, col3 = st.columns([10,1,1], gap="small")
with col1:
    st.markdown(
        """
        <div style='display: flex; align-items: center; height: 120px;'>
            <h1 style='margin: 0;'>Nearmap Cost Estimation</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
            "<div style='display: flex; align-items: center;'>"
            "<img src='https://data.aurin.org.au/assets/aurin-logo-400-D0zkc36m.png' style='height: 120px; margin: auto;'> "
            "</div>",
            unsafe_allow_html=True
        )
with col3:
    st.markdown(
            "<div style='display: flex; align-items: center;'>"
            "<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Nearmap-logo.png/1200px-Nearmap-logo.png' style='height: 120px; margin: auto;'> "
            "</div>",
            unsafe_allow_html=True
        )

left, right = st.columns([1, 3], gap="large")

if 'geodata_ready' not in st.session_state:
    st.session_state.geodata_ready = False


with left:
    # API Key Input
    api_key = st.text_input("Enter Your Nearmap API Key", type="password", value="")
    
    # Resource Type Checkboxes
    
    box_resource = st.container(height=260, border=True)
    with box_resource:
        st.write("Select Resource Type(s):")
        resources_object = NearMapHelper.get_all_resources()
        resource_type = resources_object['all_tuples']
        selected_resources = []
        for resource in resource_type:
            if st.checkbox(resource, key=resource):
                selected_resources.append(resource)
    
    box_date = st.container(height="content", border=True)
    with box_date:
        since = st.date_input("Start date", value="2024-01-01", format="YYYY-MM-DD")
        until = st.date_input("End date", value="2024-12-31", format="YYYY-MM-DD")

    box_radio_button = st.container(height="content", border=True)
    with box_radio_button:
        st.write("Capture dates")
        dates_single = st.toggle(
            "Latest capture only",
            value=True,
            help="If on: returns only the most recent capture. If off: returns all available captures."
    )

    # Map it to API value
    st.session_state.dates_single = "single" if dates_single else "all"
    

    button_col1, button_col2 = st.columns(2, gap=None)
    with button_col1:
        if st.button("Submit Estimation", type="primary", help="Submit the estimation to the API", icon="🔥"):
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
                try:
                    with st.spinner("Waiting for API response..."):
                        helper = NearMapHelper(api_key, str(since), str(until), ', '.join(selected_resources), st.session_state.dates_single)
                        response = helper.get_transaction_content(st.session_state.geodata['geometry'])
                        cost = helper.get_cost_estimate(response)
                        time.sleep(3) 
                        st.session_state['cost'] = cost
                        
                except Exception as e:
                    if "INVALID_AREA" in str(e):
                        total_cost = 0
                        ai_counter = 0
                        area_sqm = OtherHelpers.estimate_area(st.session_state.geodata)
                        all_resources = NearMapHelper.get_all_resources()['all_tuples']
                        for resource in selected_resources:
                            resource_object = all_resources[resource]
                            namespace = resource.split(":")[0]
                            unit_cost = resource_object['Credits (single survey)'] if st.session_state.dates_single == "single" else resource_object['Credits (all survey data)']
                            if (namespace != "aiPacks"):
                                total_cost += round(unit_cost*area_sqm/1000)
                            elif (namespace == "aiPacks" and ai_counter < 7):
                                ai_counter += 1
                                total_cost += round(unit_cost*area_sqm/1000)
                            else:
                                pass

                        st.session_state['cost'] = total_cost
                    else:
                        st.session_state['latestErrorMessage'] = str(e)
                        OtherHelpers.seeErrorModal()
    with button_col2:
        if st.button("See Cost Table", type="secondary", help="See the cost table", icon="📊"):
            OtherHelpers.seeCostTable()


with right:
    uploaded_file = st.file_uploader('Upload GeoJSON', type=["geojson", "json"])
    drawer = BoxDrawer(center=(-37.8136, 144.9631), zoom=12, height=500)
    if uploaded_file:
        geojson = uploaded_file.getvalue()
        if geojson and OtherHelpers.is_valid_json(geojson):
            st.session_state.geodata_ready = True
            fc = json.loads(geojson)
            st.session_state.geodata = fc["features"][0]
            drawer.show_geojson(fc)
            st.success("GeoJSON successfully uploaded.")            
        else:
            st.info("Upload a valid GeoJSON.")
    else:
        drawer.render()   
        fc = drawer.last_feature_collection() or {"type": "FeatureCollection", "features": []}
        if fc["features"]:
            st.session_state.geodata_ready = True
            st.session_state.geodata = fc["features"][0]
        else:
            st.info("Draw a rectangle on the map to see the GeoJSON here.")
            
# Text Area for Query Results
if ('cost' in st.session_state):
    OtherHelpers.seeResultModal()