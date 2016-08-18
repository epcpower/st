#!/usr/bin/env python3

# TODO: get some docstrings in here!

import serial.tools.list_ports
import sunspec.core.client as client
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(args=None):
    for port in serial.tools.list_ports.comports():
        print(port)

    device = client.SunSpecClientDevice(client.RTU, 1, '/dev/ttymod', max_count=14)
    print(device.common)
    device.common.read()
    print(device.common)
    for model in [getattr(device, model) for model in device.models]:
        model.read()
        print('  -  -  -  Model {}'.format(model.name))
        print(model)
        print()

    for model in [getattr(device, name) for name in device.models]:
        model.read()
        for name, point in [(name, getattr(model, name)) for name in model.points]:
            print('{}-{}: {}'.format(model.name, name, point))

if __name__ == '__main__':
    sys.exit(main())
