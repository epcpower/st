#!/usr/bin/env python3

#TODO: """DocString if there is one"""

# See file COPYING in this source tree
__copyright__ = ('\n'.join([
    'Copyright 2010, Kunal Anand',
    # https://gist.github.com/327585

    'Copyright 2011, Tennessee Carmel-Veilleux',
    # http://www.tentech.ca/2011/05/stream-tee-in-python-saving-stdout-to-file-while-keeping-the-console-alive/

    'Copyright 2016, EPC Power Corp.'
    # Adjusted to take a list of principals
]))
__license__ = 'GPLv2+'

class Tee:
    def __init__(self, principals):
        if len(principals) < 1:
            # TODO: be more specific with exception selection
            raise Exception('Tee requires at least one principal')

        self.principals = principals
        self.__missing_method_name = None # Hack!

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)

    def __getattr__(self, name):
        self.__missing_method_name = name # Could also be a property
        return getattr(self, '__methodmissing__')

    def __methodmissing__(self, *args, **kwargs):
        call = getattr(self.principals[0], self.__missing_method_name)
        result = call(*args, **kwargs)

        for principal in self.principals[1:]:
            call = getattr(principal, self.__missing_method_name)
            call(*args, **kwargs)

        return result


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
