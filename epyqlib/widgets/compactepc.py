#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import epyqlib.widgets.epc

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class CompactEpc(epyqlib.widgets.epc.Epc):
    def __init__(self, parent=None, in_designer=False):
        epyqlib.widgets.epc.Epc.__init__(self,
                                      parent=parent,
                                      ui_file='compactepc.ui',
                                      in_designer=in_designer)


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
