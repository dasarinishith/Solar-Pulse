"""
SolarPulse Database Models
Uses SQLAlchemy ORM for relational persistence in SQLite.
Supports multi-source data isolation (SIMULATED, UPLOADED, API_LIVE),
15-minute interval readings, multi-inverter tracking, and gateway configurations.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), unique=True, nullable=False, index=True)
    plant_name = Column(String(128), nullable=False)
    capacity_mw = Column(Float, nullable=False)
    location = Column(String(128), nullable=True)
    commission_date = Column(DateTime, nullable=True)
    grid_connection_type = Column(String(64), default="Utility Scale Grid Tied")
    default_tariff_inr = Column(Float, default=3.20)
    inverter_count = Column(Integer, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    generations = relationship("GenerationRecord", back_populates="plant", cascade="all, delete-orphan")
    tariffs = relationship("TariffConfig", back_populates="plant", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="plant", cascade="all, delete-orphan")
    maintenances = relationship("MaintenanceRecord", back_populates="plant", cascade="all, delete-orphan")
    gateways = relationship("InverterGateway", back_populates="plant", cascade="all, delete-orphan")


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    inverter_id = Column(String(32), default="CENTRAL", nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    actual_generation_kwh = Column(Float, nullable=False)
    expected_generation_kwh = Column(Float, nullable=False)
    power_kw = Column(Float, nullable=True) # AC Active Power
    dc_power_kw = Column(Float, nullable=True) # DC String Input Power
    ac_voltage_v = Column(Float, nullable=True) # AC Grid Voltage (e.g. 415V)
    dc_voltage_v = Column(Float, nullable=True) # DC String Voltage (e.g. 680V)
    current_a = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    module_temperature_c = Column(Float, nullable=True)
    irradiance_wm2 = Column(Float, nullable=True)
    rainfall_mm = Column(Float, default=0.0)
    inverter_status = Column(String(32), default="Normal") # "Normal", "Warning", "Fault", "Curtailed", "Standby"
    comm_status = Column(String(32), default="ONLINE") # "ONLINE", "COMM_LOST", "TIMEOUT"
    grid_export_kwh = Column(Float, default=0.0)
    self_consumption_kwh = Column(Float, default=0.0)
    curtailed_energy_kwh = Column(Float, default=0.0)
    tariff_inr_per_kwh = Column(Float, default=3.20)
    soiling_ratio = Column(Float, default=1.0)
    is_interval_15m = Column(Boolean, default=False)
    data_source = Column(String(32), default="SIMULATED", index=True) # "SIMULATED", "UPLOADED", "API_LIVE"
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("plant_id", "inverter_id", "timestamp", "data_source", name="uq_plant_inv_timestamp_source"),
    )

    plant = relationship("Plant", back_populates="generations")


class InverterGateway(Base):
    __tablename__ = "inverter_gateways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer = Column(String(64), nullable=False) # "SolarEdge", "SMA", "Fronius", "Sungrow", "Huawei"
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    site_id = Column(String(128), nullable=False)
    api_key = Column(String(256), nullable=True)
    api_secret = Column(String(256), nullable=True)
    base_url = Column(String(256), nullable=True)
    polling_interval_min = Column(Integer, default=15)
    status = Column(String(32), default="NOT_CONFIGURED") # "NOT_CONFIGURED", "CONFIGURED", "CONNECTED", "AUTH_FAILED", "OFFLINE"
    last_polled = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plant = relationship("Plant", back_populates="gateways")


class TariffConfig(Base):
    __tablename__ = "tariff_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    category = Column(String(64), nullable=False) # "Grid Export", "Self Consumption", "Contracted PPA", "Curtailment Compensation"
    tariff_inr = Column(Float, nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)
    notes = Column(String(256), nullable=True)

    plant = relationship("Plant", back_populates="tariffs")


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    severity = Column(String(32), nullable=False) # "CRITICAL", "WARNING", "INFO"
    category = Column(String(64), nullable=False) # "Underperformance", "Inverter Anomaly", "Soiling Loss", "Grid Curtailment"
    message = Column(Text, nullable=False)
    deviation_percent = Column(Float, nullable=True)
    status = Column(String(32), default="OPEN") # "OPEN", "ACKNOWLEDGED", "RESOLVED"
    resolved_at = Column(DateTime, nullable=True)

    plant = relationship("Plant", back_populates="alerts")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    equipment_type = Column(String(64), nullable=False)
    action_taken = Column(String(256), nullable=False)
    cost_inr = Column(Float, default=0.0)
    technician = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)

    plant = relationship("Plant", back_populates="maintenances")


class DatasetUpload(Base):
    __tablename__ = "dataset_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(256), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    record_count = Column(Integer, default=0)
    status = Column(String(32), default="SUCCESS")
    summary = Column(Text, nullable=True)
    import_mode = Column(String(32), default="APPEND") # "REPLACE", "APPEND"
