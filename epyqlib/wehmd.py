#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import enum
import struct
import socket

from ctypes import *


# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: traceability?
WEHMD_API_SOCKET = "/var/run/wehmd_api"


class Wehmd:
    def __init__(self):
        self.socket = socket.socket(family=socket.AF_UNIX,
                                    type=socket.SOCK_STREAM)
        self.socket.connect(WEHMD_API_SOCKET)

    def read_boot_mode(self):
        message = wehmd_msg_t()
        message.command = int(CommandType.WEHMD_CMD_GET_EE_BOOT_MODE)
        message.data.bootMode = 0

        self.send(message)
        response = self.receive()
        return wehmd_msg_t.from_buffer_copy(response)

    def write_boot_mode(self, value):
        message = wehmd_msg_t()
        message.command = int(CommandType.WEHMD_CMD_SET_EE_BOOT_MODE)
        message.data.bootMode = value

        self.send(message)
        response = self.receive()
        return wehmd_msg_t.from_buffer_copy(response)

    def send(self, message):
        raw = (c_char * sizeof(message))()
        memmove(raw, byref(message), sizeof(message))

        total_sent = 0
        while total_sent < len(raw):
            sent = self.socket.send(raw[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent = total_sent + sent

    def receive(self):
        chunks = []
        bytes_received = 0
        while bytes_received < sizeof(wehmd_msg_t):
            chunk = self.socket.recv(min(sizeof(wehmd_msg_t) - bytes_received, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_received = bytes_received + len(chunk)
        return b''.join(chunks)


CommandType = enum.IntEnum('CommandType', '''
    WEHMD_CMD_GET_OTC
    WEHMD_CMD_OTC
    WEHMD_CMD_GET_EE_PRODUCT_TYPE
    WEHMD_CMD_EE_PRODUCT_TYPE
    WEHMD_CMD_GET_EE_PRODUCT_VARIANT
    WEHMD_CMD_EE_PRODUCT_VARIANT
    WEHMD_CMD_GET_EE_BOARD_REVISION
    WEHMD_CMD_EE_BOARD_REVISION
    WEHMD_CMD_GET_EE_BOARD_NAME
    WEHMD_CMD_EE_BOARD_NAME
    WEHMD_CMD_GET_EE_PART_NUMBER
    WEHMD_CMD_EE_PART_NUMBER
    WEHMD_CMD_GET_EE_SERIAL_NUMBER
    WEHMD_CMD_EE_SERIAL_NUMBER
    WEHMD_CMD_GET_EE_BOOT_MODE
    WEHMD_CMD_EE_BOOT_MODE
    WEHMD_CMD_GET_EE_UNIQUE_RELEASE_ID
    WEHMD_CMD_EE_UNIQUE_RELEASE_ID
    WEHMD_CMD_GET_EE_DELETE_DIAG
    WEHMD_CMD_EE_DELETE_DIAG
    WEHMD_CMD_GET_EE_CONSOLE_MODE
    WEHMD_CMD_EE_CONSOLE_MODE
    WEHMD_CMD_GET_API_VERSION
    WEHMD_CMD_API_VERSION
    WEHMD_CMD_ERROR
    WEHMD_CMD_SET_EE_CONSOLE_MODE
    WEHMD_CMD_GET_EE_DISPLAY_BRIGHTNESS
    WEHMD_CMD_SET_EE_DISPLAY_BRIGHTNESS
    WEHMD_CMD_EE_DISPLAY_BRIGHTNESS
    WEHMD_CMD_GET_EE_KEYPAD_BRIGHTNESS
    WEHMD_CMD_SET_EE_KEYPAD_BRIGHTNESS
    WEHMD_CMD_EE_KEYPAD_BRIGHTNESS
    WEHMD_CMD_SET_EE_BOOT_MODE
    WEHMD_CMD_SET_EE_RAM_TEST
    WEHMD_CMD_GET_EE_RAM_TEST
    WEHMD_CMD_EE_RAM_TEST
    WEHMD_CMD_GET_EE_KEYPAD_COLOR
    WEHMD_CMD_SET_EE_KEYPAD_COLOR
    WEHMD_CMD_EE_KEYPAD_COLOR
''',
    start=0
)


wehmd_cmd_t = c_uint
wehmd_err_type_t = c_uint


class wehmd_error_t(Structure):
    _fields_ = [
        ('command', wehmd_cmd_t),
        ('errorType', wehmd_err_type_t)
    ]


class wehmd_msg_data_t(Union):
    _fields_ = [
        ('otc', c_uint),
        ('productType', c_ubyte),
        ('productVariant', c_ubyte),
        ('boardRevision', c_ubyte),
        ('boardName', c_char * 31),
        ('partNumber', c_char * 21),
        ('serialNumber', c_char * 21),
        ('bootMode', c_ubyte),
        ('uniqueReleaseID', c_uint),
        ('deleteDiag', c_ubyte),
        ('consoleMode', c_ubyte),
        ('apiVersion', c_uint),
        ('displayBrightness', c_ubyte),
        ('keypadBrightness', c_ubyte),
        ('keypadColor', c_uint),
        ('ramTest', c_ubyte),
        ('error', wehmd_error_t)
    ]


class wehmd_msg_t(Structure):
    _fields_ = [
        ('command', wehmd_cmd_t),
        ('data', wehmd_msg_data_t)
    ]


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
