import random
import pyqtgraph
import test_ui
import start_experiment_dialog
from PyQt5 import QtWidgets, QtCore
from handlers.database_handler import Info, Instruments, Base
from handlers.instruments_handler import *
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import pyvisa
from datetime import datetime, timedelta
import numpy as np
from os import path
from concurrent.futures import ThreadPoolExecutor
from handlers.mqtt_client import MQTTProducer
# global poll


def create_plot(canvas, graph_size, name, pen):
    # Создаёт график, передаём PlotItem, количество точек на графике, название графика в легенде и цвет
    # Возвращает список из оси х, у и самого объекта графика
    x = [datetime.now().timestamp() - graph_size + i for i in range(graph_size)]
    x = np.asarray(x) # type:ignore
    y = np.zeros(graph_size)
    y = np.asarray(y)  # type:ignore
    plt = canvas.plot(x, y, pen=pen, name=name)
    return [x, y, plt]


def update_plot(x, y, plt, y_data):
    # Функция обновления графика
    # На вход получает оси х, у, объект графика, и новое значение на оси у
    # Обновляет график plt и передаёт новые оси х и у
    x_data = datetime.now().timestamp()
    _x = np.delete(x, 0)
    x = np.append(_x, x_data)
    _y = np.delete(y, 0)
    y = np.append(_y, y_data)
    plt.setData(x, y)
    return [x, y]


def calc_cathode_temp(voltage, current, k):
    # Функция расчёта температуры катода
    # На входе получает напряжение и ток катода, а также величину k, которая определяется экспериментально
    # Передаёт температуру катода в кельвинах
    voltage = float(voltage)
    current = float(current)
    if current != 0.0 and voltage != 0.0:
        R = voltage / current
        ro = R * k
        T_K = round((0.084 * (ro ** 2)) + (17.56 * ro) + 62.557, 2)
        return T_K
    else:
        T_K = 0.0
        return T_K


class Reader(QtCore.QObject):
    reader_result = QtCore.pyqtSignal(dict, dict)

    def __init__(
        self,
        read_interval : int,
        sample        : SCPIInstrument, 
        discharge     : SCPIInstrument,  
        solenoid_1    : SCPIInstrument,
        solenoid_2    : SCPIInstrument, 
        cathode       : SCPIInstrument, 
        rrg           : RRGInstrument, 
        pressure_1    : VacuumeterERSTEVAK,
        pressure_2    : VacuumeterERSTEVAK, 
        pressure_3    : VacuumeterERSTEVAK,
        thermocouple  : NIDAQInstrument,
        k_value       : float,
        mqtt_configs  : dict
    ) -> None:

        QtCore.QObject.__init__(self)

        self.read_interval = read_interval
        self.k             = k_value

        self.client       = MQTTProducer(mqtt_configs)

        self.sample       = sample
        self.discharge    = discharge
        self.solenoid_1   = solenoid_1
        self.solenoid_2   = solenoid_2
        self.cathode      = cathode
        self.rrg          = rrg
        self.pressure_1   = pressure_1
        self.pressure_2   = pressure_2
        self.pressure_3   = pressure_3
        self.thermocouple = thermocouple

    def run(self) -> None:
        while True:
            instrument_data   = {}
            thermocouple_data = {}

            with ThreadPoolExecutor(max_workers = None) as executor:
                sample_feature_current     = executor.submit(self.sample.get_current)
                sample_feature_voltage     = executor.submit(self.sample.get_voltage)
                discharge_feature_current  = executor.submit(self.discharge.get_current)
                discharge_feature_voltage  = executor.submit(self.discharge.get_voltage)
                discharge_feature_power    = executor.submit(self.discharge.get_power)
                solenoid_1_feature_current = executor.submit(self.solenoid_1.get_current)
                solenoid_1_feature_voltage = executor.submit(self.solenoid_1.get_voltage)
                solenoid_2_feature_current = executor.submit(self.solenoid_2.get_current)
                solenoid_2_feature_voltage = executor.submit(self.solenoid_2.get_voltage)
                cathode_feature_current    = executor.submit(self.cathode.get_current)
                cathode_feature_voltage    = executor.submit(self.cathode.get_voltage)
                cathode_feature_power      = executor.submit(self.cathode.get_power)
                rrg_feature_inlet          = executor.submit(self.rrg.get_flow_inlet)
                pressure_1_feature         = executor.submit(self.pressure_1.return_value)
                pressure_2_feature         = executor.submit(self.pressure_2.return_value)
                pressure_3_feature         = executor.submit(self.pressure_3.return_value)
                thermocouple_feature       = executor.submit(self.thermocouple.read_thermocouple)

                # ----------------------------------------------------------------------------

                instrument_data.update({"sample_current"     : sample_feature_current.result()      })
                instrument_data.update({"sample_voltage"     : sample_feature_voltage.result()      })
                instrument_data.update({"discharge_current"  : discharge_feature_current.result()   })
                instrument_data.update({"discharge_voltage"  : discharge_feature_voltage.result()   })
                instrument_data.update({"discharge_power"    : discharge_feature_power.result()     })
                instrument_data.update({"solenoid_current_1" : solenoid_1_feature_current.result()  })
                instrument_data.update({"solenoid_voltage_1" : solenoid_1_feature_voltage.result()  })
                instrument_data.update({"solenoid_current_2" : solenoid_2_feature_current.result()  })
                instrument_data.update({"solenoid_voltage_2" : solenoid_2_feature_voltage.result()  })
                instrument_data.update({"cathode_current"    : cathode_feature_current.result()     })
                instrument_data.update({"cathode_voltage"    : cathode_feature_voltage.result()     })
                instrument_data.update({"cathode_power"      : cathode_feature_power.result()       })
                instrument_data.update({"T_cathode"          : calc_cathode_temp(
                                                                    voltage = cathode_feature_voltage.result(), 
                                                                    current = cathode_feature_current.result(), 
                                                                    k       = self.k)               })
                instrument_data.update({"rrg_value"          : rrg_feature_inlet.result()           })
                instrument_data.update({"pressure_1"         : pressure_1_feature.result()          })
                instrument_data.update({"pressure_2"         : pressure_2_feature.result()          })
                instrument_data.update({"pressure_3"         : pressure_3_feature.result()          })

                try:
                    thermocouple_values = thermocouple_feature.result()
                    for i in range(self.thermocouple.thermocouple_ch_end + 1):
                        if thermocouple_values[i] > 1450.0: 
                            thermocouple_data.update({f"CH{i}": 0.0})
                        else:
                            thermocouple_data.update({f"CH{i}": round(thermocouple_values[i], 2)}) 
                except:
                    thermocouple_data.update({f"CH{i}": 0.0 for i in range(self.thermocouple.thermocouple_ch_end + 1)})   

            # ----------------------- Publish the data --------------------------------

            self.reader_result.emit(instrument_data, thermocouple_data)

            for topic, value in instrument_data.items():
                self.client.publish(value, f"instruments/{topic}")

            for topic, value in thermocouple_data.items():
                self.client.publish(value, f"thermocouples/{topic}")


class PLMControl(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self._init_ui()
        self._init_settings()
        self._init_instruments()
        self.currentTime = QtCore.QTime(00, 00, 00)
        self.timeFormat = '0'
        self.experiment_timer = QtCore.QTimer()
        self.experiment_timer.timeout.connect(self.set_experiment_timer)
        self.writing_routine = QtCore.QTimer()
        self.writing_routine.timeout.connect(self.set_writing_routine)

        self.ch0_flag = False
        self.ch1_flag = False
        self.ch2_flag = False
        self.ch3_flag = False
        self.ch4_flag = False
        self.ch5_flag = False
        self.ch6_flag = False
        self.ch7_flag = False
        self.ch8_flag = False
        self.ch9_flag = False
        self.ch10_flag = False
        self.ch11_flag = False
        self.ch12_flag = False
        self.ch13_flag = False
        self.ch14_flag = False
        self.ch15_flag = False

        self.timestamp_experimental = 0.0

        self.reading_worker = Reader(read_interval=self.read_interval, sample=self.sample,
                                           discharge=self.discharge, solenoid_1=self.solenoid_1,
                                           solenoid_2=self.solenoid_2, cathode=self.cathode,
                                           rrg=self.rrg, pressure_1=self.pressure_1,
                                           pressure_2=self.pressure_2, pressure_3=self.pressure_3, 
                                           thermocouple=self.thermocouple, k_value=self.k,
                                           mqtt_configs=self.mqtt_configs)
        
        self.reading_thread = QtCore.QThread()
        self.reading_worker.moveToThread(self.reading_thread)
        self.reading_thread.started.connect(self.reading_worker.run)
        self.reading_worker.reader_result.connect(self.get_values)
        self.reading_thread.start()

        self.init_graphs()

        self.x_instruments = [datetime.now().timestamp() - self.thermocouple_array_size + i for i in range(self.thermocouple_array_size)]

        self.ui_main.check_remote_solenoid_2.setDisabled(True)

        self.display_timer = QtCore.QTimer()
        self.display_timer.timeout.connect(self.display_values)
        self.display_timer.start(int(self.read_interval * 1000))

        

        self.ui_start.OK_button.clicked.connect(self.start_main_window)
        self.ui_main.push_record.clicked.connect(self.start_experiment)
        self.ui_main.push_stopRecord.clicked.connect(self.stop_experiment)

        self.ui_main.check_local_sample.stateChanged.connect(self.sample_local)
        self.ui_main.check_remote_sample.stateChanged.connect(self.sample_remote)
        self.ui_main.sample_start.stateChanged.connect(self.sample_remote_start)
        self.ui_main.sample_stop.stateChanged.connect(self.sample_remote_stop)
        self.ui_main.set_u_sample.editingFinished.connect(self.set_u_sample)
        self.ui_main.set_u_sample_slider.sliderReleased.connect(self.set_u_sample_slider)
        self.ui_main.set_i_sample.editingFinished.connect(self.set_i_sample)
        self.ui_main.set_i_sample_slider.sliderReleased.connect(self.set_i_sample_slider)

        self.ui_main.check_local_discharge.stateChanged.connect(self.discharge_local)
        self.ui_main.check_remote_discharge.stateChanged.connect(self.discharge_remote)
        self.ui_main.discharge_start.stateChanged.connect(self.discharge_remote_start)
        self.ui_main.discharge_stop.stateChanged.connect(self.discharge_remote_stop)
        self.ui_main.set_u_discharge.editingFinished.connect(self.set_u_discharge)
        self.ui_main.set_i_discharge.editingFinished.connect(self.set_i_discharge)
        self.ui_main.set_p_discharge.editingFinished.connect(self.set_p_discharge)
        self.ui_main.set_u_discharge_slider.sliderReleased.connect(self.set_u_discharge_slider)
        self.ui_main.set_i_discharge_slider.sliderReleased.connect(self.set_i_discharge_slider)
        self.ui_main.set_p_discharge_slider.sliderReleased.connect(self.set_p_discharge_slider)

        self.ui_main.check_local_solenoid_1.stateChanged.connect(self.solenoid_1_local)
        self.ui_main.check_remote_solenoid_1.stateChanged.connect(self.solenoid_1_remote)
        self.ui_main.solenoid_start_1.stateChanged.connect(self.solenoid_1_remote_start)
        self.ui_main.solenoid_stop_1.stateChanged.connect(self.solenoid_1_remote_stop)
        self.ui_main.set_u_solenoid_1.editingFinished.connect(self.set_u_solenoid_1)
        self.ui_main.set_u_solenoid_slider_1.sliderReleased.connect(self.set_u_solenoid_1_slider)
        self.ui_main.set_i_solenoid_1.editingFinished.connect(self.set_i_solenoid_1)
        self.ui_main.set_i_solenoid_slider_1.sliderReleased.connect(self.set_i_solenoid_slider_1)

        self.ui_main.check_local_solenoid_2.stateChanged.connect(self.solenoid_2_local)
        self.ui_main.check_remote_solenoid_2.stateChanged.connect(self.solenoid_2_remote)
        self.ui_main.solenoid_start_2.stateChanged.connect(self.solenoid_2_remote_start)
        self.ui_main.solenoid_stop_2.stateChanged.connect(self.solenoid_2_remote_stop)
        self.ui_main.set_u_solenoid_2.editingFinished.connect(self.set_u_solenoid_2)
        self.ui_main.set_u_solenoid_slider_2.sliderReleased.connect(self.set_u_solenoid_2_slider)
        self.ui_main.set_i_solenoid_2.editingFinished.connect(self.set_i_solenoid_2)
        self.ui_main.set_i_solenoid_slider_2.sliderReleased.connect(self.set_i_solenoid_slider_2)

        self.ui_main.check_local_cathode.stateChanged.connect(self.cathode_local)
        self.ui_main.check_remote_cathode.stateChanged.connect(self.cathode_remote)
        self.ui_main.cathode_start.stateChanged.connect(self.cathode_remote_start)
        self.ui_main.cathode_stop.stateChanged.connect(self.cathode_remote_stop)
        self.ui_main.set_u_cathode.editingFinished.connect(self.set_u_cathode)
        self.ui_main.set_i_cathode.editingFinished.connect(self.set_i_cathode)
        self.ui_main.set_p_cathode.editingFinished.connect(self.set_p_cathode)
        self.ui_main.set_u_cathode_slider.sliderReleased.connect(self.set_u_cathode_slider)
        self.ui_main.set_i_cathode_slider.sliderReleased.connect(self.set_i_cathode_slider)
        self.ui_main.set_p_cathode_slider.sliderReleased.connect(self.set_p_cathode_slider)

        self.ui_main.set_rrg.editingFinished.connect(self.set_rrg)
        self.ui_main.set_rrg_slider.sliderReleased.connect(self.set_rrg_slider)

        self.ui_main.set_rrg_state.currentIndexChanged.connect(self.set_rrg_state)

        self.ui_main.ch0_push.clicked.connect(self.display_ch0)
        self.ui_main.ch1_push.clicked.connect(self.display_ch1)
        self.ui_main.ch2_push.clicked.connect(self.display_ch2)
        self.ui_main.ch3_push.clicked.connect(self.display_ch3)
        self.ui_main.ch4_push.clicked.connect(self.display_ch4)
        self.ui_main.ch5_push.clicked.connect(self.display_ch5)
        self.ui_main.ch6_push.clicked.connect(self.display_ch6)
        self.ui_main.ch7_push.clicked.connect(self.display_ch7)
        self.ui_main.ch8_push.clicked.connect(self.display_ch8)
        self.ui_main.ch9_push.clicked.connect(self.display_ch9)
        self.ui_main.ch10_push.clicked.connect(self.display_ch10)
        self.ui_main.ch11_push.clicked.connect(self.display_ch11)
        self.ui_main.ch12_push.clicked.connect(self.display_ch12)
        self.ui_main.ch13_push.clicked.connect(self.display_ch13)
        self.ui_main.ch14_push.clicked.connect(self.display_ch14)
        self.ui_main.ch15_push.clicked.connect(self.display_ch15)

    def _init_ui(self):
        self.ui_main = test_ui.Ui_MainWindow()
        self.ui_mainwindow = QtWidgets.QMainWindow()
        self.ui_main.setupUi(self.ui_mainwindow)

        self.ui_start = start_experiment_dialog.Ui_Dialog()
        self.ui_start_dialog = QtWidgets.QDialog()
        self.ui_start.setupUi(self.ui_start_dialog)

    def setup_graph(self, canvas):
        canvas.setAxisItems({'bottom': pyqtgraph.DateAxisItem()})
        canvas.showGrid(x=True, y=True)
        canvas.addLegend()

    def start_main_window(self):
        path = self.config['Path_to_write']
        try:
            os.mkdir(path)
        except OSError:
            print("Directory %s already exist" % path)
        else:
            print("Successfully created the directory %s" % path)

        name = QtCore.QDateTime.currentDateTime().toString('dd-MM-yyyy') + '_' + self.ui_start.filename.text()
        self.create_database(name, path)
        info = Info(
                    date=QtCore.QDateTime.currentDateTime().toString('dd.MM.yyyy'),
                    project=self.ui_start.project.text(),
                    facility=self.ui_start.facility.text(),
                    sample=self.ui_start.sample.text(),
                    description=self.ui_start.description.toPlainText(),
                    spectroscopy=self.ui_start.spectroscopy.isChecked(),
                    mass_spectrum=self.ui_start.mass_spectroscopy.isChecked(),
                    probe=self.ui_start.probe.isChecked()
                    )
        self.session.add(info)
        self.session.commit()
        self.ui_start_dialog.close()
        self.ui_mainwindow.show()

    def create_database(self, name, path):
        engine = create_engine(f'sqlite:///{path}/{name}.db')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def start_experiment(self):
        self.experiment_timer.start(1000)
        self.writing_routine.start(int(self.write_interval * 1000))

    def stop_experiment(self):
        self.experiment_timer.stop()
        self.writing_routine.stop()

    def set_experiment_timer(self):
        self.currentTime = self.currentTime.addSecs(1)
        self.timeFormat = self.currentTime.toString('hh:mm:ss')
        self.ui_main.set_timer.setText(self.timeFormat)

    def set_writing_routine(self):
        commit_time = time.localtime()
        commit_time_timestamp = datetime.now().timestamp()
        commit_time = time.strftime("%H:%M:%S", commit_time)
        self.timestamp_experimental = str(self.timestamp_experimental)
        
        commit = Instruments(
            time=commit_time,
            time_experiment=self.timeFormat,
            timestamp_abs=str(commit_time_timestamp),
            timestamp_experimental=self.timestamp_experimental,
            instruments_values=json.dumps(self.instrument_data),
            thermocouples_values=json.dumps(self.thermocouple_data)
        )
        self.session.add(commit)
        self.session.commit()
        self.timestamp_experimental = float(self.timestamp_experimental) + self.write_interval

    def init_graphs(self):
        # self.setup_graph(self.ui_main.sample_graph)
        # self.setup_graph(self.ui_main.discharge_graph)
        # self.setup_graph(self.ui_main.cathode_graph)
        self.setup_graph(self.ui_main.thermocouples_graph)
        self.setup_graph(self.ui_main.thermocouples_graph_full)
        # self.setup_graph(self.ui_main.pressure_graph)

        sample_i = self.ui_main.sample_graph.addPlot(row=0, col=0)
        sample_u = self.ui_main.sample_graph.addPlot(row=1, col=0)
        self.setup_graph(sample_i)
        self.setup_graph(sample_u)
        self.i_sample_plt = create_plot(sample_i, self.graph_size, name='I', pen=1)
        self.u_sample_plt = create_plot(sample_u, self.graph_size, name='U', pen=2)

        discharge_i = self.ui_main.discharge_graph.addPlot(row=0, col=0)
        discharge_u = self.ui_main.discharge_graph.addPlot(row=1, col=0)
        discharge_p = self.ui_main.discharge_graph.addPlot(row=2, col=0)
        self.setup_graph(discharge_i)
        self.setup_graph(discharge_u)
        self.setup_graph(discharge_p)
        self.u_discharge_plt = create_plot(discharge_u, self.graph_size, name='U', pen=1)
        self.i_discharge_plt = create_plot(discharge_i, self.graph_size, name='I', pen=2)
        self.p_discharge_plt = create_plot(discharge_p, self.graph_size, name='P', pen=3)

        cathode_i = self.ui_main.cathode_graph.addPlot(row=0, col=0)
        cathode_u = self.ui_main.cathode_graph.addPlot(row=1, col=0)
        cathode_p = self.ui_main.cathode_graph.addPlot(row=2, col=0)
        cathode_t = self.ui_main.cathode_graph.addPlot(row=3, col=0)
        self.setup_graph(cathode_i)
        self.setup_graph(cathode_u)
        self.setup_graph(cathode_p)
        self.setup_graph(cathode_t)
        self.u_cathode_plt = create_plot(cathode_u, self.graph_size, name='U', pen=1)
        self.i_cathode_plt = create_plot(cathode_i, self.graph_size, name='I', pen=2)
        self.p_cathode_plt = create_plot(cathode_p, self.graph_size, name='P', pen=3)
        self.t_cathode_plt = create_plot(cathode_t, self.graph_size, name='T', pen=4)

        gas_flow = self.ui_main.pressure_graph.addPlot(row=0, col=0)
        pressure_1 = self.ui_main.pressure_graph.addPlot(row=1, col=0)
        #ressure_2 = self.ui_main.pressure_graph.addPlot(row=2, col=0)
        #pressure_3 = self.ui_main.pressure_graph.addPlot(row=3, col=0)
        self.setup_graph(gas_flow)
        self.setup_graph(pressure_1)
        #self.setup_graph(pressure_2)
        #self.setup_graph(pressure_3)
        self.gas_flow_plt = create_plot(gas_flow, self.graph_size, name='G, %', pen=1)
        self.pressure_1_plt = create_plot(pressure_1, self.graph_size, name='P1, Торр', pen=2)
        self.pressure_2_plt = create_plot(pressure_1, self.graph_size, name='P2, Торр', pen=5)
        self.pressure_3_plt = create_plot(pressure_1, self.graph_size, name='P3, Торр', pen=7)

    def _init_settings(self):
        config_path = 'config_main.json'
        with open(config_path) as config_json:
            self.config = json.load(config_json)

        self.mqtt_configs = self.config["mqtt"]

        self.read_interval = float(self.config['Read_interval'])
        self.write_interval = float(self.config['Write_interval'])
        self.journal_auto_update = float(self.config['Journal_auto_update'])
        self.k = float(self.config['k_value'])
        self.graph_size = int(self.config['Graph_size'])

        self.sample_ip = self.config['sample_properties'][0]['IP']
        self.sample_connect = self.config['sample_properties'][0]['connection_type']
        #self.sample_mqtt = self.config['sample_properties'][0]['mqtt']
        
        self.discharge_ip = self.config['discharge_properties'][0]['IP']
        self.discharge_connect = self.config['discharge_properties'][0]['connection_type']
        #self.discharge_mqtt = self.config['discharge_properties'][0]['mqtt']
        
        self.solenoid_ip = self.config['solenoid_properties'][0]['IP']
        self.solenoid_connect = self.config['solenoid_properties'][0]['connection_type']
        #self.solenoid_mqtt = self.config['solenoid_properties'][0]['mqtt']
        
        self.solenoid_ip_2 = self.config['solenoid_properties'][1]['IP']
        self.solenoid_connect_2 = self.config['solenoid_properties'][1]['connection_type']
        #self.solenoid_2_mqtt = self.config['solenoid_properties'][1]['mqtt']
        
        self.solenoid_ip_3 = self.config['solenoid_properties'][2]['IP']
        self.solenoid_connect_3 = self.config['solenoid_properties'][2]['connection_type']
        #self.solenoid_3_mqtt = self.config['solenoid_properties'][2]['mqtt']
        
        self.cathode_ip = self.config['cathode_properties'][0]['IP']
        self.cathode_connect = self.config['cathode_properties'][0]['connection_type']
        #self.cathode_mqtt = self.config['cathode_properties'][0]['mqtt']

        self.thermocouple_path = self.config['Thermocouple'][0]['Path']
        self.thermocouple_array_size = int(self.config['Thermocouple'][0]['Array_size'])
        self.thermocouple_channel_start = int(self.config['Thermocouple'][0]['Channel_start'])
        self.thermocouple_channel_stop = int(self.config['Thermocouple'][0]['Channel_stop'])
        self.thermocouple_fast_read = float(self.config['Thermocouple'][0]['Fast_read'])

        self.rrg_port = self.config['RRG_connection'][0]['COM_port']
        self.rrg_baudrate = int(self.config['RRG_connection'][0]['Baudrate'])
        self.rrg_address = int(self.config['RRG_connection'][0]['Address'])
        #self.rrg_mqtt = self.config['RRG_connection'][0]['mqtt']

        self.pressure_1_ip = self.config['Pressure1'][0]['ip']
        self.pressure_1_port = int(self.config['Pressure1'][0]['port'])
        self.pressure_1_address = int(self.config['Pressure1'][0]['address'])
        #self.pressure_1_mqtt = self.config['Pressure1'][0]['mqtt']
        
        self.pressure_2_ip = self.config['Pressure2'][0]['ip']
        self.pressure_2_port = int(self.config['Pressure2'][0]['port'])
        self.pressure_2_address = int(self.config['Pressure2'][0]['address'])
        #self.pressure_2_mqtt = self.config['Pressure2'][0]['mqtt']
        
        self.pressure_3_ip = self.config['Pressure3'][0]['ip']
        self.pressure_3_port = int(self.config['Pressure3'][0]['port'])
        self.pressure_3_address = int(self.config['Pressure3'][0]['address'])
        #self.pressure_3_mqtt = self.config['Pressure3'][0]['mqtt']

        self.ui_main.set_u_sample.setMinimum(-int(self.config['sample_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_sample.setMaximum(int(self.config['sample_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_sample_slider.setMinimum(-float(self.config['sample_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_sample_slider.setMaximum(float(self.config['sample_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_sample_slider.setInterval(0.01)
        self.ui_main.set_u_sample_slider.setValue(0)
        self.ui_main.set_i_sample.setMinimum(-int(self.config['sample_properties'][0]['Current_limit']))
        self.ui_main.set_i_sample.setMaximum(int(self.config['sample_properties'][0]['Current_limit']))
        self.ui_main.set_i_sample_slider.setMinimum(-float(self.config['sample_properties'][0]['Current_limit']))
        self.ui_main.set_i_sample_slider.setMaximum(float(self.config['sample_properties'][0]['Current_limit']))
        self.ui_main.set_i_sample_slider.setInterval(0.01)
        self.ui_main.set_i_sample_slider.setValue(0)

        self.ui_main.set_u_discharge.setMaximum(int(self.config['discharge_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_discharge_slider.setMaximum(int(self.config['discharge_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_discharge_slider.setInterval(0.01)
        self.ui_main.set_i_discharge.setMaximum(int(self.config['discharge_properties'][0]['Current_limit']))
        self.ui_main.set_i_discharge_slider.setMaximum(int(self.config['discharge_properties'][0]['Current_limit']))
        self.ui_main.set_i_discharge_slider.setInterval(0.01)
        self.ui_main.set_p_discharge.setMaximum(int(self.config['discharge_properties'][0]['Power_limit']))
        self.ui_main.set_p_discharge_slider.setMaximum(int(self.config['discharge_properties'][0]['Power_limit']))
        self.ui_main.set_p_discharge_slider.setInterval(0.01)

        self.ui_main.set_u_solenoid_1.setMaximum(int(self.config['solenoid_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_1.setMaximum(int(self.config['solenoid_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_1.setInterval(0.01)
        self.ui_main.set_i_solenoid_1.setMaximum(int(self.config['solenoid_properties'][0]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_1.setMaximum(int(self.config['solenoid_properties'][0]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_1.setInterval(0.01)

        self.ui_main.set_u_solenoid_2.setMaximum(int(self.config['solenoid_properties'][1]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_2.setMaximum(int(self.config['solenoid_properties'][1]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_2.setInterval(0.01)
        self.ui_main.set_i_solenoid_2.setMaximum(int(self.config['solenoid_properties'][1]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_2.setMaximum(int(self.config['solenoid_properties'][1]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_2.setInterval(0.01)
        self.ui_main.set_p_solenoid_2.setMaximum(int(self.config['solenoid_properties'][1]['Power_limit']))
        self.ui_main.set_p_solenoid_slider_2.setMaximum(int(self.config['solenoid_properties'][1]['Power_limit']))
        self.ui_main.set_p_solenoid_slider_2.setInterval(0.01)

        self.ui_main.set_u_solenoid_3.setMaximum(int(self.config['solenoid_properties'][2]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_3.setMaximum(int(self.config['solenoid_properties'][2]['Voltage_limit']))
        self.ui_main.set_u_solenoid_slider_3.setInterval(0.01)
        self.ui_main.set_i_solenoid_3.setMaximum(int(self.config['solenoid_properties'][2]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_3.setMaximum(int(self.config['solenoid_properties'][2]['Current_limit']))
        self.ui_main.set_i_solenoid_slider_3.setInterval(0.01)
        self.ui_main.set_p_solenoid_3.setMaximum(int(self.config['solenoid_properties'][2]['Power_limit']))
        self.ui_main.set_p_solenoid_slider_3.setMaximum(int(self.config['solenoid_properties'][2]['Power_limit']))
        self.ui_main.set_p_solenoid_slider_3.setInterval(0.01)

        self.ui_main.set_u_cathode.setMaximum(int(self.config['cathode_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_cathode_slider.setMaximum(int(self.config['cathode_properties'][0]['Voltage_limit']))
        self.ui_main.set_u_cathode_slider.setInterval(0.01)
        self.ui_main.set_i_cathode.setMaximum(int(self.config['cathode_properties'][0]['Current_limit']))
        self.ui_main.set_i_cathode_slider.setMaximum(int(self.config['cathode_properties'][0]['Current_limit']))
        self.ui_main.set_i_cathode_slider.setInterval(0.01)
        self.ui_main.set_p_cathode.setMaximum(int(self.config['cathode_properties'][0]['Power_limit']))
        self.ui_main.set_p_cathode_slider.setMaximum(int(self.config['cathode_properties'][0]['Power_limit']))
        self.ui_main.set_p_cathode_slider.setInterval(0.01)

        self.ui_main.set_rrg.setMaximum(300)
        self.ui_main.set_rrg.setMinimum(0)
        self.ui_main.set_rrg_slider.setMaximum(300)
        self.ui_main.set_rrg_slider.setMinimum(0)

    def _init_instruments(self):
        print("Establishing connection with sensors...")
        self.rm = pyvisa.ResourceManager()
        self.sample = SCPIInstrument(self.rm, self.sample_connect, self.sample_ip, 5025, name='Sample')
        if not self.sample.isInitialized:
            self.ui_main.check_remote_sample.setDisabled(True)

        self.discharge = SCPIInstrument(self.rm, self.discharge_connect, self.discharge_ip, 0, name='Discharge')
        if not self.discharge.isInitialized:
            self.ui_main.check_remote_discharge.setDisabled(True)

        self.solenoid_1 = SCPIInstrument(self.rm, self.solenoid_connect, self.solenoid_ip, 5025, name='Solenoid')
        if not self.solenoid_1.isInitialized:
            self.ui_main.check_remote_solenoid_1.setDisabled(True)

        self.solenoid_2 = SCPIInstrument(self.rm, self.solenoid_connect_2, self.solenoid_ip_2, 0, name='Solenoid 2')
        if not self.solenoid_2.isInitialized:
            self.ui_main.check_remote_solenoid_2.setDisabled(True)

        self.solenoid_3 = SCPIInstrument(self.rm, self.solenoid_connect_3, self.solenoid_ip_3, 0, name='Solenoid 3')
        if not self.solenoid_3.isInitialized:
            self.ui_main.check_remote_solenoid_3.setDisabled(True)

        self.cathode = SCPIInstrument(self.rm, self.cathode_connect, self.cathode_ip, 0, name='Cathode')
        if not self.cathode.isInitialized:
            self.ui_main.check_remote_cathode.setDisabled(True)

        self.rrg = RRGInstrument(unit=self.rrg_address, method='rtu', port=self.rrg_port, baudrate=self.rrg_baudrate)
        if not self.rrg.isInitialized:
            self.ui_main.set_rrg_state.setDisabled(True)
        self.rrg.set_flow(0)
        self.ui_main.set_rrg_state.setCurrentIndex(1)

        self.thermocouple = NIDAQInstrument(self.thermocouple_path, 'thermocouples', self.thermocouple_channel_start,
                                            self.thermocouple_channel_stop)

        self.thermocouple.create_multiple_thermocouples()
        try:
            self.thermocouple.task.timing.adc_sample_high_speed()
        except Exception:
            pass

        self.pressure_1 = VacuumeterERSTEVAK(ip=self.pressure_1_ip, port=self.pressure_1_port,
                                             address=self.pressure_1_address)
        self.pressure_2 = VacuumeterERSTEVAK(ip=self.pressure_2_ip, port=self.pressure_2_port,
                                             address=self.pressure_2_address)
        self.pressure_3 = VacuumeterERSTEVAK(ip=self.pressure_3_ip, port=self.pressure_3_port,
                                             address=self.pressure_3_address)

    def get_values(self, instrument_value, thermocouple_value):
        self.instrument_data   = instrument_value
        self.thermocouple_data = thermocouple_value

    def display_values(self): 
        value = self.instrument_data
        sample_voltage = value['sample_voltage']
        sample_current = value['sample_current']
        discharge_voltage = value['discharge_voltage']
        discharge_current = value['discharge_current']
        discharge_power = value['discharge_power']
        solenoid_voltage_1 = value['solenoid_voltage_1']
        solenoid_current_1 = value['solenoid_current_1']
        solenoid_voltage_2 = value['solenoid_voltage_2']
        solenoid_current_2 = value['solenoid_current_2']
        cathode_voltage = value['cathode_voltage']
        cathode_current = value['cathode_current']
        cathode_power = value['cathode_power']
        cathode_temp = value['T_cathode']
        gas_flow = value['rrg_value']
        pressure_1 = value['pressure_1']
        pressure_2 = value['pressure_2']
        pressure_3 = value['pressure_3']
        value_thermocouples = self.thermocouple_data

        self.ui_main.u_sample_actual.setText(str(sample_voltage))
        self.ui_main.i_sample_actual.setText(str(sample_current))
        self.ui_main.u_discharge_actual.setText(str(discharge_voltage))
        self.ui_main.i_discharge_actual.setText(str(discharge_current))
        self.ui_main.p_discharge_actual.setText(str(discharge_power))
        self.ui_main.u_solenoid_actual_1.setText(str(solenoid_voltage_1))
        self.ui_main.u_solenoid_actual_2.setText(str(solenoid_voltage_2))
        self.ui_main.i_solenoid_actual_1.setText(str(solenoid_current_1))
        self.ui_main.i_solenoid_actual_2.setText(str(solenoid_current_2))
        self.ui_main.u_cathode_actual.setText(str(cathode_voltage))
        self.ui_main.i_cathode_actual.setText(str(cathode_current))
        self.ui_main.p_cathode_actual.setText(str(cathode_power))
        self.ui_main.t_cathode_actual.setText(str(cathode_temp))
        self.ui_main.rrg_actual.setText(str(gas_flow))
        self.ui_main.p_1_actual.setText(str('%.2E' % pressure_1))
        self.ui_main.p_2_actual.setText(str('%.2E' % pressure_2))
        self.ui_main.p_3_actual.setText(str('%.2E' % pressure_3))

        [self.u_cathode_plt[0], self.u_cathode_plt[1]] = update_plot(self.u_cathode_plt[0],
                                                                     self.u_cathode_plt[1],
                                                                     self.u_cathode_plt[2],
                                                                     cathode_voltage)
        [self.i_cathode_plt[0], self.i_cathode_plt[1]] = update_plot(self.i_cathode_plt[0],
                                                                     self.i_cathode_plt[1],
                                                                     self.i_cathode_plt[2],
                                                                     cathode_current)
        [self.p_cathode_plt[0], self.p_cathode_plt[1]] = update_plot(self.p_cathode_plt[0],
                                                                     self.p_cathode_plt[1],
                                                                     self.p_cathode_plt[2],
                                                                     cathode_power)
        [self.t_cathode_plt[0], self.t_cathode_plt[1]] = update_plot(self.t_cathode_plt[0],
                                                                     self.t_cathode_plt[1],
                                                                     self.t_cathode_plt[2],
                                                                     cathode_temp)

        [self.i_discharge_plt[0], self.i_discharge_plt[1]] = update_plot(self.i_discharge_plt[0],
                                                                         self.i_discharge_plt[1],
                                                                         self.i_discharge_plt[2],
                                                                         discharge_current)
        [self.u_discharge_plt[0], self.u_discharge_plt[1]] = update_plot(self.u_discharge_plt[0],
                                                                         self.u_discharge_plt[1],
                                                                         self.u_discharge_plt[2],
                                                                         discharge_voltage)
        [self.p_discharge_plt[0], self.p_discharge_plt[1]] = update_plot(self.p_discharge_plt[0],
                                                                         self.p_discharge_plt[1],
                                                                         self.p_discharge_plt[2],
                                                                         discharge_power)

        [self.i_sample_plt[0], self.i_sample_plt[1]] = update_plot(self.i_sample_plt[0],
                                                                   self.i_sample_plt[1],
                                                                   self.i_sample_plt[2],
                                                                   sample_current)
        [self.u_sample_plt[0], self.u_sample_plt[1]] = update_plot(self.u_sample_plt[0],
                                                                   self.u_sample_plt[1],
                                                                   self.u_sample_plt[2],
                                                                   sample_voltage)
        [self.pressure_1_plt[0], self.pressure_1_plt[1]] = update_plot(self.pressure_1_plt[0],
                                                                       self.pressure_1_plt[1],
                                                                       self.pressure_1_plt[2],
                                                                       pressure_1)
        [self.pressure_2_plt[0], self.pressure_2_plt[1]] = update_plot(self.pressure_2_plt[0],
                                                                       self.pressure_2_plt[1],
                                                                       self.pressure_2_plt[2],
                                                                       pressure_2)
        [self.pressure_3_plt[0], self.pressure_3_plt[1]] = update_plot(self.pressure_3_plt[0],
                                                                       self.pressure_3_plt[1],
                                                                       self.pressure_3_plt[2],
                                                                       pressure_3)
        [self.gas_flow_plt[0], self.gas_flow_plt[1]] = update_plot(self.gas_flow_plt[0],
                                                                   self.gas_flow_plt[1],
                                                                   self.gas_flow_plt[2],
                                                                   gas_flow)

        if self.ch0_flag:
            self.ui_main.ch0.setText(str(value_thermocouples['CH0']))
            [self.ch0_plt[0], self.ch0_plt[1]] = update_plot(self.ch0_plt[0],
                                                             self.ch0_plt[1],
                                                             self.ch0_plt[2],
                                                             value_thermocouples['CH0'])
        if self.ch1_flag:
            self.ui_main.ch1.setText(str(value_thermocouples['CH1']))
            [self.ch1_plt[0], self.ch1_plt[1]] = update_plot(self.ch1_plt[0],
                                                             self.ch1_plt[1],
                                                             self.ch1_plt[2],
                                                             value_thermocouples['CH1'])
        if self.ch2_flag:
            self.ui_main.ch2.setText(str(value_thermocouples['CH2']))
            [self.ch2_plt[0], self.ch2_plt[1]] = update_plot(self.ch2_plt[0],
                                                             self.ch2_plt[1],
                                                             self.ch2_plt[2],
                                                             value_thermocouples['CH2'])
        if self.ch3_flag:
            self.ui_main.ch3.setText(str(value_thermocouples['CH3']))
            [self.ch3_plt[0], self.ch3_plt[1]] = update_plot(self.ch3_plt[0],
                                                             self.ch3_plt[1],
                                                             self.ch3_plt[2],
                                                             value_thermocouples['CH3'])
        if self.ch4_flag:
            self.ui_main.ch4.setText(str(value_thermocouples['CH4']))
            [self.ch4_plt[0], self.ch4_plt[1]] = update_plot(self.ch4_plt[0],
                                                             self.ch4_plt[1],
                                                             self.ch4_plt[2],
                                                             value_thermocouples['CH4'])
        if self.ch5_flag:
            self.ui_main.ch5.setText(str(value_thermocouples['CH5']))
            [self.ch5_plt[0], self.ch5_plt[1]] = update_plot(self.ch5_plt[0],
                                                             self.ch5_plt[1],
                                                             self.ch5_plt[2],
                                                             value_thermocouples['CH5'])
        if self.ch6_flag:
            self.ui_main.ch6.setText(str(value_thermocouples['CH6']))
            [self.ch6_plt[0], self.ch6_plt[1]] = update_plot(self.ch6_plt[0],
                                                             self.ch6_plt[1],
                                                             self.ch6_plt[2],
                                                             value_thermocouples['CH6'])
        if self.ch7_flag:
            self.ui_main.ch7.setText(str(value_thermocouples['CH7']))
            [self.ch7_plt[0], self.ch7_plt[1]] = update_plot(self.ch7_plt[0],
                                                             self.ch7_plt[1],
                                                             self.ch7_plt[2],
                                                             value_thermocouples['CH7'])
        if self.ch8_flag:
            self.ui_main.ch8.setText(str(value_thermocouples['CH8']))
            [self.ch8_plt[0], self.ch8_plt[1]] = update_plot(self.ch8_plt[0],
                                                             self.ch8_plt[1],
                                                             self.ch8_plt[2],
                                                             value_thermocouples['CH8'])
        if self.ch9_flag:
            self.ui_main.ch9.setText(str(value_thermocouples['CH9']))
            [self.ch9_plt[0], self.ch9_plt[1]] = update_plot(self.ch9_plt[0],
                                                             self.ch9_plt[1],
                                                             self.ch9_plt[2],
                                                             value_thermocouples['CH9'])
        if self.ch10_flag:
            self.ui_main.ch10.setText(str(value_thermocouples['CH10']))
            [self.ch10_plt[0], self.ch10_plt[1]] = update_plot(self.ch10_plt[0],
                                                               self.ch10_plt[1],
                                                               self.ch10_plt[2],
                                                               value_thermocouples['CH10'])
        if self.ch11_flag:
            self.ui_main.ch11.setText(str(value_thermocouples['CH11']))
            [self.ch11_plt[0], self.ch11_plt[1]] = update_plot(self.ch11_plt[0],
                                                               self.ch11_plt[1],
                                                               self.ch11_plt[2],
                                                               value_thermocouples['CH11'])
        if self.ch12_flag:
            self.ui_main.ch12.setText(str(value_thermocouples['CH12']))
            [self.ch12_plt[0], self.ch12_plt[1]] = update_plot(self.ch12_plt[0],
                                                               self.ch12_plt[1],
                                                               self.ch12_plt[2],
                                                               value_thermocouples['CH12'])
        if self.ch13_flag:
            self.ui_main.ch13.setText(str(value_thermocouples['CH13']))
            [self.ch13_plt[0], self.ch13_plt[1]] = update_plot(self.ch13_plt[0],
                                                               self.ch13_plt[1],
                                                               self.ch13_plt[2],
                                                               value_thermocouples['CH13'])
        if self.ch14_flag:
            self.ui_main.ch14.setText(str(value_thermocouples['CH14']))
            [self.ch14_plt[0], self.ch14_plt[1]] = update_plot(self.ch14_plt[0],
                                                               self.ch14_plt[1],
                                                               self.ch14_plt[2],
                                                               value_thermocouples['CH14'])
        if self.ch15_flag:
            self.ui_main.ch15.setText(str(value_thermocouples['CH15']))
            [self.ch15_plt[0], self.ch15_plt[1]] = update_plot(self.ch15_plt[0],
                                                               self.ch15_plt[1],
                                                               self.ch15_plt[2],
                                                               value_thermocouples['CH15'])

    def display_ch0(self):
        if not self.ch0_flag:
            self.ch0_flag = True
            self.ch0_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH0', pen=0)
            self.ch0_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH0', pen=0)
        else:
            self.ch0_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch0_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch0_plt[2])
            self.ui_main.ch0.setText('0')

    def display_ch1(self):
        if not self.ch1_flag:
            self.ch1_flag = True
            self.ch1_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH1', pen=1)
            self.ch1_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH1', pen=1)
        else:
            self.ch1_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch1_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch1_plt[2])
            self.ui_main.ch1.setText('0')

    def display_ch2(self):
        if not self.ch2_flag:
            self.ch2_flag = True
            self.ch2_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH2', pen=2)
            self.ch2_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH2', pen=2)
        else:
            self.ch2_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch2_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch2_plt[2])
            self.ui_main.ch2.setText('0')

    def display_ch3(self):
        if not self.ch3_flag:
            self.ch3_flag = True
            self.ch3_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH3', pen=3)
            self.ch3_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH3', pen=3)
        else:
            self.ch3_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch3_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch3_plt[2])

    def display_ch4(self):
        if not self.ch4_flag:
            self.ch4_flag = True
            self.ch4_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH4', pen=4)
            self.ch4_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH4', pen=4)
        else:
            self.ch4_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch4_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch4_plt[2])

    def display_ch5(self):
        if not self.ch5_flag:
            self.ch5_flag = True
            self.ch5_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH5', pen=5)
            self.ch5_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH5', pen=5)
        else:
            self.ch5_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch5_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch5_plt[2])

    def display_ch6(self):
        if not self.ch6_flag:
            self.ch6_flag = True
            self.ch6_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH6', pen=6)
            self.ch6_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH6', pen=6)
        else:
            self.ch6_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch6_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch6_plt[2])

    def display_ch7(self):
        if not self.ch7_flag:
            self.ch7_flag = True
            self.ch7_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH7', pen=7)
            self.ch7_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH7', pen=7)
        else:
            self.ch7_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch7_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch7_plt[2])

    def display_ch8(self):
        if not self.ch8_flag:
            self.ch8_flag = True
            self.ch8_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH8', pen=8)
            self.ch8_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH8', pen=8)
        else:
            self.ch8_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch8_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch8_plt[2])

    def display_ch9(self):
        if not self.ch9_flag:
            self.ch9_flag = True
            self.ch9_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH9', pen=9)
            self.ch9_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH9', pen=9)
        else:
            self.ch9_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch9_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch9_plt[2])

    def display_ch10(self):
        if not self.ch10_flag:
            self.ch10_flag = True
            self.ch10_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH10',pen=10)
            self.ch10_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH10', pen=10)
        else:
            self.ch10_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch10_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch10_plt[2])

    def display_ch11(self):
        if not self.ch11_flag:
            self.ch11_flag = True
            self.ch11_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH11', pen=11)
            self.ch11_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH11', pen=11)
        else:
            self.ch11_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch11_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch11_plt[2])

    def display_ch12(self):
        if not self.ch12_flag:
            self.ch12_flag = True
            self.ch12_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH12', pen=12)
            self.ch12_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH12',pen=12)
        else:
            self.ch12_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch12_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch12_plt[2])

    def display_ch13(self):
        if not self.ch13_flag:
            self.ch13_flag = True
            self.ch13_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH13', pen=13)
            self.ch13_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH13', pen=13)
        else:
            self.ch13_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch13_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch13_plt[2])

    def display_ch14(self):
        if not self.ch14_flag:
            self.ch14_flag = True
            self.ch14_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH14', pen=14)
            self.ch14_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH14', pen=14)
        else:
            self.ch14_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch14_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch14_plt[2])

    def display_ch15(self):
        if not self.ch15_flag:
            self.ch15_flag = True
            self.ch15_plt = create_plot(self.ui_main.thermocouples_graph_full, self.graph_size, name='CH15', pen=15)
            self.ch15_plt_fast = create_plot(self.ui_main.thermocouples_graph, self.thermocouple_array_size, name='CH15', pen=15)
        else:
            self.ch15_flag = False
            self.ui_main.thermocouples_graph.removeItem(self.ch15_plt_fast[2])
            self.ui_main.thermocouples_graph_full.removeItem(self.ch15_plt[2])

    def sample_local(self):
        if self.ui_main.check_local_sample.isChecked():
            # self.sample.set_mode_local()
            print('SAMPLE: SYSTEM:LOCAL')
            self.ui_main.check_remote_sample.setDisabled(False)
            self.ui_main.check_remote_sample.setChecked(False)
            self.ui_main.check_local_sample.setDisabled(True)
            self.ui_main.set_i_sample.setDisabled(True)
            self.ui_main.set_i_sample_slider.setDisabled(True)
            self.ui_main.set_u_sample.setDisabled(True)
            self.ui_main.set_u_sample_slider.setDisabled(True)
            # self.ui_main.set_p_sample.setDisabled(True)
            self.ui_main.sample_start.setDisabled(True)
            self.ui_main.sample_stop.setDisabled(True)

    def sample_remote(self):
        if self.ui_main.check_remote_sample.isChecked():
            # self.sample.set_mode_remote()
            print('SAMPLE: SYSTEM:REMOTE')
            self.ui_main.check_local_sample.setDisabled(False)
            self.ui_main.check_local_sample.setChecked(False)
            self.ui_main.check_remote_sample.setDisabled(True)
            self.ui_main.set_i_sample.setDisabled(False)
            self.ui_main.set_i_sample_slider.setDisabled(False)
            self.ui_main.set_u_sample.setDisabled(False)
            self.ui_main.set_u_sample_slider.setDisabled(False)
            # self.ui_main.set_p_sample.setDisabled(False)
            self.ui_main.sample_start.setDisabled(False)
            self.ui_main.sample_stop.setDisabled(False)

    def sample_remote_start(self):
        if self.ui_main.sample_start.isChecked():
            self.ui_main.sample_stop.setChecked(False)
            self.ui_main.sample_start.setDisabled(True)
            self.sample.set_output_on()

    def sample_remote_stop(self):
        if self.ui_main.sample_stop.isChecked():
            self.ui_main.sample_start.setChecked(False)
            self.ui_main.sample_start.setDisabled(False)
            self.sample.set_output_off()

    def discharge_local(self):
        if self.ui_main.check_local_discharge.isChecked():
            self.discharge.set_mode_local()
            print('DISCHARGE: SYSTEM:LOCAL')
            self.ui_main.check_remote_discharge.setDisabled(False)
            self.ui_main.check_remote_discharge.setChecked(False)
            self.ui_main.check_local_discharge.setDisabled(True)
            self.ui_main.set_i_discharge.setDisabled(True)
            self.ui_main.set_i_discharge_slider.setDisabled(True)
            self.ui_main.set_u_discharge.setDisabled(True)
            self.ui_main.set_u_discharge_slider.setDisabled(True)
            self.ui_main.set_p_discharge.setDisabled(True)
            self.ui_main.set_p_discharge_slider.setDisabled(True)
            self.ui_main.discharge_start.setDisabled(True)
            self.ui_main.discharge_stop.setDisabled(True)

    def discharge_remote(self):
        if self.ui_main.check_remote_discharge.isChecked():
            self.discharge.set_mode_remote()
            print('DISCHARGE: SYSTEM:REMOTE')
            self.ui_main.check_local_discharge.setDisabled(False)
            self.ui_main.check_local_discharge.setChecked(False)
            self.ui_main.check_remote_discharge.setDisabled(True)
            self.ui_main.set_i_discharge.setDisabled(False)
            self.ui_main.set_i_discharge_slider.setDisabled(False)
            self.ui_main.set_u_discharge.setDisabled(False)
            self.ui_main.set_u_discharge_slider.setDisabled(False)
            self.ui_main.set_p_discharge.setDisabled(False)
            self.ui_main.set_p_discharge_slider.setDisabled(False)
            self.ui_main.discharge_start.setDisabled(False)
            self.ui_main.discharge_stop.setDisabled(False)

    def discharge_remote_start(self):
        if self.ui_main.discharge_start.isChecked():
            self.ui_main.discharge_stop.setChecked(False)
            self.ui_main.discharge_start.setDisabled(True)
            self.discharge.set_output_on()

    def discharge_remote_stop(self):
        if self.ui_main.discharge_stop.isChecked():
            self.ui_main.discharge_start.setChecked(False)
            self.ui_main.discharge_start.setDisabled(False)
            self.discharge.set_output_off()

    def solenoid_1_local(self):
        if self.ui_main.check_local_solenoid_1.isChecked():
            print('SOLENOID: SYSTEM:LOCAL')
            self.ui_main.check_remote_solenoid_1.setDisabled(False)
            self.ui_main.check_remote_solenoid_1.setChecked(False)
            self.ui_main.check_local_solenoid_1.setDisabled(True)
            self.ui_main.set_i_solenoid_1.setDisabled(True)
            self.ui_main.set_i_solenoid_slider_1.setDisabled(True)
            self.ui_main.set_u_solenoid_1.setDisabled(True)
            self.ui_main.set_u_solenoid_slider_1.setDisabled(True)
            self.ui_main.solenoid_start_1.setDisabled(True)
            self.ui_main.solenoid_stop_1.setDisabled(True)

    def solenoid_1_remote(self):
        if self.ui_main.check_remote_solenoid_1.isChecked():
            print('SOLENOID: SYSTEM:REMOTE')
            self.ui_main.check_local_solenoid_1.setDisabled(False)
            self.ui_main.check_local_solenoid_1.setChecked(False)
            self.ui_main.check_remote_solenoid_1.setDisabled(True)
            self.ui_main.set_u_solenoid_1.setDisabled(False)
            self.ui_main.set_u_solenoid_slider_1.setDisabled(False)
            self.ui_main.set_i_solenoid_1.setDisabled(False)
            self.ui_main.set_i_solenoid_slider_1.setDisabled(False)
            self.ui_main.solenoid_start_1.setDisabled(False)
            self.ui_main.solenoid_stop_1.setDisabled(False)

    def solenoid_1_remote_start(self):
        if self.ui_main.solenoid_start_1.isChecked():
            self.ui_main.solenoid_stop_1.setChecked(False)
            self.ui_main.solenoid_start_1.setDisabled(True)
            self.solenoid_1.set_output_on()

    def solenoid_1_remote_stop(self):
        if self.ui_main.solenoid_stop_1.isChecked():
            self.ui_main.solenoid_start_1.setChecked(False)
            self.ui_main.solenoid_start_1.setDisabled(False)
            self.solenoid_1.set_output_off()

    def solenoid_2_local(self):
        if self.ui_main.check_local_solenoid_2.isChecked():
            print('SOLENOID: SYSTEM:LOCAL')
            self.ui_main.check_remote_solenoid_2.setDisabled(False)
            self.ui_main.check_remote_solenoid_2.setChecked(False)
            self.ui_main.check_local_solenoid_2.setDisabled(True)
            self.ui_main.set_i_solenoid_2.setDisabled(True)
            self.ui_main.set_i_solenoid_slider_2.setDisabled(True)
            self.ui_main.set_u_solenoid_2.setDisabled(True)
            self.ui_main.set_u_solenoid_slider_2.setDisabled(True)
            self.ui_main.solenoid_start_2.setDisabled(True)
            self.ui_main.solenoid_stop_2.setDisabled(True)

    def solenoid_2_remote(self):
        if self.ui_main.check_remote_solenoid_2.isChecked():
            print('SOLENOID: SYSTEM:REMOTE')
            self.ui_main.check_local_solenoid_2.setDisabled(False)
            self.ui_main.check_local_solenoid_2.setChecked(False)
            self.ui_main.check_remote_solenoid_2.setDisabled(True)
            self.ui_main.set_u_solenoid_2.setDisabled(False)
            self.ui_main.set_u_solenoid_slider_2.setDisabled(False)
            self.ui_main.set_i_solenoid_2.setDisabled(False)
            self.ui_main.set_i_solenoid_slider_2.setDisabled(False)
            self.ui_main.solenoid_start_2.setDisabled(False)
            self.ui_main.solenoid_stop_2.setDisabled(False)

    def solenoid_2_remote_start(self):
        if self.ui_main.solenoid_start_2.isChecked():
            self.ui_main.solenoid_stop_2.setChecked(False)
            self.ui_main.solenoid_start_2.setDisabled(True)
            self.solenoid_2.set_output_on()

    def solenoid_2_remote_stop(self):
        if self.ui_main.solenoid_stop_2.isChecked():
            self.ui_main.solenoid_start_2.setChecked(False)
            self.ui_main.solenoid_start_2.setDisabled(False)
            self.solenoid_2.set_output_off()

    def cathode_local(self):
        if self.ui_main.check_local_cathode.isChecked():
            self.cathode.set_mode_local()
            print('CATHODE: SYSTEM:LOCAL')
            self.ui_main.check_remote_cathode.setDisabled(False)
            self.ui_main.check_remote_cathode.setChecked(False)
            self.ui_main.check_local_cathode.setDisabled(True)
            self.ui_main.set_i_cathode.setDisabled(True)
            self.ui_main.set_i_cathode_slider.setDisabled(True)
            self.ui_main.set_u_cathode.setDisabled(True)
            self.ui_main.set_u_cathode_slider.setDisabled(True)
            self.ui_main.set_p_cathode.setDisabled(True)
            self.ui_main.set_p_cathode_slider.setDisabled(True)
            self.ui_main.cathode_start.setDisabled(True)
            self.ui_main.cathode_stop.setDisabled(True)

    def cathode_remote(self):
        if self.ui_main.check_remote_cathode.isChecked():
            self.cathode.set_mode_remote()
            print('CATHODE: SYSTEM:REMOTE')
            self.ui_main.check_local_cathode.setDisabled(False)
            self.ui_main.check_local_cathode.setChecked(False)
            self.ui_main.check_remote_cathode.setDisabled(True)
            self.ui_main.set_i_cathode.setDisabled(False)
            self.ui_main.set_i_cathode_slider.setDisabled(False)
            self.ui_main.set_u_cathode.setDisabled(False)
            self.ui_main.set_u_cathode_slider.setDisabled(False)
            self.ui_main.set_p_cathode.setDisabled(False)
            self.ui_main.set_p_cathode_slider.setDisabled(False)
            self.ui_main.cathode_start.setDisabled(False)
            self.ui_main.cathode_stop.setDisabled(False)

    def cathode_remote_start(self):
        if self.ui_main.cathode_start.isChecked():
            self.ui_main.cathode_stop.setChecked(False)
            self.cathode.set_output_on()

    def cathode_remote_stop(self):
        if self.ui_main.cathode_stop.isChecked():
            self.ui_main.cathode_start.setChecked(False)
            self.cathode.set_output_off()

    def set_u_sample(self):
        self.u_sample = round(self.ui_main.set_u_sample.value(), 2)
        self.ui_main.set_u_sample_slider.setValue(self.u_sample)
        self.sample.set_voltage(self.u_sample)

    def set_u_sample_slider(self):
        self.u_sample = round(self.ui_main.set_u_sample_slider.value(), 2)
        self.ui_main.set_u_sample.setValue(self.u_sample)
        self.sample.set_voltage(self.u_sample)

    def set_i_sample(self):
        self.i_sample = round(self.ui_main.set_i_sample.value(), 2)
        self.ui_main.set_i_sample_slider.setValue(self.i_sample)
        self.sample.set_current(self.i_sample)

    def set_i_sample_slider(self):
        self.i_sample = round(self.ui_main.set_i_sample_slider.value(), 2)
        self.ui_main.set_i_sample.setValue(self.i_sample)
        self.sample.set_current(self.i_sample)

    def set_u_discharge(self):
        self.u_discharge = round(self.ui_main.set_u_discharge.value(), 2)
        self.ui_main.set_u_discharge_slider.setValue(self.u_discharge)
        self.discharge.set_voltage(self.u_discharge)

    def set_u_discharge_slider(self):
        self.u_discharge = round(self.ui_main.set_u_discharge_slider.value(), 2)
        self.ui_main.set_u_discharge.setValue(self.u_discharge)
        self.discharge.set_voltage(self.u_discharge)

    def set_i_discharge(self):
        self.i_discharge = round(self.ui_main.set_i_discharge.value(), 2)
        self.ui_main.set_i_discharge_slider.setValue(self.i_discharge)
        self.discharge.set_current(self.i_discharge)

    def set_i_discharge_slider(self):
        self.i_discharge = round(self.ui_main.set_i_discharge_slider.value(), 2)
        self.ui_main.set_i_discharge.setValue(self.i_discharge)
        self.discharge.set_current(self.i_discharge)

    def set_p_discharge(self):
        self.p_discharge = round(self.ui_main.set_p_discharge.value(), 2)
        self.ui_main.set_p_discharge_slider.setValue(self.p_discharge)
        self.discharge.set_power(self.p_discharge)

    def set_p_discharge_slider(self):
        self.p_discharge = round(self.ui_main.set_p_discharge_slider.value(), 2)
        self.ui_main.set_p_discharge.setValue(self.p_discharge)
        self.discharge.set_power(self.p_discharge)

    def set_u_solenoid_1(self):
        self.u_solenoid_1 = round(self.ui_main.set_u_solenoid_1.value(), 2)
        self.ui_main.set_u_solenoid_slider_1.setValue(self.u_solenoid_1)
        self.solenoid_1.set_voltage(self.u_solenoid_1)

    def set_u_solenoid_1_slider(self):
        self.u_solenoid_1 = round(self.ui_main.set_u_solenoid_slider_1.value(), 2)
        self.ui_main.set_u_solenoid_1.setValue(self.u_solenoid_1)
        self.solenoid_1.set_voltage(self.u_solenoid_1)

    def set_i_solenoid_1(self):
        self.i_solenoid_1 = round(self.ui_main.set_i_solenoid_1.value(), 2)
        self.ui_main.set_i_solenoid_slider_1.setValue(self.i_solenoid_1)
        self.solenoid_1.set_current(self.i_solenoid_1)

    def set_i_solenoid_slider_1(self):
        self.i_solenoid_1 = round(self.ui_main.set_i_solenoid_slider_1.value(), 2)
        self.ui_main.set_i_solenoid_1.setValue(self.i_solenoid_1)
        self.solenoid_1.set_current(self.i_solenoid_1)

    def set_u_solenoid_2(self):
        self.u_solenoid_2 = round(self.ui_main.set_u_solenoid_2.value(), 2)
        self.ui_main.set_u_solenoid_slider_2.setValue(self.u_solenoid_2)
        self.solenoid_2.set_voltage(self.u_solenoid_2)

    def set_u_solenoid_2_slider(self):
        self.u_solenoid_2 = round(self.ui_main.set_u_solenoid_slider_2.value(), 2)
        self.ui_main.set_u_solenoid_2.setValue(self.u_solenoid_2)
        self.solenoid_2.set_voltage(self.u_solenoid_2)

    def set_i_solenoid_2(self):
        self.i_solenoid_2 = round(self.ui_main.set_i_solenoid_2.value(), 2)
        self.ui_main.set_i_solenoid_slider_2.setValue(self.i_solenoid_2)
        self.solenoid_2.set_current(self.i_solenoid_2)

    def set_i_solenoid_slider_2(self):
        self.i_solenoid_2 = round(self.ui_main.set_i_solenoid_slider_2.value(), 2)
        self.ui_main.set_i_solenoid_2.setValue(self.i_solenoid_2)
        self.solenoid_2.set_current(self.i_solenoid_2)

    def set_u_cathode(self):
        self.u_cathode = round(self.ui_main.set_u_cathode.value(), 2)
        self.ui_main.set_u_cathode_slider.setValue(self.u_cathode)
        self.cathode.set_voltage(self.u_cathode)

    def set_u_cathode_slider(self):
        self.u_cathode = round(self.ui_main.set_u_cathode_slider.value(), 2)
        self.ui_main.set_u_cathode.setValue(self.u_cathode)
        self.cathode.set_voltage(self.u_cathode)

    def set_i_cathode(self):
        self.i_cathode = round(self.ui_main.set_i_cathode.value(), 2)
        self.ui_main.set_i_cathode_slider.setValue(self.i_cathode)
        self.cathode.set_current(self.i_cathode)

    def set_i_cathode_slider(self):
        self.i_cathode = round(self.ui_main.set_i_cathode_slider.value(), 2)
        self.ui_main.set_i_cathode.setValue(self.i_cathode)
        self.cathode.set_current(self.i_cathode)

    def set_p_cathode(self):
        self.p_cathode = round(self.ui_main.set_p_cathode.value(), 2)
        self.ui_main.set_p_cathode_slider.setValue(self.p_cathode)
        self.cathode.set_power(self.p_cathode)

    def set_p_cathode_slider(self):
        self.p_cathode = round(self.ui_main.set_p_cathode_slider.value(), 2)
        self.ui_main.set_p_cathode.setValue(self.p_cathode)
        self.cathode.set_power(self.p_cathode)

    def set_rrg(self):
        self.gas = round(self.ui_main.set_rrg.value(), 2)
        self.ui_main.set_rrg_slider.setValue(self.gas)
        self.rrg.set_flow(self.gas)

    def set_rrg_slider(self):
        self.gas = round(self.ui_main.set_rrg_slider.value(), 2)
        self.ui_main.set_rrg.setValue(self.gas)
        self.rrg.set_flow(self.gas)

    def get_rrg_state(self):
        state = self.rrg.get_state()
        self.ui_main.set_rrg_state.setCurrentIndex(state) #type:ignore

    def set_rrg_state(self):
        # 0 - открыт, 1 - закрыт, 2 - регулировка
        state = self.ui_main.set_rrg_state.currentIndex()
        self.rrg.set_state(state)
        if state == 0:
            self.ui_main.set_rrg.setDisabled(False)
            self.ui_main.set_rrg_slider.setDisabled(False)
            self.ui_main.set_rrg.setValue(100)
            self.ui_main.set_rrg_slider.setValue(100)
        if state == 1:
            self.ui_main.set_rrg.setDisabled(True)
            self.ui_main.set_rrg_slider.setDisabled(True)
            self.ui_main.set_rrg.setValue(0)
            self.ui_main.set_rrg_slider.setValue(0)
            self.rrg.set_flow(0)
        if state == 2:
            self.ui_main.set_rrg.setDisabled(False)
            self.ui_main.set_rrg_slider.setDisabled(False)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    plm_control = PLMControl()
    plm_control.ui_start_dialog.show()
    sys.exit(app.exec_())
