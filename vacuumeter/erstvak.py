import socket
import time

def ERSTVAK_CRC64(command_full):
        crc = 0
        for ch in command_full:
            crc += ch
        crc = (crc % 64) + 64
        return bytes(chr(crc), 'ascii')

def ERSTVAK_command(addr, cmd):
    command = "{0:03d}{1:1s}".format(addr, cmd).encode('ascii')
    command += ERSTVAK_CRC64(command)
    command += bytes('\r', 'ascii')
    return command

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
s.connect(("192.168.0.32", 501))
s.sendall(ERSTVAK_command(1, "c1"))
res = s.recv(1024)
print(res)

time.sleep(1)
s.sendall(ERSTVAK_command(1, "c000160"))
res = s.recv(1024)
print(res)
time.sleep(1)

s.sendall(ERSTVAK_command(1, "C1"))
res = s.recv(1024)

print(res)

s.close()