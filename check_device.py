#!/usr/bin/env python3

# TODO: get some docstrings in here!

import epyqlib.device

from PyQt5.QtWidgets import QApplication

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(args=None):
    # TODO: CAMPid 9757656124812312388543272342377
    app = QApplication(sys.argv)
    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPyQ')

    if args is None:
        import argparse

        parser = argparse.ArgumentParser()

        parser.add_argument('devices', nargs='+')
        args = parser.parse_args()

    for device_path in args.devices:
        print(' - - - - - - Checking {}'.format(device_path))
        epyqlib.device.Device(file=device_path)


if __name__ == '__main__':
    import sys
    sys.exit(main())
