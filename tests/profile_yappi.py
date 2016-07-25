# http://stackoverflow.com/a/32458998/228539
"""Replace python thread identifier by TID."""
# Imports
import threading, ctypes
# Define get tid function
def gettid():
    """Get TID as displayed by htop."""
    libc = 'libc.so.6'
    for cmd in (186, 224, 178):
        tid = ctypes.CDLL(libc).syscall(cmd)
        if tid != -1:
            return tid


import yappi
import epyq.__main__
import os

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


class Bunch:
    # http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991

    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def main():
    print('Main TID: {}'.format(gettid()))
    args = Bunch(channel=None,
                 devices=[],
                 generate=False,
                 ui='main.ui')
    yappi.start()
    exit_value = epyq.__main__.main(args=args)
    yappi.stop()
    yappi.get_func_stats().save('yappi.stats', type='pstat')
    yappi.get_thread_stats().print_all()
    return exit_value

if __name__ == '__main__':
    import sys
    sys.exit(main())
