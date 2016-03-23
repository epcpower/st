#!/usr/bin/env python3.4

# TODO: get some docstrings in here!

import time

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class BusProxy:
    def __init__(self, bus=None):
        self.bus = bus

    def recv(self, timeout=None):
        if self.bus is not None:
            return self.bus.recv(timeout=timeout)
        elif timeout is not None:
            time.sleep(timeout)

    def send(self, message):
        if self.bus is not None:
            return self.bus.send(message=message)

    def shutdown(self):
        if self.bus is not None:
            return self.bus.shutdown()

    def flash(self):
        if self.bus is not None:
            return self.bus.flash()

    def set_bus(self, bus=None):
        self.bus = bus


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
