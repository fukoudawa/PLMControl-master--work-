from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, REAL, ForeignKey
import sqlalchemy.sql.default_comparator
Base = declarative_base()


class Info(Base):
    __tablename__ = 'info'
    id = Column(Integer, primary_key=True)
    date = Column(String)
    project = Column(String)
    facility = Column(String)
    sample = Column(String)
    description = Column(String)
    spectroscopy = Column(Boolean)
    mass_spectrum = Column(Boolean)
    probe = Column(Boolean)


class Instruments(Base):
    __tablename__ = 'instruments'
    id = Column(Integer, primary_key=True)
    time = Column(String)
    time_experiment = Column(String)
    timestamp_abs = Column(String)
    timestamp_experimental = Column(String)
    instruments_values = Column(String)  # json
    thermocouples_values = Column(String)        # json строка
    diagnostics_values = Column(String)        # json строка
    aux_values = Column(String)


# class Methods(Base):
#     __tablename__ = 'methods'
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     experiment_history = relationship('ExperimentHistory', backref='method')
#     isDeleted = Column(Boolean, default=False)
#
#
# class Facilities(Base):
#     __tablename__ = 'facilities'
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)
#     experiment_history = relationship('ExperimentHistory', backref='facility')
#     isDeleted = Column(Boolean, default=False)
#
#
# class Projects(Base):
#     __tablename__ = 'projects'
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)
#     date_begin = Column(String)
#     date_end = Column(String)
#     experiment_history = relationship('ExperimentHistory', backref='project')
#     isDeleted = Column(Boolean, default=False)
#
#
# class Samples(Base):
#     __tablename__ = 'samples'
#     id = Column(Integer, primary_key=True)
#     manufacturer = Column(String)
#     parent = Column(Integer, nullable=True)
#     date = Column(String)
#     description = Column(String, nullable=False)
#     current_location = Column(String)
#     experiment_history = relationship('ExperimentHistory', backref='sample')
#     isDeleted = Column(Boolean, default=False)
#
#
# class ExperimentHistory(Base):
#     __tablename__ = 'experiment_history'
#     id = Column(Integer, primary_key=True)
#     date = Column(String)
#     description = Column(String)
#     id_sample = Column(Integer, ForeignKey('samples.id'))
#     id_project = Column(Integer, ForeignKey('projects.id'))
#     id_facility = Column(Integer, ForeignKey('facilities.id'))
#     id_method = Column(Integer, ForeignKey('methods.id'))
#     data = relationship('ExperimentalData', backref='experiment')
#     spectroscopy = Column(Boolean)
#     mass_spectrum = Column(Boolean)
#     probe = Column(Boolean)
#     files_path = Column(String)
#     photo_path = Column(String)
#     isDeleted = Column(Boolean, default=False)
#
#
# class ExperimentalData(Base):
#     __tablename__ = 'experimental_data'
#     id = Column(Integer, primary_key=True)
#     id_experiment = Column(Integer, ForeignKey('experiment_history.id'))
#     time = Column(String)
#     time_experiment = Column(String)
#     timestamp_abs = Column(String)
#     timestamp_experimental = Column(String)
#     power_supply_params = Column(String)  # json
#     thermocouples = Column(String)  # json строка
#     mass_spectrum = Column(String)  # json строка
#     gas_flow_params = Column(String)
#     aux_values = Column(String)
#     isDeleted = Column(Boolean, default=False)
