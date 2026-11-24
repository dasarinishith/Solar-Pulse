-- SolarPulse Enterprise Supabase Migration
-- Schema for Multi-Plant Solar Asset Operations & Intelligence

-- 1. Plants table
CREATE TABLE IF NOT EXISTS plants (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(32) UNIQUE NOT NULL,
    plant_name VARCHAR(128) NOT NULL,
    capacity_mw FLOAT NOT NULL,
    location VARCHAR(128),
    commission_date TIMESTAMP WITHOUT TIME ZONE,
    grid_connection_type VARCHAR(64) DEFAULT 'Utility Scale Grid Tied',
    default_tariff_inr FLOAT DEFAULT 3.20,
    inverter_count INTEGER DEFAULT 4,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- 2. Generation Records table (Supports SIMULATED, UPLOADED, API_LIVE)
CREATE TABLE IF NOT EXISTS generation_records (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(32) NOT NULL REFERENCES plants (plant_id) ON DELETE CASCADE,
    inverter_id VARCHAR(32) DEFAULT 'CENTRAL' NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    actual_generation_kwh FLOAT NOT NULL,
    expected_generation_kwh FLOAT NOT NULL,
    power_kw FLOAT,
    dc_power_kw FLOAT,
    ac_voltage_v FLOAT,
    dc_voltage_v FLOAT,
    current_a FLOAT,
    temperature_c FLOAT,
    module_temperature_c FLOAT,
    irradiance_wm2 FLOAT,
    rainfall_mm FLOAT DEFAULT 0.0,
    inverter_status VARCHAR(32) DEFAULT 'Normal',
    comm_status VARCHAR(32) DEFAULT 'ONLINE',
    grid_export_kwh FLOAT DEFAULT 0.0,
    self_consumption_kwh FLOAT DEFAULT 0.0,
    curtailed_energy_kwh FLOAT DEFAULT 0.0,
    tariff_inr_per_kwh FLOAT DEFAULT 3.20,
    soiling_ratio FLOAT DEFAULT 1.0,
    is_interval_15m BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(32) DEFAULT 'SIMULATED',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_plant_inv_timestamp_source UNIQUE (plant_id, inverter_id, timestamp, data_source)
);

-- Index for high-performance time-series queries
CREATE INDEX IF NOT EXISTS idx_gen_plant_source_ts ON generation_records (plant_id, data_source, timestamp);
CREATE INDEX IF NOT EXISTS idx_gen_source_interval ON generation_records (data_source, is_interval_15m);

-- 3. Inverter Gateways table
CREATE TABLE IF NOT EXISTS inverter_gateways (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(64) NOT NULL,
    plant_id VARCHAR(32) NOT NULL REFERENCES plants (plant_id) ON DELETE CASCADE,
    site_id VARCHAR(128) NOT NULL,
    api_key VARCHAR(256),
    api_secret VARCHAR(256),
    base_url VARCHAR(256),
    polling_interval_min INTEGER DEFAULT 15,
    status VARCHAR(32) DEFAULT 'NOT_CONFIGURED',
    last_polled TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_gw_mfg_plant_site UNIQUE (manufacturer, plant_id, site_id)
);

-- 4. Tariff Configurations table
CREATE TABLE IF NOT EXISTS tariff_configs (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(32) NOT NULL REFERENCES plants (plant_id) ON DELETE CASCADE,
    category VARCHAR(64) NOT NULL,
    tariff_inr FLOAT NOT NULL,
    effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITHOUT TIME ZONE,
    notes VARCHAR(256)
);

-- 5. Alert Records table
CREATE TABLE IF NOT EXISTS alert_records (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(32) NOT NULL REFERENCES plants (plant_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    severity VARCHAR(32) NOT NULL,
    category VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    deviation_percent FLOAT,
    status VARCHAR(32) DEFAULT 'ACTIVE',
    resolved_at TIMESTAMP WITHOUT TIME ZONE
);

-- 6. Maintenance Records table
CREATE TABLE IF NOT EXISTS maintenance_records (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(32) NOT NULL REFERENCES plants (plant_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    equipment_type VARCHAR(64) NOT NULL,
    action_taken VARCHAR(256) NOT NULL,
    cost_inr FLOAT,
    technician VARCHAR(128),
    notes TEXT
);

-- 7. Dataset Uploads Tracking table
CREATE TABLE IF NOT EXISTS dataset_uploads (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(256) NOT NULL,
    upload_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    record_count INTEGER,
    status VARCHAR(32),
    summary TEXT,
    import_mode VARCHAR(32)
);
