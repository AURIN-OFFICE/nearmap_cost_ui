# Nearmap Cost Estimation UI

A Streamlit-based web application for estimating costs of Nearmap API requests based on area coverage and selected resource types. This tool helps users understand the credit costs associated with their Nearmap data requests before making API calls.

## Overview

The Nearmap Cost Estimation UI provides an intuitive interface for:
- **Interactive area selection** on maps
- **Resource type selection** from Nearmap's available data types
- **Automatic area calculation** in square meters
- **Real-time cost estimation** based on selected resources and area size
- **Cost table reference** for understanding credit requirements

## How to use the tool?

### Step 1: Setup
1. **Enter API Key**: Input your Nearmap API key in the designated field
2. **Select Resources**: Choose the data types you need from the available options

### Step 2: Define Area of Interest
You have two options:
- **Draw on Map**: Use the interactive map to draw a rectangle around your area of interest
- **Upload GeoJSON**: Upload a pre-defined GeoJSON file with your area boundaries

### Step 3: Configure Parameters
- **Date Range**: Set your start and end dates for data capture
- **Capture Type**: Choose between "Latest capture only" or "All available captures"

### Step 4: Get Cost Estimate
- Click "Submit Estimation" to calculate the cost
- View the estimated credits required for your request
- Use "See Cost Table" to reference detailed pricing information

## Key Features

### Interactive Map Interface
- **Draw Tool**: Click and drag to create rectangular areas of interest
- **GeoJSON Support**: Upload existing GeoJSON files for complex boundaries
- **Area Display**: Automatic calculation and display of area in square meters
- **Visual Feedback**: Real-time map updates as you draw or upload areas

### Resource Selection
Choose from comprehensive Nearmap data types:

#### Raster Data
- **Vertical Imagery**: Standard aerial photography
- **Panorama Views**: North, South, East, West directional views
- **True Ortho**: Orthorectified imagery
- **DEM/DTM**: Digital Elevation Models and Digital Terrain Models
- **DSM**: Digital Surface Models

#### AI Packs (Artificial Intelligence Analysis)
- **Building Detection**: Identify and classify buildings
- **Construction Monitoring**: Track construction progress
- **Debris Detection**: Identify debris and waste materials
- **Pavement Marking**: Detect road markings and signage
- **Pool Detection**: Identify swimming pools and water features
- **Roof Analysis**: Assess roof characteristics and conditions
- **Solar Panel Detection**: Identify solar installations
- **Surface Analysis**: Classify surface types and permeability
- **Vegetation Mapping**: Analyze vegetation coverage and health

### Cost Calculation
The application calculates costs based on:
- **Area Size**: Larger areas require more credits
- **Resource Types**: Different data types have different credit costs
- **Capture Frequency**: Single capture vs. all available captures
- **Built-in Pricing**: Uses official Nearmap credit pricing tables

### Date Range Selection
- **Single Capture**: Get the most recent data capture (lower cost)
- **All Captures**: Access all available historical data (higher cost)
- **Custom Date Ranges**: Specify exact start and end dates for your analysis

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nearmap_cost_ui
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
streamlit run main.py
```

2. Open your browser and navigate to the provided local URL (typically `http://localhost:8501`)

3. Use the application:
   - Enter your Nearmap API key
   - Select resource types you want to estimate
   - Choose date range and capture type
   - Either draw a rectangle on the map or upload a GeoJSON file
   - Click "Submit Estimation" to get cost estimates

## API Key

You'll need a valid Nearmap API key to use the cost estimation features. The application will prompt you to enter this key.

## Technical Details

### Architecture
The application is built using:
- **Frontend**: Streamlit for the web interface
- **Mapping**: Folium for interactive maps with drawing capabilities
- **Geometry**: Shapely for area calculations and geometric operations
- **Projections**: PyProj for coordinate system transformations
- **Data Processing**: Pandas for data manipulation

### Area Calculation
- Uses **Albers Equal Area** projection for accurate area calculations
- Automatically projects coordinates based on the centroid of the area of interest
- Returns area in square meters for consistent measurement

### Cost Calculation Logic
1. **Resource Mapping**: Each selected resource is mapped to its corresponding cost table entry
2. **Area Scaling**: Costs are calculated per 1000 square meters
3. **AI Pack Limitation**: Maximum of 7 AI packs can be selected (cost optimization)
4. **Capture Type**: Different pricing for single capture vs. all captures

## File Structure

```
nearmap_cost_ui/
├── main.py              # Main Streamlit application
├── map_helper.py        # Map drawing utilities and GeoJSON handling
├── cost_table.json      # Cost table data with credit requirements
├── logos/               # Application logos (AURIN and Nearmap)
│   ├── aurin-logo-400-D0zkc36m.png
│   └── Nearmap-logo.png
├── requirements.txt     # Python dependencies
└── README.md           # This documentation file
```

## Dependencies

- **streamlit**: Web application framework
- **requests**: HTTP requests for API calls
- **pandas**: Data manipulation
- **folium**: Interactive maps
- **streamlit-folium**: Streamlit integration for Folium
- **shapely**: Geometric operations
- **pyproj**: Coordinate system transformations

## Cost Calculation

The application calculates costs based on:
- Selected resource types (raster data, AI packs, etc.)
- Area of interest (calculated in square meters)
- Date range selection (single capture vs. all captures)
- Built-in cost table with credit requirements per resource type

## Supported Resource Types

### Raster Data
- Vertical imagery
- Panorama (North, South, East, West)
- True Ortho
- DEM/DTM
- DSM

### AI Packs
- Building detection
- Construction monitoring
- Debris detection
- Pavement marking
- Pool detection
- Roof analysis
- Solar panel detection
- Surface analysis
- Vegetation mapping
- And more...

## Troubleshooting

### Common Issues

#### "Please enter an API key" Error
- **Solution**: Ensure you have a valid Nearmap API key and enter it in the designated field
- **Note**: API keys are case-sensitive and should not include extra spaces

#### "Please select at least one resource type" Error
- **Solution**: Check at least one resource type from the available options
- **Tip**: Start with basic raster data before adding AI packs

#### "Either upload a geojson or select the extent on the map" Error
- **Solution**: Either draw a rectangle on the map or upload a valid GeoJSON file
- **Note**: The area must be defined before cost estimation

#### Area Calculation Issues
- **Problem**: Area shows as 0 or incorrect values
- **Solution**: Ensure your GeoJSON has valid geometry and proper coordinate system
- **Tip**: Use WGS84 (EPSG:4326) coordinates for best results

#### High Cost Estimates
- **Explanation**: Costs are calculated per 1000 square meters
- **Optimization**: Consider reducing area size or selecting fewer resource types
- **AI Packs**: Limit to 7 or fewer AI packs for cost efficiency

### Performance Tips

1. **Area Size**: Smaller areas (< 1 km²) provide faster estimates
2. **Resource Selection**: Start with essential resources, add more as needed
3. **Date Range**: Single capture is more cost-effective than all captures
4. **Browser**: Use modern browsers (Chrome, Firefox, Safari) for best performance

## FAQ

### Q: What is the maximum area I can estimate?
A: There's no hard limit, but larger areas will result in higher credit costs. Consider breaking very large areas into smaller segments.

### Q: Why are AI packs limited to 7 selections?
A: This is a cost optimization feature. Selecting more than 7 AI packs doesn't provide additional value due to pricing structure.

### Q: Can I use this tool without a Nearmap API key?
A: You can explore the interface and see cost estimates, but you'll need a valid API key for actual data requests.

### Q: What coordinate systems are supported?
A: The tool works best with WGS84 (EPSG:4326) coordinates, but can handle most standard coordinate systems.

### Q: How accurate are the cost estimates?
A: Estimates are based on official Nearmap pricing tables and should be accurate within the current pricing structure.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
streamlit run main.py --server.runOnSave true
```

## Support
For issues or questions, please send a support email to masoud.rahimi@unimelb.edu.au.

## License
This project is developed for research and educational purposes. Please ensure compliance with Nearmap's terms of service when using their API.
