#!/usr/bin/env python3

# TODO: get some docstrings in here!

import epyqlib.canneo
import epyqlib.deviceextension

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class DeviceExtension(epyqlib.deviceextension.DeviceExtension):
    def post(self):
        power_ring = self.device.loaded_uis['example_hmi_power_ring.ui']
        self.vac_line_bar = power_ring.vac_line_bar
        self.vac_reference = power_ring.vac_reference
        self.vac_reference.signal_object.value_changed.connect(
            self.update_line_bar)

    def update_line_bar(self, value):
        self.vac_line_bar.reference_value = value
        min_max = [0.9 * value, 1.1 * value]
        self.vac_line_bar.minimum = min(min_max)
        self.vac_line_bar.maximum = max(min_max)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
