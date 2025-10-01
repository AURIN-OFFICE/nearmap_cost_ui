import streamlit as st
import requests
import pandas as pd
import folium
from map_helper import BoxDrawer
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import time


# Configure the Streamlit Page
st.set_page_config(
    page_title="Nearmap Cost Estimator", 
    page_icon=":money:", 
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapses sidebar if present to save space
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
            "all_tuples": [
                "raster:Vert",
                "raster:DetailDtm",
                "raster:DetailDsm",
                "raster:TrueOrtho",
                "raster:North",
                "raster:East",
                "raster:South",
                "raster:West",
                "aiPacks:building",
                "aiPacks:building_char",
                "aiPacks:construction",
                "aiPacks:debris",
                "aiPacks:pavement_marking",
                "aiPacks:poles",
                "aiPacks:pool",
                "aiPacks:postcat",
                "aiPacks:roof_char",
                "aiPacks:roof_cond",
                "aiPacks:roof_objects",
                "aiPacks:solar",
                "aiPacks:surface_permeability",
                "aiPacks:surfaces",
                "aiPacks:trampoline",
                "aiPacks:vegetation",
                "trueOrthoAiPacks:building",
                "trueOrthoAiPacks:building_char",
                "aiImpactAssessment:postcat"
            ]
        }

    def __init__(self, API_KEY, since, until, resources):
        self.API_KEY = API_KEY
        self.since = since
        self.until = until
        self.resources = resources
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
            "dates": "all",
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

def is_valid_json(json_string: str) -> bool:
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False

# # Main body
st.header("Nearmap Cost Estimation")
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
    
    box_date = st.container(height=180, border=True)
    with box_date:
        since = st.date_input("Start date", value="2024-01-01", format="YYYY-MM-DD")
        until = st.date_input("End date", value="2024-12-31", format="YYYY-MM-DD")

    if st.button("Submit Estimation", type="primary"):
        if not api_key:
            st.error("Please enter an API key.")
        elif not selected_resources:
            st.error("Please select at least one resource type.")
        elif not st.session_state.geodata_ready:
            st.error("Either upload a geojson or select the extent on the map.")
        else: 
            try:
                with st.spinner("Waiting for API response..."):
                    helper = NearMapHelper(api_key, str(since), str(until), ', '.join(selected_resources))
                    response = helper.get_transaction_content(st.session_state.geodata['geometry'])
                    cost = helper.get_cost_estimate(response)
                    time.sleep(3) 
                    st.session_state['cost'] = cost
            except Exception as e:
                st.error(e)



with right:
    uploaded_file = st.file_uploader('Upload GeoJSON')
    drawer = BoxDrawer(center=(-37.8136, 144.9631), zoom=12, height=500)
    if uploaded_file:
        geojson = uploaded_file.getvalue()
        if geojson and is_valid_json(geojson):
            st.session_state.geodata_ready = True
            fc = json.loads(geojson)
            st.session_state.geodata = fc["features"][0]
            drawer.show_geojson(fc)
            st.info("GeoJSON successfully uploaded.")
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
    box_result = st.container(height=100, border=True)
    with box_result:
        st.metric(label='Total Cost', value=f"{st.session_state['cost']}")
        # st.metric(label='Remaining Credits', value=f"{st.session_state['remaining_credits']}")
