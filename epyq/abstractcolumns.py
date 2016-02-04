#!/usr/bin/env python3

#TODO: """DocString if there is one"""

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


class AbstractColumns:
    def __init__(self, **kwargs):
        for member in self._members:
            try:
                value = kwargs[member]
            except KeyError:
                value = None
            finally:
                setattr(self, member, value)

        #TODO exception for args not in members
        self._length = len(self.__dict__)

    @classmethod
    def __len__(cls):
        return len(cls._members)

    @classmethod
    def indexes(cls):
        return cls(**dict(zip(cls._members, range(len(cls._members)))))

    @classmethod
    def fill(cls, value):
        return cls(**dict(zip(cls._members, [value] * len(cls._members))))

    def __getitem__(self, index):
        for attribute in self.__class__._members:
            if index == getattr(self.__class__.indexes, attribute):
                return getattr(self, attribute)

        raise IndexError('column index out of range')


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
