from nidaqmx import Task, constants
import time
import serial
from pymodbus.client import ModbusSerialClient
import socket


class SCPIInstrument:
    """
    Класс, реализующий управление источниками питания через протокол SCPI
    """
    def __init__(self, rm, connection_type, ip, port, name, sleep_time=0.01):
        self.name = name  # название прибора
        self.isInitialized = bool()  # флаг инициализации
        self.sleep_time = sleep_time  # интервал между командами
        try:
            if connection_type == 'TCPIP':  # Первый способ установки соединения с прибором
                self.instrument = rm.open_resource(f'TCPIP::{ip}::inst0::INSTR')
            if connection_type == 'SOCKET':  # Второй способ установки соединения с прибором
                self.instrument = rm.open_resource(f'TCPIP::{ip}::{port}::SOCKET')
                self.instrument.write_termination = '\n'
                self.instrument.read_termination = '\n'
            #print(f'{self.name}')
            #print(self.get_identification())
            print(f'(+) {self.name} initialized: {self.get_identification()}')
            self.isInitialized = True

        except Exception as e:
            self.instrument = None
            print(f'(!) {self.name} failed to initialize:\t{e}')
            self.IsInitialized = False

    def set_voltage(self, value: float):
        """
        Отправляет в прибор команду на установление напряжения, переданного в метод
        """
        try:
            self.instrument.write(f'VOLTAGE {value}') #type:ignore
            time.sleep(self.sleep_time)
        except Exception:
            pass

    def set_current(self, value: float):
        """
        Отправляет в прибор команду на установление тока, переданного в метод
        """
        try:
            self.instrument.write(f'CURRENT {value}')#type:ignore
            time.sleep(self.sleep_time)
        except Exception:
            pass

    def set_power(self, value: float):
        """
        Отправляет в прибор команду на установление мощности, переданного в метод
        """
        try:
            self.instrument.write(f'POWER {value}')#type:ignore
            time.sleep(self.sleep_time)
        except Exception:
            pass

    def get_voltage(self):
        """
        Возвращает текущее напряжение на источнике питания
        """
        try:
            return round(float(self.instrument.query('MEASURE:VOLTAGE?').strip('\x00')), 2)#type:ignore
        except:
            return 0.0

    def get_current(self):
        """
        Возвращает текущий ток на источнике питания
        """
        try:
            return round(float(self.instrument.query('MEASURE:CURRENT?').strip('\x00')), 2)#type:ignore
        except:
            return 0.0

    def get_power(self):
        """
        Возвращает текущую мощность на источнике питания
        """
        try:
            return round(float(self.instrument.query('MEASURE:POWER?').strip('\x00')), 2)#type:ignore
        except:
            return 0.0

    def get_identification(self):
        """
        Возвращает идентификацию прибора
        """
        try:   
            return self.instrument.query('*IDN?')#type:ignore
        except:
            return 0.0

    def set_output_on(self):
        """
        Включает выход источника питания, передаёт состояние выхода прибора (0-выход отключен, 1-выход включен)
        """
        try:
            self.instrument.write('OUTPUT ON')#type:ignore
            time.sleep(self.sleep_time)
            return self.instrument.query('OUTPUT?')#type:ignore
        except Exception:
            print(f'{self.name}: Cannot set output to on')

    def set_output_off(self):
        """
        Выключает выход источника питания, передаёт состояние выхода прибора (0-выход отключен, 1-выход включен)
        """
        try:
            self.instrument.write('OUTPUT OFF')#type:ignore
            time.sleep(self.sleep_time)
            return self.instrument.query('OUTPUT?')#type:ignore
        except Exception:
            print(f'{self.name}: Cannot set output to off')

    def set_mode_local(self):
        """
        Устанавливает прибор в состояние, при котором управление осуществляется с лицевой панели прибора
        """
        try:
            self.instrument.write('SYSTEM:LOCAL')#type:ignore
            time.sleep(self.sleep_time)
            return f'{self.name}: SYSTEM:LOCAL'
        except Exception:
            print(f'{self.name}: Cannot set device to local mode')

    def set_mode_remote(self):
        """
        Устанавливает прибор в состояние, при котором управление можно осуществлять удалённо, а прибор способен
        воспринимать команды со сторонних программ
        """
        try:
            self.instrument.write('SYSTEM:REMOTE')#type:ignore
            time.sleep(self.sleep_time)
            return f'{self.name}: SYSTEM:REMOTE'
        except Exception:
            print(f'{self.name}: Cannot set device to remote mode')


class PyrometerInstrument:
    """
    Класс, объединяющий методы для работы с пирометром через COM-порт
    """
    def __init__(self, port, baudrate):
        self.isInitialized = bool()
        try:
            self.ser = serial.Serial(port=port, baudrate=baudrate)
            self.ser.open()
            print('(+) Pyrometer initialized')
            self.isInitialized = True

        except Exception:
            self.ser = object
            print('(!) Failed to initialize pyrometer')
            self.isInitialized = False

    def return_value_pyrometer(self):
        value = self.ser.readline().decode('ascii') #type:ignore  # получаем от пирометра абракадабру и декодируем её в строку
        return value[9:len(value)-3]                 # достаём из строки значение температуры на пирометре


class RRGInstrument:

    def __init__(self, unit, method, port, baudrate):
        self.isInitialized = bool()
        self.unit = unit
        try:
            self.client = ModbusSerialClient(port=port, baudrate=baudrate)
            self.client.connect()
            self.isInitialized = True
            print("(+) RRG initialized")
        except Exception as e:
            self.isInitialized = False
            self.client = None
            print("(!) Failed to initialize RRG:\t", e)

    def _get_holding_registers(self):
        try:
            rr = self.client.read_holding_registers(0, 7, slave=self.unit) #type:ignore
            self.holding_registers = rr.registers  # list of ints
            self.flag_1 = bin(self.holding_registers[2])  # binary string
            self.flag_1 = self.flag_1[::-1]  # reversed binary string
            self.flag_1 = self.flag_1[:-2]   # reversed binary string without 0b
            # преобразование строки в список целых чисел
            self.flag_1_int = [int(self.flag_1[i]) for i in range(len(self.flag_1))]

        except Exception as e:
            if self.isInitialized:
                print(f'(ERROR) RRG: Cannot get holding registers: {e}')

    def get_state(self):
        result = int()

        try:
            self._get_holding_registers()
            bit_2 = self.flag_1_int[2]
            bit_3 = self.flag_1_int[3]
            if bit_2 == 1 and bit_3 == 0:
                result = 0
            if bit_2 == 0 and bit_3 == 1:
                result = 1
            if bit_2 == 0 and bit_3 == 0:
                result = 2
            if bit_2 == 1 and bit_3 == 1:
                result = 0

        except Exception:
            if self.isInitialized:
                result = -1
                print('(ERROR) RRG: Cannot get state')

        return result

    def get_flow_inlet(self):
        try:
            self._get_holding_registers()
            flow_inlet = self.holding_registers[4]
            flow_outlet = self.holding_registers[5]
            flow_outlet = bin(flow_outlet)
            flow_inlet = round(flow_inlet * 0.01, 2)
            return flow_inlet
        except Exception:
            if self.isInitialized:
                print('(ERROR) RRG: Cannot get flow inlet')
            return 0

    def get_flow_outlet(self):
        pass

    def set_state(self, state):
        # 0 - открыт, 1 - закрыт, 2 - регулировка
        try:
            self._get_holding_registers()
            # if state == 'RRG open 1':
            #     self.flag_1_int[2] = 1
            #     self.flag_1_int[3] = 1
            if state == 0:
                self.flag_1_int[2] = 1
                self.flag_1_int[3] = 0
            if state == 1:
                self.flag_1_int[2] = 0
                self.flag_1_int[3] = 1
            if state == 2:
                self.flag_1_int[2] = 0
                self.flag_1_int[3] = 0
            self.flag_1_int = self.flag_1_int[::-1]
            self.flag_1 = map(str, self.flag_1_int)
            self.flag_1 = ''.join(self.flag_1)
            self.flag_1 = int(self.flag_1, 2)
            self.client.write_register(2, self.flag_1, slave=self.unit) #type:ignore
        except Exception:
            if self.isInitialized:
                print('(ERROR) RRG: Set state has failed')

    def set_flow(self, value: int):
        try:
            value_to_rrg = value * 100
            self.client.write_register(4, value_to_rrg, slave=self.unit) #type:ignore
            self._get_holding_registers()
            return self.holding_registers[4]
        except Exception:
            if self.isInitialized:
                print('(ERROR) RRG: Set flow has failed')
            return None


class NIDAQInstrument:
    def __init__(self,
                 path,
                 name,
                 thermocouple_ch_start,
                 thermocouple_ch_end=0,
                 thermocouple_type='K',
                 thermal_unit='C',
                 high_speed_adc=True,
                 sleep_time=0,
                 cjc='default'):
        self.path = path
        self.name = name
        self.thermocouple_ch_start = thermocouple_ch_start
        self.thermocouple_ch_end = thermocouple_ch_end
        self.sleep_time = sleep_time
        self.cjc = cjc

        if thermocouple_type == 'K':
            self.thermocouple_type = constants.ThermocoupleType.K
        if thermocouple_type == 'J':
            self.thermocouple_type = constants.ThermocoupleType.J
        if thermocouple_type == 'B':
            self.thermocouple_type = constants.ThermocoupleType.B
        if thermocouple_type == 'E':
            self.thermocouple_type = constants.ThermocoupleType.E
        if thermocouple_type == 'N':
            self.thermocouple_type = constants.ThermocoupleType.N
        if thermocouple_type == 'R':
            self.thermocouple_type = constants.ThermocoupleType.R
        if thermocouple_type == 'S':
            self.thermocouple_type = constants.ThermocoupleType.S
        if thermocouple_type == 'T':
            self.thermocouple_type = constants.ThermocoupleType.T
        if thermal_unit == 'C':
            self.thermal_unit = constants.TemperatureUnits.DEG_C
        if thermal_unit == 'K':
            self.thermal_unit = constants.TemperatureUnits.DEG_K #type:ignore
        try:
            self.task = Task()
            # try:
            #     if high_speed_adc:
            #         self.task.timing.adc_sample_high_speed()
            #     else:
            #         pass
            # except Exception:
            #     print('Cannot set ADC on thermocouple to high speed mode')
            self.isInitialized = True
            print("(+) Thermocouple initialized")
        except Exception:
            self.task = None
            print(f'Thermocouple {self.name} does not initialized')
            self.isInitialized = False

    def create_single_thermocouple(self):
        try:
            self.task.ai_channels.add_ai_thrmcpl_chan(rf'{self.path}/ai{self.thermocouple_ch_start}', #type:ignore
                                                      thermocouple_type=self.thermocouple_type,
                                                      units=self.thermal_unit
                                                      )
        except Exception:
            print(f'Thermocouple {self.name} does not created')

    def create_multiple_thermocouples(self):
        try:
            self.task.ai_channels.add_ai_thrmcpl_chan(                                                                        #type:ignore
                                            rf'{self.path}/ai{self.thermocouple_ch_start}:{self.thermocouple_ch_end}',
                                            thermocouple_type=self.thermocouple_type, units=self.thermal_unit
                                                    )
        except Exception:
            print(f'Thermocouple {self.name} does not created')

    def read_thermocouple(self):
        # try:
            value = self.task.read() #type:ignore
            # time.sleep(self.sleep_time)
            return value
        # except Exception:
        #     print('Cannot read value from thermocouple')
        #     return None

    def stop_task(self):
        self.task.close() #type:ignore

class VacuumeterERSTEVAK:
    def __init__(self, ip, port, address):
        self.ip = ip
        self.port = port
        self.address = address

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.ip, self.port))
            print("(+) Vacuumeter reader initialized")
        except OSError as e:
            s.close()
            print("(!) Failed to initialize Vacuumeter reader:\t", e)

    def return_value(self):
        data = float()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((self.ip, self.port))
                s.send(self.ERSTVAK_command(self.address, 'M'))
                data = s.recv(1024).decode('ascii')
                mantissa = int(data[4:8]) / 1000
                exponent = int(data[8:10]) - 20
                data = mantissa * 10 ** exponent * 0.75  # torr
        except:
            data = 0

        return data

    def ERSTVAK_CRC64(self, command_full):
        crc = 0
        for ch in command_full:
            crc += ch
        crc = (crc % 64) + 64
        return bytes(chr(crc), 'ascii')

    def ERSTVAK_command(self, addr, cmd):
        command = "{0:03d}{1:1s}".format(addr, cmd).encode('ascii')
        command += self.ERSTVAK_CRC64(command)
        command += bytes('\r', 'ascii')
        return command


class VacuumeterADC:
    """
     Класс, объединяющий методы для работы с вакуумметрами через COM-порт
     TODO: hardcoded af, переделать?
    """

    def __init__(self, port, baudrate):
        self.isInitialized = bool()

        try:
            self.device = serial.Serial(port=port, baudrate=baudrate)
            self.isInitialized = True
            print("(+) Vacuumeter reader initialized")

        except serial.SerialException as se:
            self.device = serial.Serial()
            self.isInitialized = False
            print("(!) Failed to initialize Vacuumeter reader:\t", se)

    def __del__(self):
        if self.device != None:
            self.device.close()

    def return_value(self):
        data = { "Пушка": 0, "Ресивер": 0, "Форвакуумная линия": 0}

        if self.isInitialized:
            adc_ch = str(self.device.readline()).split(',')
            adc_voltage = lambda adc, r1, r2, udd: adc * (r2/r1) * (udd/2**16)
            pressure_ersvak = lambda u: (10**(u-5.5)) * 1.333 # torr
            pressure_instrue = lambda u: 10**(1.222*u-7.647)  # torr

            data["Пушка"] = pressure_ersvak(adc_voltage(adc_ch[0], 1000, 4500, 5.0))
            data["Ресивер"] = pressure_instrue(adc_voltage(adc_ch[1], 1000, 4500, 5.0))
            data["Форвакуумная линия"] = pressure_ersvak(adc_voltage(adc_ch[2], 1000, 4500, 5.0))

        return data



class ElimInstrument:
    # Заглушка под управление источниками питания ЭЛИМ
    pass

if __name__ == "__main__":
    VacuumeterERSTEVAK(
        ip = '192.168.0.32',
        port = 501,
        address = 3
    )







