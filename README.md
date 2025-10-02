# Nearmap Cost Estimation UI

A Streamlit-based web application for estimating costs of Nearmap API requests based on area coverage and selected resource types.

## How to use the tool?

1. **Interactive Map Interface**: Draw or upload GeoJSON areas of interest
2. **Resource Selection**: Choose from various Nearmap data types (raster, AI packs, etc.)
3. **Date Range Selection**: Choose between single capture or all available captures
4. **Cost Estimation**: Real-time cost calculation based on selected resources and area
5. **Cost Table Integration**: Built-in cost table for reference

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

## File Structure

```
nearmap_cost_ui/
├── main.py              # Main Streamlit application
├── map_helper.py         # Map drawing utilities
├── cost_table.json      # Cost table data
├── logos/               # Application logos
├── requirements.txt     # Python dependencies
└── README.md           # This file
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support
For issues or questions, please send a support email to masoud.rahimi@unimelb.edu.au.
