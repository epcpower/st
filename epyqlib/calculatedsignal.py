import epyqlib.canneo

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class Signal(epyqlib.canneo.Signal):
    def __init__(self, *args, **kwargs):
        epyqlib.canneo.Signal.__init__(self, *args, **kwargs)

        self.sources = {}

    def add_source(self, source):
        source.value_changed.connect(self.source_changed)
        self.sources[(source.frame.name, source.name)] = source.human_value

    @pyqtSlot(float)
    def source_changed(self, value):
        self.calculate()


class MyCalcedSignal(epyqlib.calculatedsignal.CalculatedSignal)

import math
def calcIt(sources):
    return math.round(sources['existing.Signal'] / 1000)

calcedSig = epyqlib.calculatedsignals.Signal(f=calcIt)

class Frame(epyqlib.canneo.Frame):
    def __init__(self, *args, **kwargs):
        epyqlib.canneo.Frame.__init__(self, *args, **kwargs)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
