import sys

__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


def errbackhook(error):
    sys.excepthook(message=str(error))


def detour_result(result, f, *args, **kwargs):
    f(*args, **kwargs)

    return result
