"""
SolarPulse Database Models
Uses SQLAlchemy ORM for relational persistence in SQLite.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean, UniqueConstraint
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
    commission_date = Column(Date, nullable=True)
    grid_connection_type = Column(String(64), default="Utility Scale Grid Tied")
    default_tariff_inr = Column(Float, default=3.20)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    generations = relationship("GenerationRecord", back_populates="plant", cascade="all, delete-orphan")
    tariffs = relationship("TariffConfig", back_populates="plant", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="plant", cascade="all, delete-orphan")
    maintenances = relationship("MaintenanceRecord", back_populates="plant", cascade="all, delete-orphan")


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    timestamp = Column(Date, nullable=False, index=True)
    actual_generation_kwh = Column(Float, nullable=False)
    expected_generation_kwh = Column(Float, nullable=False)
    power_kw = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    module_temperature_c = Column(Float, nullable=True)
    irradiance_wm2 = Column(Float, nullable=True)
    rainfall_mm = Column(Float, default=0.0)
    inverter_status = Column(String(32), default="Normal")
    grid_export_kwh = Column(Float, default=0.0)
    self_consumption_kwh = Column(Float, default=0.0)
    curtailed_energy_kwh = Column(Float, default=0.0)
    tariff_inr_per_kwh = Column(Float, default=3.20)
    soiling_ratio = Column(Float, default=1.0)
    data_source = Column(String(32), default="SIMULATED") # "SIMULATED", "UPLOADED", "API_LIVE"
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("plant_id", "timestamp", name="uq_plant_timestamp"),
    )

    plant = relationship("Plant", back_populates="generations")


class TariffConfig(Base):
    __tablename__ = "tariff_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(32), ForeignKey("plants.plant_id"), nullable=False, index=True)
    category = Column(String(64), nullable=False) # "Grid Export", "Self Consumption", "Contracted PPA", "Curtailment Compensation"
    tariff_inr = Column(Float, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
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
    timestamp = Column(Date, nullable=False)
    equipment_type = Column(String(64), nullable=False) # "Panels / Cleaning", "Inverter", "Transformer", "Scada"
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
