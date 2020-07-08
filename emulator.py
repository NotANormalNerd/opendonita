#!/usr/bin/env python3

import socket
import select
import sys
import requests
import time
import struct
import json

# Emulates a Cecotec Conga 1490

def ask_http(uri, data = None):
    print(f"Asking {uri}")
    if data is None:
        d = requests.get(uri)
    else:
        d = requests.post(uri, data=data)
    d.encoding = 'latin1'
    print(d)
    print(d.text)
    print()

data = {"appKey":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "deviceId":"yyyyyyyyyyyyyyy",
    "deviceType":"1",
    "clearTime":"0"}
ask_http('http://127.0.0.1/baole-web/common/sumbitClearTime.do', data)

time.sleep(1)

data = {"appKey":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
"authCode":"zzzzz",
"deviceId":"yyyyyyyyyyyyyy",
"deviceType":"1",
"funDefine":"11101",
"nonce_str":"AAAAA",
"version": '{"wifi":"1.0.48","mcu":"3.9.1714(513)"}',
"sign":"SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS"}

ask_http('http://127.0.0.1/baole-web/common/getToken.do', data)

time.sleep(1)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1',20008))

counter = 1
received_data = b""
max_timeout = 15
timeout = max_timeout
timeout_mode2 = 2

def print_header(header):
    c = 0
    for a in header:
        v = hex(a)[2:]
        if len(v) < 2:
            v = "0" + v
        print(f" {v}", end = "")
        c += 1
        if (c%4 == 0) and (c < 20):
            print(" |", end="")


def send_packet(value1, value2, packet_id, value3, data = b""):
    global s
    global counter
    global timeout

    if packet_id is None:
        counter += 1
        packet_id = counter
    if isinstance(data, str):
        data = data.encode('latin1')
    header = bytearray(struct.pack("<LLLLL", 20 + len(data), value1, value2, packet_id, value3))
    s.send(header + data)
    print("Sending ", end="")
    print_header(header)
    print(f"\n{data}\n")
    timeout = max_timeout


def receive_packet():
    global s
    global received_data

    data = s.recv(65536)
    if len(data) == 0:
        print("Read error")
        sys.exit(0)
    received_data += data
    if len(received_data) < 20:
        return None, ""
    header = struct.unpack("<LLLLL", received_data[:20])
    if len(received_data) < header[0]:
        return None, ""
    data = received_data[20:header[0]].decode('latin1')
    print("Received", end="")
    print_header(received_data[:20])
    print(f"\n{data}\n")
    received_data = received_data[header[0]:]
    if len(data) == 0:
        return header, None
    else:
        return header, json.loads(data)

def compare_packet(header, length, v1, v2, sequence, v4):
    if (length is not None) and (length != header[0]):
        return False
    if (v1 is not None) and (v1 != header[1]):
        return False
    if (v2 is not None) and (v2 != header[2]):
        return False
    if (sequence is not None) and (sequence != header[3]):
        return False
    if (v4 is not None) and (v4 != header[4]):
        return False
    return True

def check_command(data, command):
    if data is None:
        return False
    if 'value' not in data:
        return False
    if 'transitCmd' not in data['value']:
        return False
    return data['value']['transitCmd'] == command

# mode 0: waiting for identification
# mode 1: idle
# mode 2: working
# mode 3: returning to base

mode = 0
counter_error = 0

send_packet(0x0010, 0x0001, None, 0x00, '{"version":"1.0","control":{"targetId":"0","targetType":"6","broadcast":"0"},"value":{"token":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","deviceId":"yyyyyyyyyyyyyy","appKey":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","deviceType":"1","authCode":"zzzzz","deviceIp":"192.168.18.3","devicePort":"8888"}}')

while True:
    l = select.select([s],[],[],1)
    if len(l[0]) == 0:
        timeout -= 1
        if timeout == 0:
            timeout = max_timeout
            send_packet(0x00c80100, 0x0001, None, 0x0003e7)
        if mode == 2:
            timeout_mode2 -= 1
            if timeout_mode2 == 0:
                timeout_mode2 = 2
                send_packet(0x014, 0x01, None, 0x00, '{"version": "1.0","control": {"targetId": "0","targetType": "6","broadcast": "0"},"value": {"noteCmd": "101","clearArea": "0","clearTime": "10","clearSign": "2020-06-24-01-31-41-2","clearModule": "11","isFinish": "1","chargerPos": "-1,-1","map": "AAAAAAAAZABk0vwAaoDXAGpA1wBqgNcAqNL8AA==","track": "AQAEADIxMzExMTEy"}}')
        counter_error += 1
        if counter_error == 5:
            send_packet(0x0016, 0x01, None, 0x00, '{"version":"1.0","control":{"targetId":"0","targetType":"6","broadcast":"0"},"value":{"noteCmd":"100","errorCode":"24"}}')
        continue

    timeout = max_timeout
    header, data = receive_packet()
    if header is None:
        continue
    if mode == 0:
        mode = 1
        send_packet(0x0018, 0x0001, None, 0x00,'{"version":"1.0","control": {"targetId":"0","targetType":"6","broadcast":"0"},"value": {"noteCmd":"102","workState":"6","workMode":"0","fan":"1","direction":"0","brush":"2","battery":"100","voice":"2","error":"0","standbyMode":"1","waterTank":"40","clearComponent":"0","waterMark":"0","version":"3.9.1714(513)","attract":"0","deviceIp":"192.168.18.14","devicePort":"8888","cleanGoon":"2"}}')
        continue

    if compare_packet(header, None, 0x00c800fa, 0x01090000, None, 0x00) and check_command(data, "100"):
        if mode == 1:
            mode = 2
            counter_error = 0
            timeout_mode2 = 2
            send_packet(0x00fa, 0x01, header[3], 0x00, '{"version":"1.0","control":{"targetId":"zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz","targetType":"3","broadcast":"0"},"value":{"noteCmd":"102","workState":"5","workMode":"0","fan":"2","direction":"0","brush":"2","battery":"100","voice":"2","error":"0","standbyMode":"1","waterTank":"40","clearComponent":"0","waterMark":"0","version":"3.11.416(513)","attract":"0","deviceIp":"192.168.18.3","devicePort":"8888","cleanGoon":"2"}}')
            send_packet(0x0018, 0x01, None, 0x00, '{"version":"1.0","control":{"targetId":"0","targetType":"6","broadcast":"0"},"value":{"noteCmd":"102","workState":"5","workMode":"0","fan":"2","direction":"0","brush":"2","battery":"100","voice":"2","error":"0","standbyMode":"1","waterTank":"40","clearComponent":"0","waterMark":"0","version":"3.11.416(513)","attract":"0","deviceIp":"192.168.18.3","devicePort":"8888","cleanGoon":"2"}}')
        continue

    if compare_packet(header, None, 0x00c800fa, 0x01090000, None, 0x00) and check_command(data, "102"):
        if mode == 2:
            mode = 1
            send_packet(0x00fa, 0x01, header[3], 0x00, '{"version":"1.0","control":{"targetId":"zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz","targetType":"3","broadcast":"0"},"value":{"noteCmd":"102","workState":"1","workMode":"11","fan":"2","direction":"0","brush":"2","battery":"100","voice":"2","error":"0","standbyMode":"1","waterTank":"40","clearComponent":"0","waterMark":"0","version":"3.11.416(513)","attract":"0","deviceIp":"192.168.18.3","devicePort":"8888","cleanGoon":"2"}}')
            send_packet(0x0018, 0x01, None, 0x00, '{"version":"1.0","control":{"targetId":"0","targetType":"6","broadcast":"0"},"value":{"noteCmd":"102","workState":"2","workMode":"0","fan":"2","direction":"0","brush":"2","battery":"100","voice":"2","error":"0","standbyMode":"1","waterTank":"40","clearComponent":"0","waterMark":"0","version":"3.11.416(513)","attract":"0","deviceIp":"192.168.18.3","devicePort":"8888","cleanGoon":"2"}}')
        continue


    if compare_packet(header, 0x14, 0x00c80111, 0x01080001, None, 0x03e7):
        continue
    if compare_packet(header, 0x3c, 0x00c80019, 0x01, None, 0x01):
        continue
    print("Unknown packet")
