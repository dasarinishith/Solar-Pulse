# SolarPulse (⚡)
### AI-Powered Solar Energy Analytics & Revenue Intelligence Platform

SolarPulse is a production-grade, enterprise renewable energy SaaS platform built for Independent Power Producers (IPPs), solar asset managers, and operations & maintenance (O&M) teams. It enables renewable energy enterprises to monitor utility-scale solar plant performance, analyse electricity generation, detect root causes of energy shortfalls, forecast future yield, and quantify financial revenue impacts.

---

## 🌟 Key Capabilities & Architecture

| Module | Identifier | Purpose & Core Features |
| :--- | :--- | :--- |
| **Executive Overview** | `Module A` | Portfolio-level KPIs (Yield, Efficiency, Revenue, Shortfalls), top/underperforming assets, environmental impact ($tCO_2e$, trees). |
| **Solar Performance** | `Module B` | IEC 61724 yield analytics, Performance Ratio (PR %), Capacity Utilization Factor (CUF %), daily/weekly/monthly/annual trends. |
| **Loss Detection** | `Module C` | Deviation thresholding, shortfall quantification, diagnostic root cause categorization (Weather, Soiling, Inverter, Grid). |
| **Revenue Intelligence** | `Module D` | Multi-tier PPA tariffs, grid feed-in vs captive self-consumption, shortfall valuation, tariff sensitivity models, 96.5% collection projections. |
| **CleanSense** | `Module E` | Panel soiling ratio tracking, natural rain wash detection, cleaning priority matrix, and payback turnaround calculator. |
| **PredictCare** | `Module F` | Inverter telemetry diagnostics, thermal derating, string degradation, and Scikit-learn **Isolation Forest** anomaly detection. |
| **SolarCast** | `Module G` | Dual-engine day-ahead and 14-day forecasting: Baseline Statistical (7-day MA) + Random Forest ML with 95% confidence intervals (MAE, RMSE, MAPE, $R^2$). |
| **GridWatch** | `Module H` | Grid export reliability, DISCOM backdown/curtailment logs, uncompensated transmission loss monetization under PPA clauses. |
| **Data Management** | `Ingestion` | Flexible CSV/Excel uploader, fuzzy column synonym mapper, duplicate detection, missing value imputation, and SQLite persistence. |
| **API Connectors** | `Gateway` | Simulated real-time SCADA telemetry streamer + extensible REST interfaces for SolarEdge, SMA Sunny Portal, Fronius, and Sungrow. |
| **Report Center** | `Dossier` | Instant downloadable executive PDF reports (via ReportLab) and curated granular CSV exports. |

---

## 📐 Mathematical & Financial Formulations

All calculations in SolarPulse are strictly zero-division safe, physically bounded, and compliant with renewable industry standards:

1. **Generation Efficiency (%)**:
   $$\text{Efficiency} = \left(\frac{\text{Actual Generation (kWh)}}{\text{Expected Generation (kWh)}}\right) \times 100$$
2. **Generation Shortfall (kWh)**:
   $$\text{Shortfall} = \max(\text{Expected Generation} - \text{Actual Generation}, 0)$$
3. **Capacity Utilization Factor (CUF %)**:
   $$\text{CUF} = \left(\frac{\text{Actual Generation (kWh)}}{\text{Installed Capacity (kW)} \times \text{Hours (24)}}\right) \times 100$$
4. **Performance Ratio (PR %) [IEC 61724]**:
   $$\text{PR} = \left(\frac{\text{Actual Yield (kWh/kWp)}}{\text{Reference Yield (GHI } W/m^2 / 1000)}\right) \times 100$$
5. **Multi-Tier Revenue Monetization**:
   $$\text{Total Revenue} = (\text{Grid Export kWh} \times \text{PPA Tariff}) + (\text{Self-Consumption kWh} \times \text{Captive Tariff})$$
6. **Carbon Avoidance**:
   $$\text{Emissions Avoided (tCO}_2e) = \frac{\text{Generation (kWh)} \times 0.82 \text{ kg CO}_2/\text{kWh}}{1000}$$

---

## 🛠️ Technology Stack

- **Frontend & App Framework**: [Streamlit](https://streamlit.io/) with custom CSS enterprise theme (dark charcoal & deep emerald aesthetic).
- **Visualisations**: [Plotly](https://plotly.com/python/) interactive charts with custom high-contrast palettes and unified hover states.
- **Backend & Analytics**: Python 3.12, [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/).
- **Machine Learning**: [Scikit-learn](https://scikit-learn.org/) (Isolation Forest for anomaly detection, Random Forest Regressor for time-series forecasting).
- **Database & Persistence**: SQLite with [SQLAlchemy](https://www.sqlalchemy.org/) ORM.
- **Reporting**: [ReportLab](https://www.reportlab.com/) for publication-quality C-suite executive PDF generation.
- **Testing**: [pytest](https://pytest.org/) automated test suite (16 test cases).

---

## 🚀 Installation & Setup (macOS / Apple Silicon M4)

### 1. Prerequisites
- macOS (Compatible with Apple Silicon M1/M2/M3/M4 & Intel)
- Python 3.12 (via Homebrew: `brew install python@3.12 uv`)

### 2. Environment Setup
```bash
# Clone or navigate to the repository
cd "/Users/nitish/solar pulse/Solar-Pulse"

# Create a virtual environment using Python 3.12
uv venv .venv --python /opt/homebrew/bin/python3.12

# Activate virtual environment
source .venv/bin/activate

# Install all dependencies
uv pip install -r requirements.txt
```

### 3. Generate Simulated Dataset & Seed Database
SolarPulse comes with a pre-configured multi-plant synthetic dataset generator covering 4 utility-scale solar parks across 12 months (1,460 records):
- **SP-01**: Pavagada Solar Park (50 MW, Karnataka)
- **SP-02**: Bhadla Solar Park (75 MW, Rajasthan)
- **SP-03**: Rewa Ultra Mega Solar (40 MW, Madhya Pradesh)
- **SP-04**: Charanka Solar Park (30 MW, Gujarat)

```bash
# Generate sample CSV and seed SQLite
python data/generate_sample_data.py
```

### 4. Run the Application
```bash
# Launch Streamlit server
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## 🧪 Running Unit Tests

Execute the automated test suite covering edge cases (zero generation, null values, division-by-zero, multi-tier tariffs, anomaly classification, and forecasting intervals):

```bash
PYTHONPATH=. .venv/bin/pytest -v tests/
```

Expected result:
```
======================== 16 passed in 0.82s ========================
```

---

## 📂 Project Directory Structure

```
Solar-Pulse/
├── app.py                      # Main application entrypoint and module router
├── requirements.txt            # Python dependencies
├── README.md                   # Enterprise documentation & setup guide
├── .gitignore                  # Git exclusions (.venv, databases, cache)
├── solarpulse.db               # SQLite database (auto-generated)
│
├── pages/                      # Multi-page application modules
│   ├── 1_Overview.py           # Module A: Executive Dashboard
│   ├── 2_Performance.py        # Module B: Generation Analytics & CUF/PR
│   ├── 3_Loss_Detection.py     # Module C: Loss Identification & Root Cause Analysis
│   ├── 4_Revenue_Intelligence.py # Module D: Financial Engine & Sensitivity
│   ├── 5_CleanSense.py         # Module E: Soiling & Cleaning Prioritization
│   ├── 6_PredictCare.py        # Module F: Predictive Inverter Maintenance
│   ├── 7_SolarCast.py          # Module G: ML Generation Forecasting
│   ├── 8_GridWatch.py          # Module H: Grid Export & Curtailment Tracking
│   ├── 9_Data_Management.py    # Data Upload Center & Flexible Schema Mapper
│   ├── 10_API_Connectors.py    # Live SCADA Telemetry & Inverter Gateway
│   └── 11_Reports.py           # Executive PDF & CSV Export Center
│
├── core/                       # Core analytical & business logic
│   ├── __init__.py
│   ├── calculations.py         # Physics, efficiency, shortfall, CUF, PR formulas
│   ├── revenue_engine.py       # Multi-tier tariffs, revenue shortfall, collection rates
│   ├── validation.py           # Column synonym dictionary, cleaning & imputation
│   ├── clean_sense.py          # Soiling index, rainfall washes, cleaning ROI
│   ├── anomaly_detection.py    # Physical rules & Isolation Forest model
│   ├── forecasting.py          # Baseline 7-Day MA & Random Forest ML Forecaster
│   └── api_client.py           # SCADA simulated poller & REST gateway interfaces
│
├── database/                   # Database models & access layer
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy ORM schemas
│   ├── connection.py           # Engine & session management
│   └── operations.py           # Seeding, queries, and bulk ingestion
│
├── components/                 # Reusable UI widgets & visualizers
│   ├── __init__.py
│   ├── sidebar.py              # Filter controls & data status badges
│   ├── kpi_cards.py            # Responsive HTML KPI card renderers
│   ├── charts.py               # Unified Plotly dark theme chart generators
│   └── report_generator.py     # ReportLab executive PDF & CSV builder
│
├── data/                       # Data assets & generator
│   ├── sample_solar_data.csv   # 12-month synthetic multi-plant dataset
│   └── generate_sample_data.py # Physics-based synthetic dataset generator
│
├── assets/                     # Stylesheets and visual assets
│   └── styles.css              # Custom enterprise theme
│
└── tests/                      # Automated unit test suite
    ├── test_calculations.py    # Mathematical & division-by-zero tests
    ├── test_revenue.py         # Financial engine tests
    ├── test_data_validation.py # Schema mapping & cleansing tests
    ├── test_anomaly.py         # Anomaly detection tests
    └── test_forecasting.py     # Forecast & ML interval tests
```

---

## 💼 Demonstration Notes for Renewable Energy Interviews

When presenting SolarPulse as a Data Analyst / Technology demonstration:
1. **Highlight Physics-to-Finance Alignment**: Walk through how technical losses (inverter clipping, module soiling, grid curtailment) directly map to monetary shortfall lines in the **Revenue Intelligence** module.
2. **Showcase Enterprise UX**: Contrast the charcoal/deep emerald aesthetic and custom KPI cards against standard default dashboards.
3. **Demonstrate Flexible Data Ingestion**: Open the **Data Management** module and show how non-standard column headers (e.g., `Energy_KWh`, `PlantCode`, `Solar_Radiation`) are automatically standardized.
4. **Demonstrate ReportLab PDF Generation**: Export a PDF from the **Report Center** to showcase real-time investor-ready dossier generation.
5. **Explain Machine Learning with Transparency**: Emphasize that models use prediction intervals and validation metrics ($R^2$, MAPE) rather than black-box claims.
