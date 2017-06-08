#!/usr/bin/env python3

# TODO: get some docstrings in here!

# import can

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def referenced_files(raw_dict):
    return ()


class DeviceExtension:
    def __init__(self, device):
        self.device = device

    def post(self):
        pass


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
