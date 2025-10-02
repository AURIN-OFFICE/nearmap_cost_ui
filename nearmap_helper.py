# Nearmap API Helper Module
# This module provides functionality for interacting with the Nearmap API
# and managing cost estimation for Nearmap data requests.

import requests


class NearMapHelper:
    """
    Helper class for interacting with the Nearmap API.
    
    This class provides methods to:
    - Retrieve available resource types and their costs
    - Make API requests to get transaction content
    - Calculate cost estimates
    - Check remaining API credits
    """
    
    @staticmethod
    def get_all_resources():
        """
        Returns a comprehensive dictionary of all available Nearmap resource types and their costs.
        
        Returns:
            dict: A dictionary containing:
                - namespaces: List of available resource namespaces
                - resources: Dictionary mapping namespaces to their available resources
                - all_tuples: Dictionary mapping resource combinations to their cost information
        """
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
        """
        Initialize the NearMapHelper with API credentials and query parameters.
        
        Args:
            API_KEY (str): The Nearmap API key for authentication
            since (str): Start date for the query in YYYY-MM-DD format
            until (str): End date for the query in YYYY-MM-DD format
            resources (str): Comma-separated string of selected resource types
            dates_single (str): Either "single" for latest capture only or "all" for all captures
        """
        self.API_KEY = API_KEY  # Nearmap API key for authentication
        self.since = since  # Start date for the query
        self.until = until  # End date for the query
        self.resources = resources  # Selected resource types
        self.dates_single = dates_single  # Capture date preference
        
    def get_data(self, url, headers):
        """
        Make a GET request to the specified URL with the given headers.
        
        Args:
            url (str): The URL to make the GET request to
            headers (dict): HTTP headers to include in the request
            
        Returns:
            dict: JSON response from the API
            
        Raises:
            Exception: If the request fails, returns empty response, or JSON parsing fails
        """
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
        """
        Make a POST request to the specified URL with the given payload and headers.
        
        Args:
            url (str): The URL to make the POST request to
            payload (dict): JSON payload to send in the request body
            headers (dict): HTTP headers to include in the request
            
        Returns:
            dict: JSON response from the API
            
        Raises:
            Exception: If the request fails, returns empty response, or JSON parsing fails
        """
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
        """
        Get transaction content and cost estimate for a given Area of Interest (AOI).
        
        Args:
            AOI (dict): GeoJSON geometry representing the Area of Interest
            
        Returns:
            dict: API response containing cost information and survey data
        """
        url = f"https://api.nearmap.com/coverage/v2/tx/aoi?apikey={self.API_KEY}"
        payload = {
            "preview": "true",  
            "aiOn3dCoverage": "false",  # AI on 3D coverage
            "resources": self.resources,  # Selected resource types
            "dates": self.dates_single,  # Date preference (single/all)
            "since": self.since,  # Start date
            "until": self.until,  # End date
            "overlap": "all",  # Include all overlapping data
            "aoi": AOI  # Area of Interest geometry
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }   
        return self.post_data(url, payload, headers)
    
    @staticmethod
    def get_cost_estimate(response):
        """
        Extract the cost estimate from the API response.
        
        Args:
            response (dict): API response containing cost information
            
        Returns:
            float: The estimated cost in credits
        """
        return response["costOfTransaction"]
    
    @staticmethod
    def get_surveys(response):
        """
        Extract survey information from the API response.
        
        Args:
            response (dict): API response containing survey data
            
        Returns:
            list: List of available surveys
        """
        return response["surveys"]
    
    def get_remaining_credits(self):
        """
        Get the remaining API credits for the authenticated user.
        
        Returns:
            dict: API response containing remaining credit information
        """
        url = "https://api.betterview.net/api/properties/quota"
        headers = {"accept": "application/json", "authorization": f"Bearer {self.API_KEY}"}
        return self.get_data(url, headers)
