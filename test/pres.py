import socket
import time

ip = "192.168.0.32"
port = 502
address = 4
poll_interval = 0.001

# def ERSTVAK_CRC64(command_full):
#     crc = 0
#     for ch in command_full:
#         crc += ch
#     crc = (crc % 64) + 64
#     return bytes(chr(crc), 'ascii')

# def ERSTVAK_command(addr, cmd):
#     command = "{0:03d}{1:1s}".format(addr, cmd).encode('ascii')
#     command += ERSTVAK_CRC64(command)
#     command += bytes('\r', 'ascii')
#     return command

# while True:
#     try:
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#             s.connect((ip, port))
#             s.settimeout(5)
#             s.send(ERSTVAK_command(address, 'M'))
#             data = s.recv(1024).decode('ascii')
#             mantissa = int(data[4:8]) / 1000
#             exponent = int(data[8:10]) - 20
#             print(f"{mantissa} * 10^{exponent} мбар")
#             time.sleep(poll_interval)
#     except Exception as e:
#             print(str(e))

class VacuumeterERSTEVAK:
    def __init__(self, ip, port, address):
        self.ip = ip
        self.port = port
        self.address = address

    def return_value(self):
        data = float()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            s.settimeout(5)
            s.send(self.ERSTVAK_command(self.address, 'M'))

            data = s.recv(1024).decode('ascii')
            mantissa = int(data[4:8]) / 1000
            exponent = int(data[8:10]) - 20
            data = mantissa * 10 ** exponent

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

# sensor = VacuumeterERSTEVAK(ip, port, address)
# while True:
#     print(sensor.return_value())
#     time.sleep(0.1)

if __name__ == "__main__":
    vac = VacuumeterERSTEVAK(ip = "192.168.0.32", port = 500, address = 2)
    #print(vac.ERSTVAK_command(4, "T"))
    print(vac.return_value())