#!/usr/bin/env python3

# TODO: get some docstrings in here!

import sunspec.core.client as client
import sys

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(args=None):
    d = client.SunSpecClientDevice(client.RTU, 1, '/dev/ttymod')
    print(d.common)
    d.common.read()
    print(d.common)
    for model in [getattr(d, model) for model in d.models]:
        model.read()
        print('  -  -  -  Model {}'.format(model.name))
        print(model)
        print()


if __name__ == '__main__':
    sys.exit(main())
