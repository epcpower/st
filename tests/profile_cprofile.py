import cProfile
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
    pr = cProfile.Profile()
    can_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'AFE_CAN_ID247_FACTORY.sym')
    args = Bunch(can=can_file, generate=False)
    pr.enable()
    exit_value = epyq.__main__.main(args=args)
    pr.disable()
    pr.dump_stats('cprofile.stats')
    return exit_value

if __name__ == '__main__':
    import sys
    sys.exit(main())
