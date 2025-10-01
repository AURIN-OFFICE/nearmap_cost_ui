import streamlit as st
import requests
import pandas as pd

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

# # Main body
left, right = st.columns([1, 3], gap="large")

with left:
    st.header("Nearmap Cost Estimation")
    
    # API Key Input
    api_key = st.text_input("Enter Nearmap API Key", type="password", value="")
    
    # Resource Type Checkboxes
    st.subheader("Select Resource Types")
    box = st.container(height=260, border=True)   # <- fixed height makes it scroll
    with box:
        resources_object = NearMapHelper.get_all_resources()
        resource_type = resources_object['all_tuples']
        selected_resources = []
        for resource in resource_type:
            if st.checkbox(resource, key=resource):
                selected_resources.append(resource)
    
    since = st.date_input("Start date", value="2024-01-01", format="YYYY-MM-DD")
    until = st.date_input("End date", value="2024-12-31", format="YYYY-MM-DD")


    if st.button("Submit Estimation", type="primary"):
        if not api_key:
            st.error("Please enter an API key.")
        elif not selected_resources:
            st.error("Please select at least one resource type.")
        else:
            #TODO to be replace later on
            AOI = {
                "coordinates": [
                    [
                    [
                        144.96005958283428,
                        -37.81180103987199
                    ],
                    [
                        144.96005958283428,
                        -37.81327791021184
                    ],
                    [
                        144.9627625779271,
                        -37.81327791021184
                    ],
                    [
                        144.9627625779271,
                        -37.81180103987199
                    ],
                    [
                        144.96005958283428,
                        -37.81180103987199
                    ]
                    ]
                ],
                "type": "Polygon"
            }
            helper = NearMapHelper(api_key, str(since), str(until), ', '.join(selected_resources))
            response = helper.get_transaction_content(AOI)
            cost = helper.get_cost_estimate(response)
            st.session_state['cost'] = cost


    # Text Area for Query Results
    if ('cost' in st.session_state):
        st.subheader("Estimation Results")
        st.metric(label='Cost', value=f"{st.session_state['cost']}")


with right:
    st.write("second secion")
