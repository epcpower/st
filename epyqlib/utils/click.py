import functools
import logging

import click

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def verbose_option(f):
    @click.option('-v', count=True)
    @functools.wraps(f)
    def d(*args, v, **kwargs):
        level = logging.getLogger().getEffectiveLevel()
        step = logging.INFO - logging.DEBUG
        level -= v * step

        logging.getLogger().setLevel(level)

        f(*args, **kwargs)

    return d
