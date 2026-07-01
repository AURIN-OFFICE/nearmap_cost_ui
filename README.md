# Nearmap Cost Estimation UI

A Streamlit-based web application for estimating costs of Nearmap API requests based on area coverage and selected resource types. This tool helps users understand the credit costs associated with their Nearmap data requests before making API calls.

## Overview

The Nearmap Cost Estimation UI provides an intuitive interface for:
- **Interactive area selection** on maps
- **Resource type selection** from Nearmap's available data types
- **Automatic area calculation** in square meters
- **Real-time cost estimation** based on selected resources and area size
- **Cost table reference** for understanding credit requirements

## (NEW) Two cost estimates: `by_area` (legacy) + `by_api_return` (API)

**Why:** the original estimate (`by_area`) computes cost locally as `rate × area`. It's a
good approximation, but it can't see Nearmap's actual billing, so it **over-estimates**
AOIs that include ocean/uncovered land and **invents a price for packs your subscription can't
order** (the API rejects them). So the app now also computes **`by_api_return`**: it tiles the
AOI and sums the real `preview=true` cost from Nearmap's Coverage API (the validated method
from the sibling `nearmap` repo), which is the number Nearmap actually bills — so it's exact,
always reflects current pricing (no hardcoded rate table to keep in sync), works at any AOI
size, and reports how much of your area actually has coverage.

**What's done:** a self-contained [`api_cost_estimation/`](api_cost_estimation/) module
(tiling + per-tile preview, ported GDAL-free — **no new runtime dependencies**) plus an
offline + live validation harness. The UI now shows **both figures side by side**; `by_area`
is kept unchanged as a sanity check, with `by_api_return` as the trusted figure. All preview
calls are free.

**Test result:** offline suite **74 passed / 6 skipped**, and live API checks (preview-only, $0)
confirm it — 0% price drift, both pricing bundles hold, and entitlements are enforced (all 25
AI packs are valid, priced identifiers on the test key; the separate `aiImpactAssessment:postcat`
returns 403 not permitted). The payoff: **`by_api_return` is the *actual billed cost*.**
On covered AOIs with packs you own it matches `by_area` to ~0.1% (just per-tile rounding), but
it's the figure to trust because it's right where `by_area` quietly isn't — it won't
**over-charge AOIs touching ocean/uncovered land (up to +33%)** or **quote packs your
subscription can't order**, both common in real use (most AU study areas are coastal; pack
access varies by plan).

See [`api_cost_estimation/README.md`](api_cost_estimation/README.md) (design & why) and
[`tests/REPORT.md`](tests/REPORT.md)
(evidence & numbers) for details.

**Tooling (uv vs Docker):** Docker runs the deployed app from `requirements.txt` only (no
new deps were added). `uv` (`pyproject.toml` + `uv.lock`) is the local dev/test environment
— used to run the validation harness and iterate locally. The estimator code runs in both;
the validation scripts only ever run under `uv`.

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
**25 AI packs** are available. Each costs 5 credits for a single survey (7.5 for all
surveys); beyond 7 packs the price is capped at the all-packs bundle. The API resource
identifier (used in requests) is shown in `code`.

| AI Pack | Resource ID | | AI Pack | Resource ID |
|---|---|---|---|---|
| Building Footprints | `aiPacks:building` | | Roof Objects | `aiPacks:roof_objects` |
| Building Characteristics | `aiPacks:building_char` | | Commercial Roof Objects | `aiPacks:commercial_roof_objects` |
| Building Structures | `aiPacks:building_structures` | | Roof Overhang | `aiPacks:roof_overhang` |
| Construction | `aiPacks:construction` | | Solar Panels | `aiPacks:solar` |
| Debris | `aiPacks:debris` | | Swimming Pool | `aiPacks:pool` |
| Roof Characteristics | `aiPacks:roof_char` | | Trampoline | `aiPacks:trampoline` |
| Roof Condition | `aiPacks:roof_cond` | | Yard Objects | `aiPacks:yard_objects` |
| Advanced Roof Condition | `aiPacks:advanced_roof_cond` | | Surfaces | `aiPacks:surfaces` |
| Roof Shape | `aiPacks:roof_shape` | | Surface Permeability | `aiPacks:surface_permeability` |
| Roof Materials | `aiPacks:roof_materials` | | Pavement Markings | `aiPacks:pavement_marking` |
| Pavement Condition | `aiPacks:pavement_cond` | | Poles | `aiPacks:poles` |
| Utilities | `aiPacks:utilities` | | Vegetation | `aiPacks:vegetation` |
| Experimental | `aiPacks:experimental` | | | |

Post-catastrophe / damage assessment is a **separate** product — `aiImpactAssessment:postcat`
(35 credits) — not one of the AI packs, and it needs its own subscription entitlement.

> **Identifiers are irregular and were verified against the live coverage API** (the API
> returns `UNKNOWN_PACK` for the "obvious" spelling), so don't normalise them: `pavement_cond`
> (not `pavement_condition`), `roof_materials` (plural) but `roof_shape` (singular), and
> `advanced_roof_cond` (not `roof_cond_advanced`).

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

### Option 1: Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd nearmap_cost_ui
```

2. Build and run with Docker Compose:
```bash
docker-compose up --build
```

3. Access the application at `http://localhost:8501`

### Option 2: Local Python Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nearmap_cost_ui
```

2. Install dependencies.

   **Recommended — [uv](https://github.com/astral-sh/uv)** (matches the sibling `nearmap` repo; reads `pyproject.toml` + `uv.lock`):
   ```bash
   uv sync
   ```
   This creates a `.venv` with the pinned runtime + dev (pytest) dependencies.

   Or with plain pip + venv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Usage

### Docker Usage

1. Run the application with Docker Compose:
```bash
docker-compose up --build
```

2. Access the application at `http://localhost:8501`

3. Use the application:
   - Enter your Nearmap API key
   - Select resource types you want to estimate
   - Choose date range and capture type
   - Either draw a rectangle on the map or upload a GeoJSON file
   - Click "Submit Estimation" to get cost estimates

### Local Python Usage

1. Run the application:
```bash
uv run streamlit run main.py    # or, with an activated venv: streamlit run main.py
```

2. Open your browser and navigate to the provided local URL (typically `http://localhost:8501`)

3. Use the application:
   - Enter your Nearmap API key
   - Select resource types you want to estimate
   - Choose date range and capture type
   - Either draw a rectangle on the map or upload a GeoJSON file
   - Click "Submit Estimation" to get cost estimates

## Docker Deployment

### Quick Start

The easiest way to run the application is using the provided build scripts:

#### Linux/macOS:
```bash
# Clone the repository
git clone <repository-url>
cd nearmap_cost_ui

# Make the build script executable
chmod +x build.sh

# Build and run the application
./build.sh run

# Or start in background
./build.sh start

# Access the application at http://localhost:8501
```

#### Windows:
```cmd
# Clone the repository
git clone <repository-url>
cd nearmap_cost_ui

# Build and run the application
build.bat run

# Or start in background
build.bat start

# Access the application at http://localhost:8501
```

#### Manual Docker Compose:
```bash
# Clone the repository
git clone <repository-url>
cd nearmap_cost_ui

# Build and run the application
docker-compose up --build

# Access the application at http://localhost:8501
```

### Docker Commands

#### Build the Docker image:
```bash
docker build -t nearmap-cost-ui .
```

#### Run the container:
```bash
docker run -p 8501:8501 nearmap-cost-ui
```

#### Run with Docker Compose:
```bash
# Start the application
docker-compose up

# Start in background
docker-compose up -d

# Stop the application
docker-compose down

# Rebuild and start
docker-compose up --build
```

### Build Scripts

The repository includes convenient build scripts for easy deployment:

- **`build.sh`** (Linux/macOS): Bash script with colored output and error handling
- **`build.bat`** (Windows): Batch script for Windows environments

#### Available Commands:
- `build` - Build the Docker image
- `run` - Run the application with Docker Compose
- `start` - Start the application in background
- `stop` - Stop the application
- `logs` - Show application logs
- `clean` - Clean up Docker resources
- `help` - Show help message

### Docker Configuration

The application includes several Docker configuration files:

- **`Dockerfile`**: Multi-stage build with Python 3.11, system dependencies, and security best practices
- **`docker-compose.yml`**: Service definition with port mapping, environment variables, and health checks
- **`.dockerignore`**: Excludes unnecessary files from the Docker build context
- **`entrypoint.sh`**: Custom startup script with health checks and error handling

### Environment Variables

You can customize the application behavior using environment variables:

```bash
# Streamlit configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### Production Deployment

For production deployment, consider:

1. **Using a reverse proxy** (nginx, Apache) for SSL termination
2. **Setting up monitoring** and logging
3. **Using environment variables** for configuration
4. **Implementing proper secrets management**

Example production docker-compose.yml:
```yaml
version: '3.8'
services:
  nearmap-cost-ui:
    build: .
    ports:
      - "8501:8501"
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

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
├── main.py                # Main Streamlit application
├── map_helper.py          # Map drawing utilities and GeoJSON handling
├── nearmap_helper.py      # Nearmap API helper + resource/rate table
├── cost_table.json        # Cost table data with credit requirements
├── api_cost_estimation/       # Dual cost estimators + validation harness
│   ├── coverage_fetcher.py  # GDAL-free port of ../nearmap tiling + preview
│   ├── by_area.py           # original manual estimator (preserved as-is)
│   ├── estimators.py        # estimate_cost / count_tiles — UI entry points
│   ├── data/                # test AOIs + cached credit plans (from ../nearmap)
│   └── validation/          # offline pytest + REPORT.md + live script
├── pyproject.toml         # Project metadata + dependencies (uv source of truth)
├── uv.lock                # Pinned dependency lockfile (uv)
├── requirements.txt       # Runtime deps (used by Docker / Streamlit Cloud)
├── requirements-dev.txt   # Dev deps (pytest) for pip users
└── README.md              # This documentation file
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
25 AI packs across buildings, roofs, surfaces, pavement, vegetation, amenities and
infrastructure — see the full pack ↔ resource-ID table under
[Supported Resource Types → AI Packs](#ai-packs-artificial-intelligence-analysis).

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
# Install runtime + dev (pytest) dependencies with uv
uv sync

# Run in development mode
uv run streamlit run main.py --server.runOnSave true

# Run the offline validation suite (no API key, no cost)
uv run pytest tests/ -v
```

With plain pip instead of uv:
```bash
pip install -r requirements-dev.txt   # runtime + pytest
streamlit run main.py --server.runOnSave true
pytest tests/ -v
```

## Support
For issues or questions, please send a support email to masoud.rahimi@unimelb.edu.au.

## License
This project is developed for research and educational purposes. Please ensure compliance with Nearmap's terms of service when using their API.
