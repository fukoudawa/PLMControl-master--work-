from sqlalchemy import create_engine
from sqlalchemy import Column, String, Integer, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import psycopg2

"postgresql+psycopg2://root:pass@localhost/mydb"

DATABASE_NAME = "root:pass@localhost/mydb"


engine = create_engine(f'postgresql+psycopg2://{DATABASE_NAME}')


Session = sessionmaker(bind=engine)

Base = declarative_base()


class Methods(Base):
    __tablename__ = 'methods'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    experiment_history = relationship('ExperimentHistory', backref='method')
    isDeleted = Column(Boolean, default=False)


class Facilities(Base):
    __tablename__ = 'facilities'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    experiment_history = relationship('ExperimentHistory', backref='facility')
    isDeleted = Column(Boolean, default=False)


class Projects(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date_begin = Column(String)
    date_end = Column(String)
    experiment_history = relationship('ExperimentHistory', backref='project')
    isDeleted = Column(Boolean, default=False)


class Samples(Base):
    __tablename__ = 'samples'
    id = Column(Integer, primary_key=True)
    manufacturer = Column(String)
    parent = Column(Integer, nullable=True)
    date = Column(String)
    description = Column(String, nullable=False)
    current_location = Column(String)
    experiment_history = relationship('ExperimentHistory', backref='sample')
    isDeleted = Column(Boolean, default=False)


class ExperimentHistory(Base):
    __tablename__ = 'experiment_history'
    id = Column(Integer, primary_key=True)
    date = Column(String)
    description = Column(String)
    id_sample = Column(Integer, ForeignKey('samples.id'))
    id_project = Column(Integer, ForeignKey('projects.id'))
    id_facility = Column(Integer, ForeignKey('facilities.id'))
    id_method = Column(Integer, ForeignKey('methods.id'))
    data = relationship('ExperimentalData', backref='experiment')
    spectroscopy = Column(Boolean)
    mass_spectrum = Column(Boolean)
    probe = Column(Boolean)
    files_path = Column(String)
    photo_path = Column(String)
    isDeleted = Column(Boolean, default=False)


class ExperimentalData(Base):
    __tablename__ = 'experimental_data'
    id = Column(Integer, primary_key=True)
    id_experiment = Column(Integer, ForeignKey('experiment_history.id'))
    time = Column(String)
    time_experiment = Column(String)
    timestamp_abs = Column(String)
    timestamp_experimental = Column(String)
    power_supply_params = Column(String)  # json
    thermocouples = Column(String)  # json строка
    mass_spectrum = Column(String)  # json строка
    gas_flow_params = Column(String)
    aux_values = Column(String)
    isDeleted = Column(Boolean, default=False)


class PLM1ExperimentalData(Base):
    __tablename__ = 'plm_1_experimental_data'
    id = Column(Integer, primary_key=True)
    id_experiment = Column(Integer, ForeignKey('experiment_history.id'))
    time = Column(String)
    time_experiment = Column(String)
    timestamp_abs = Column(String)
    timestamp_experimental = Column(String)
    cathode_current = Column(String)
    cathode_voltage = Column(String)
    cathode_power = Column(String)
    cathode_temperature = Column(String)
    discharge_current = Column(String)
    discharge_voltage = Column(String)
    discharge_power = Column(String)
    sample_current = Column(String)
    sample_voltage = Column(String)
    solenoid_current = Column(String)
    solenoid_voltage = Column(String)
    thermocouples = Column(String)
    rrg_value = Column(String)
    pressure = Column(String)
    diagnostics = Column(String)
    aux_values = Column(String)


class PLM2ExperimentalData(Base):
    __tablename__ = 'plm_2_experimental_data'
    id = Column(Integer, primary_key=True)
    id_experiment = Column(Integer, ForeignKey('experiment_history.id'))
    time = Column(String)
    time_experiment = Column(String)
    timestamp_abs = Column(String)
    timestamp_experimental = Column(String)
    cathode_current = Column(String)
    cathode_voltage = Column(String)
    cathode_power = Column(String)
    cathode_temperature = Column(String)
    discharge_current = Column(String)
    discharge_voltage = Column(String)
    discharge_power = Column(String)
    sample_current = Column(String)
    sample_voltage = Column(String)
    solenoid_1_current = Column(String)
    solenoid_1_voltage = Column(String)
    solenoid_2_current = Column(String)
    solenoid_2_voltage = Column(String)
    thermocouples = Column(String)
    rrg_value = Column(String)
    throttle_valve_value = Column(String)
    pressure = Column(String)
    diagnostics = Column(String)
    aux_values = Column(String)


def create_database():
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    create_database()


