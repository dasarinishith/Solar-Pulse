"""
SolarPulse Database Operations
Handles database seeding, queries, bulk ingestion, and state management.
"""

import os
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session as DBSession
from database.connection import get_db_session, init_db
from database.models import Plant, GenerationRecord, TariffConfig, AlertRecord, MaintenanceRecord, DatasetUpload

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
                Plant(plant_id="SP-01", plant_name="Pavagada Solar Park", capacity_mw=50.0, location="Tumakuru, Karnataka", default_tariff_inr=3.25),
                Plant(plant_id="SP-02", plant_name="Bhadla Solar Park", capacity_mw=75.0, location="Phalodi, Rajasthan", default_tariff_inr=2.95),
                Plant(plant_id="SP-03", plant_name="Rewa Ultra Mega Solar", capacity_mw=40.0, location="Rewa, Madhya Pradesh", default_tariff_inr=3.40),
                Plant(plant_id="SP-04", plant_name="Charanka Solar Park", capacity_mw=30.0, location="Patan, Gujarat", default_tariff_inr=3.15),
            ]
            session.add_all(initial_plants)
            session.commit()

            # Add default tariff configs
            for p in initial_plants:
                t1 = TariffConfig(plant_id=p.plant_id, category="Grid Export", tariff_inr=p.default_tariff_inr, effective_from=date(2025, 1, 1))
                t2 = TariffConfig(plant_id=p.plant_id, category="Self Consumption", tariff_inr=round(p.default_tariff_inr * 1.35, 2), effective_from=date(2025, 1, 1))
                session.add_all([t1, t2])
            session.commit()

        # Check if generation records exist
        gen_count = session.query(GenerationRecord).count()
        if gen_count == 0:
            if not os.path.exists(csv_path):
                from data.generate_sample_data import generate_multi_plant_dataset
                generate_multi_plant_dataset(output_csv=csv_path)

            df = pd.read_csv(csv_path)
            bulk_insert_generation_records(df, source="SIMULATED", session=session)
            print(f"Seeded {len(df)} generation records into SQLite database.")
    finally:
        session.close()

def bulk_insert_generation_records(df: pd.DataFrame, source: str = "SIMULATED", session: DBSession = None):
    """
    Bulk inserts or updates records from a DataFrame safely.
    """
    should_close = False
    if session is None:
        session = get_db_session()
        should_close = True

    try:
        # Standardize timestamp column to datetime.date
        df["timestamp_clean"] = pd.to_datetime(df["timestamp"]).dt.date

        # Fetch existing plant IDs to ensure foreign key integrity
        valid_plants = {p.plant_id: p for p in session.query(Plant).all()}
        
        # If any plant_id is not in database, create it dynamically
        for p_id in df["plant_id"].unique():
            if p_id not in valid_plants:
                sample_name = df[df["plant_id"] == p_id]["plant_name"].iloc[0] if "plant_name" in df.columns else f"Plant {p_id}"
                new_p = Plant(plant_id=p_id, plant_name=sample_name, capacity_mw=50.0, default_tariff_inr=3.20)
                session.add(new_p)
                session.commit()
                valid_plants[p_id] = new_p

        records_to_insert = []
        for _, row in df.iterrows():
            rec = GenerationRecord(
                plant_id=str(row["plant_id"]),
                timestamp=row["timestamp_clean"],
                actual_generation_kwh=float(row.get("actual_generation_kwh", 0.0)),
                expected_generation_kwh=float(row.get("expected_generation_kwh", 0.0)),
                power_kw=float(row["power_kw"]) if pd.notna(row.get("power_kw")) else None,
                temperature_c=float(row["temperature_c"]) if pd.notna(row.get("temperature_c")) else None,
                module_temperature_c=float(row["module_temperature_c"]) if pd.notna(row.get("module_temperature_c")) else None,
                irradiance_wm2=float(row["irradiance_wm2"]) if pd.notna(row.get("irradiance_wm2")) else None,
                rainfall_mm=float(row.get("rainfall_mm", 0.0)) if pd.notna(row.get("rainfall_mm")) else 0.0,
                inverter_status=str(row.get("inverter_status", "Normal")),
                grid_export_kwh=float(row.get("grid_export_kwh", 0.0)) if pd.notna(row.get("grid_export_kwh")) else 0.0,
                self_consumption_kwh=float(row.get("self_consumption_kwh", 0.0)) if pd.notna(row.get("self_consumption_kwh")) else 0.0,
                curtailed_energy_kwh=float(row.get("curtailed_energy_kwh", 0.0)) if pd.notna(row.get("curtailed_energy_kwh")) else 0.0,
                tariff_inr_per_kwh=float(row.get("tariff_inr_per_kwh", 3.20)) if pd.notna(row.get("tariff_inr_per_kwh")) else 3.20,
                soiling_ratio=float(row.get("soiling_ratio", 1.0)) if pd.notna(row.get("soiling_ratio")) else 1.0,
                data_source=source
            )
            records_to_insert.append(rec)

        # Bulk save
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
                "grid_connection_type": p.grid_connection_type
            }
            for p in plants
        ]
    finally:
        session.close()

def load_generation_dataframe(plant_ids=None, start_date=None, end_date=None):
    """
    Loads generation records joined with plant names into a pandas DataFrame.
    """
    session = get_db_session()
    try:
        query = session.query(
            GenerationRecord.plant_id,
            Plant.plant_name,
            Plant.capacity_mw,
            GenerationRecord.timestamp,
            GenerationRecord.actual_generation_kwh,
            GenerationRecord.expected_generation_kwh,
            GenerationRecord.power_kw,
            GenerationRecord.temperature_c,
            GenerationRecord.module_temperature_c,
            GenerationRecord.irradiance_wm2,
            GenerationRecord.rainfall_mm,
            GenerationRecord.inverter_status,
            GenerationRecord.grid_export_kwh,
            GenerationRecord.self_consumption_kwh,
            GenerationRecord.curtailed_energy_kwh,
            GenerationRecord.tariff_inr_per_kwh,
            GenerationRecord.soiling_ratio,
            GenerationRecord.data_source
        ).join(Plant, GenerationRecord.plant_id == Plant.plant_id)

        if plant_ids and "ALL" not in plant_ids:
            if isinstance(plant_ids, str):
                plant_ids = [plant_ids]
            query = query.filter(GenerationRecord.plant_id.in_(plant_ids))

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(GenerationRecord.timestamp >= start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(GenerationRecord.timestamp <= end_date)

        records = query.order_by(GenerationRecord.timestamp.asc()).all()
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    finally:
        session.close()
