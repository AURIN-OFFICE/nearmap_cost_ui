import streamlit as st
import requests

# Configure the Streamlit Page
st.set_page_config(
    page_title="Nearmap Cost Estimator", 
    page_icon=":money:", 
    layout="wide"
    )
  
class NearMapHelper:
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

# Main body
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

API_KEY = st.secrets["API_KEY"]
since = "2024-01-01"
until = "2024-12-31"
resources = "raster:Vert,raster:TrueOrtho,aiPacks:roof_objects"
helper = NearMapHelper(API_KEY, since, until, resources)
response = helper.get_transaction_content(AOI)
st.write(helper.get_cost_estimate(response))
