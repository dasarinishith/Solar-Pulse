"""
SolarPulse Database Operations
Handles database seeding, queries, bulk ingestion, 3-mode data isolation,
15-minute telemetry fetching, and inverter gateway configurations.
"""

import os
import pandas as pd
from datetime import datetime, date
from sqlalchemy import or_, and_, delete
from sqlalchemy.orm import Session as DBSession
from database.connection import get_db_session, init_db
from database.models import (
    Plant, GenerationRecord, TariffConfig, AlertRecord,
    MaintenanceRecord, DatasetUpload, InverterGateway
)

def seed_initial_database_if_empty(csv_path: str = "data/sample_solar_data.csv"):
    """
    Initializes DB schema and seeds plants and simulated generation records if empty.
    """
    init_db()
    session = get_db_session()
    try:
        plant_count = session.query(Plant).count()
        if plant_count == 0:
            initial_plants = [
                Plant(plant_id="SP-01", plant_name="Pavagada Solar Park", capacity_mw=50.0, location="Tumakuru, Karnataka", default_tariff_inr=3.25, inverter_count=4),
                Plant(plant_id="SP-02", plant_name="Bhadla Solar Park", capacity_mw=75.0, location="Phalodi, Rajasthan", default_tariff_inr=2.95, inverter_count=6),
                Plant(plant_id="SP-03", plant_name="Rewa Ultra Mega Solar", capacity_mw=40.0, location="Rewa, Madhya Pradesh", default_tariff_inr=3.40, inverter_count=4),
                Plant(plant_id="SP-04", plant_name="Charanka Solar Park", capacity_mw=30.0, location="Patan, Gujarat", default_tariff_inr=3.15, inverter_count=3),
            ]
            session.add_all(initial_plants)
            session.commit()

            # Add default tariff configs
            for p in initial_plants:
                t1 = TariffConfig(plant_id=p.plant_id, category="Grid Export", tariff_inr=p.default_tariff_inr, effective_from=datetime(2025, 1, 1))
                t2 = TariffConfig(plant_id=p.plant_id, category="Self Consumption", tariff_inr=round(p.default_tariff_inr * 1.35, 2), effective_from=datetime(2025, 1, 1))
                session.add_all([t1, t2])

            # Seed default Gateway records in NOT_CONFIGURED status
            gateways = [
                InverterGateway(manufacturer="SolarEdge", plant_id="SP-01", site_id="SE-SITE-PVG", status="NOT_CONFIGURED"),
                InverterGateway(manufacturer="SMA", plant_id="SP-02", site_id="SMA-BHD-CLUSTER", status="NOT_CONFIGURED"),
                InverterGateway(manufacturer="Fronius", plant_id="SP-03", site_id="FRO-RWA-01", status="NOT_CONFIGURED"),
                InverterGateway(manufacturer="Sungrow", plant_id="SP-04", site_id="SG-CRK-PARK", status="NOT_CONFIGURED"),
                InverterGateway(manufacturer="Huawei", plant_id="SP-01", site_id="HW-FUSION-PVG", status="NOT_CONFIGURED")
            ]
            session.add_all(gateways)
            session.commit()

        # Seed simulated records if not present
        sim_count = session.query(GenerationRecord).filter(GenerationRecord.data_source == "SIMULATED").count()
        if sim_count == 0:
            if not os.path.exists(csv_path):
                from data.generate_sample_data import generate_multi_plant_dataset
                generate_multi_plant_dataset(output_csv=csv_path)

            df = pd.read_csv(csv_path)
            bulk_insert_generation_records(df, source="SIMULATED", mode="REPLACE", session=session)
            print(f"Seeded {len(df)} simulated solar records into SQLite database.")
    finally:
        session.close()

def reset_and_reload_sample_data(csv_path: str = "data/sample_solar_data.csv"):
    """
    Clears all SIMULATED records and regenerates fresh sample data without touching UPLOADED records.
    """
    session = get_db_session()
    try:
        # Delete only SIMULATED generation records
        session.query(GenerationRecord).filter(GenerationRecord.data_source == "SIMULATED").delete()
        session.commit()

        from data.generate_sample_data import generate_multi_plant_dataset
        df = generate_multi_plant_dataset(output_csv=csv_path)
        count = bulk_insert_generation_records(df, source="SIMULATED", mode="APPEND", session=session)
        return count
    finally:
        session.close()

def bulk_insert_generation_records(df: pd.DataFrame, source: str = "UPLOADED", mode: str = "APPEND", session: DBSession = None):
    """
    Bulk inserts records from a DataFrame safely.
    Supports mode='REPLACE' (clears existing records of this source) or 'APPEND'.
    """
    should_close = False
    if session is None:
        session = get_db_session()
        should_close = True

    try:
        if mode == "REPLACE":
            session.query(GenerationRecord).filter(GenerationRecord.data_source == source).delete()
            session.commit()

        # Parse timestamp safely
        df = df.copy()
        df["timestamp_clean"] = pd.to_datetime(df["timestamp"])

        valid_plants = {p.plant_id: p for p in session.query(Plant).all()}
        for p_id in df["plant_id"].unique():
            if p_id not in valid_plants:
                sample_name = df[df["plant_id"] == p_id]["plant_name"].iloc[0] if "plant_name" in df.columns else f"Plant {p_id}"
                new_p = Plant(plant_id=p_id, plant_name=sample_name, capacity_mw=50.0, default_tariff_inr=3.20)
                session.add(new_p)
                session.commit()
                valid_plants[p_id] = new_p

        records_to_insert = []
        for _, row in df.iterrows():
            is_15m = bool(row.get("is_interval_15m", False))
            rec = GenerationRecord(
                plant_id=str(row["plant_id"]),
                inverter_id=str(row.get("inverter_id", "CENTRAL")),
                timestamp=row["timestamp_clean"].to_pydatetime(),
                actual_generation_kwh=float(row.get("actual_generation_kwh", 0.0)),
                expected_generation_kwh=float(row.get("expected_generation_kwh", 0.0)),
                power_kw=float(row["power_kw"]) if pd.notna(row.get("power_kw")) else None,
                dc_power_kw=float(row["dc_power_kw"]) if pd.notna(row.get("dc_power_kw")) else None,
                ac_voltage_v=float(row["ac_voltage_v"]) if pd.notna(row.get("ac_voltage_v")) else None,
                dc_voltage_v=float(row["dc_voltage_v"]) if pd.notna(row.get("dc_voltage_v")) else None,
                current_a=float(row["current_a"]) if pd.notna(row.get("current_a")) else None,
                temperature_c=float(row["temperature_c"]) if pd.notna(row.get("temperature_c")) else None,
                module_temperature_c=float(row["module_temperature_c"]) if pd.notna(row.get("module_temperature_c")) else None,
                irradiance_wm2=float(row["irradiance_wm2"]) if pd.notna(row.get("irradiance_wm2")) else None,
                rainfall_mm=float(row.get("rainfall_mm", 0.0)) if pd.notna(row.get("rainfall_mm")) else 0.0,
                inverter_status=str(row.get("inverter_status", "Normal")),
                comm_status=str(row.get("comm_status", "ONLINE")),
                grid_export_kwh=float(row.get("grid_export_kwh", 0.0)) if pd.notna(row.get("grid_export_kwh")) else 0.0,
                self_consumption_kwh=float(row.get("self_consumption_kwh", 0.0)) if pd.notna(row.get("self_consumption_kwh")) else 0.0,
                curtailed_energy_kwh=float(row.get("curtailed_energy_kwh", 0.0)) if pd.notna(row.get("curtailed_energy_kwh")) else 0.0,
                tariff_inr_per_kwh=float(row.get("tariff_inr_per_kwh", 3.20)) if pd.notna(row.get("tariff_inr_per_kwh")) else 3.20,
                soiling_ratio=float(row.get("soiling_ratio", 1.0)) if pd.notna(row.get("soiling_ratio")) else 1.0,
                is_interval_15m=is_15m,
                data_source=source
            )
            records_to_insert.append(rec)

        session.bulk_save_objects(records_to_insert)
        session.commit()
        return len(records_to_insert)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        if should_close:
            session.close()

def get_all_plants():
    """Returns list of all registered plants as dictionaries."""
    session = get_db_session()
    try:
        plants = session.query(Plant).all()
        return [
            {
                "plant_id": p.plant_id,
                "plant_name": p.plant_name,
                "capacity_mw": p.capacity_mw,
                "location": p.location,
                "default_tariff_inr": p.default_tariff_inr,
                "grid_connection_type": p.grid_connection_type,
                "inverter_count": p.inverter_count
            }
            for p in plants
        ]
    finally:
        session.close()

def get_available_data_sources():
    """Returns dictionary of record counts grouped by data_source."""
    session = get_db_session()
    try:
        sources = {}
        for s in ["SIMULATED", "UPLOADED", "API_LIVE"]:
            cnt = session.query(GenerationRecord).filter(GenerationRecord.data_source == s).count()
            sources[s] = cnt
        return sources
    finally:
        session.close()

def load_generation_dataframe(
    plant_ids=None,
    start_date=None,
    end_date=None,
    data_source="SIMULATED",
    include_15min=False
):
    """
    Loads generation records filtered by plant_id, date range, and strictly by data_source.
    Default loads daily aggregates (is_interval_15m=False).
    """
    session = get_db_session()
    try:
        query = session.query(
            GenerationRecord.plant_id,
            Plant.plant_name,
            Plant.capacity_mw,
            GenerationRecord.inverter_id,
            GenerationRecord.timestamp,
            GenerationRecord.actual_generation_kwh,
            GenerationRecord.expected_generation_kwh,
            GenerationRecord.power_kw,
            GenerationRecord.dc_power_kw,
            GenerationRecord.ac_voltage_v,
            GenerationRecord.dc_voltage_v,
            GenerationRecord.current_a,
            GenerationRecord.temperature_c,
            GenerationRecord.module_temperature_c,
            GenerationRecord.irradiance_wm2,
            GenerationRecord.rainfall_mm,
            GenerationRecord.inverter_status,
            GenerationRecord.comm_status,
            GenerationRecord.grid_export_kwh,
            GenerationRecord.self_consumption_kwh,
            GenerationRecord.curtailed_energy_kwh,
            GenerationRecord.tariff_inr_per_kwh,
            GenerationRecord.soiling_ratio,
            GenerationRecord.is_interval_15m,
            GenerationRecord.data_source
        ).join(Plant, GenerationRecord.plant_id == Plant.plant_id)

        # Filter strictly by data_source
        if data_source != "ALL":
            query = query.filter(GenerationRecord.data_source == data_source)

        if not include_15min:
            query = query.filter(GenerationRecord.is_interval_15m == False)

        if plant_ids and "ALL" not in plant_ids:
            if isinstance(plant_ids, str):
                plant_ids = [plant_ids]
            query = query.filter(GenerationRecord.plant_id.in_(plant_ids))

        if start_date:
            if isinstance(start_date, (str, date)):
                start_dt = datetime.combine(pd.to_datetime(start_date).date(), datetime.min.time())
                query = query.filter(GenerationRecord.timestamp >= start_dt)

        if end_date:
            if isinstance(end_date, (str, date)):
                end_dt = datetime.combine(pd.to_datetime(end_date).date(), datetime.max.time())
                query = query.filter(GenerationRecord.timestamp <= end_dt)

        records = query.order_by(GenerationRecord.timestamp.asc()).all()
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    finally:
        session.close()

def load_15min_telemetry_dataframe(plant_id="SP-01", target_date=None, data_source="SIMULATED"):
    """
    Specifically queries 15-minute readings for a specific day to graph diurnal morning ramp-up,
    peak, evening decline, DC/AC power, voltage, and inverter faults.
    """
    session = get_db_session()
    try:
        query = session.query(
            GenerationRecord.timestamp,
            GenerationRecord.plant_id,
            GenerationRecord.inverter_id,
            GenerationRecord.power_kw,
            GenerationRecord.dc_power_kw,
            GenerationRecord.actual_generation_kwh,
            GenerationRecord.expected_generation_kwh,
            GenerationRecord.ac_voltage_v,
            GenerationRecord.dc_voltage_v,
            GenerationRecord.current_a,
            GenerationRecord.irradiance_wm2,
            GenerationRecord.temperature_c,
            GenerationRecord.module_temperature_c,
            GenerationRecord.inverter_status,
            GenerationRecord.comm_status,
            GenerationRecord.data_source
        ).filter(
            GenerationRecord.data_source == data_source,
            GenerationRecord.is_interval_15m == True
        )

        if plant_id and plant_id != "ALL":
            query = query.filter(GenerationRecord.plant_id == plant_id)

        if target_date:
            start_day = datetime.combine(pd.to_datetime(target_date).date(), datetime.min.time())
            end_day = datetime.combine(pd.to_datetime(target_date).date(), datetime.max.time())
            query = query.filter(GenerationRecord.timestamp >= start_day, GenerationRecord.timestamp <= end_day)

        records = query.order_by(GenerationRecord.timestamp.asc(), GenerationRecord.inverter_id.asc()).all()
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    finally:
        session.close()

# Gateway Configuration Operations
def get_gateway_configs():
    """Returns list of all configured or unconfigured inverter gateways."""
    session = get_db_session()
    try:
        gateways = session.query(InverterGateway).all()
        return [
            {
                "id": g.id,
                "manufacturer": g.manufacturer,
                "plant_id": g.plant_id,
                "site_id": g.site_id,
                "api_key_masked": f"{g.api_key[:4]}...{g.api_key[-4:]}" if g.api_key and len(g.api_key) > 8 else ("Configured" if g.api_key else "None"),
                "has_key": bool(g.api_key),
                "base_url": g.base_url,
                "polling_interval_min": g.polling_interval_min,
                "status": g.status,
                "last_polled": g.last_polled.strftime("%Y-%m-%d %H:%M:%S") if g.last_polled else "Never",
                "last_error": g.last_error
            }
            for g in gateways
        ]
    finally:
        session.close()

def save_gateway_config(manufacturer: str, plant_id: str, site_id: str, api_key: str, api_secret: str = None, base_url: str = None, polling_interval: int = 15, status: str = "CONFIGURED"):
    """Saves or updates gateway configuration for an inverter manufacturer."""
    session = get_db_session()
    try:
        gw = session.query(InverterGateway).filter(
            InverterGateway.manufacturer == manufacturer,
            InverterGateway.plant_id == plant_id
        ).first()

        if not gw:
            gw = InverterGateway(
                manufacturer=manufacturer,
                plant_id=plant_id,
                site_id=site_id,
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                polling_interval_min=polling_interval,
                status=status
            )
            session.add(gw)
        else:
            gw.site_id = site_id
            if api_key:
                gw.api_key = api_key
            if api_secret:
                gw.api_secret = api_secret
            if base_url:
                gw.base_url = base_url
            gw.polling_interval_min = polling_interval
            gw.status = status
            gw.updated_at = datetime.utcnow()

        session.commit()
        return gw.id
    finally:
        session.close()

def update_gateway_status(manufacturer: str, plant_id: str, status: str, last_error: str = None):
    """Updates connection status and error feedback for an inverter gateway."""
    session = get_db_session()
    try:
        gw = session.query(InverterGateway).filter(
            InverterGateway.manufacturer == manufacturer,
            InverterGateway.plant_id == plant_id
        ).first()
        if gw:
            gw.status = status
            gw.last_error = last_error
            if status == "CONNECTED":
                gw.last_polled = datetime.utcnow()
            session.commit()
    finally:
        session.close()
