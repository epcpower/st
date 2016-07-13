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

        object.__setattr__(self, '_length', len(self.__dict__))

        invalid_parameters = set(kwargs.keys()) - set(self.__dict__.keys())
        if len(invalid_parameters):
            raise ValueError('Invalid parameter{} passed: {}'.format(
                's' if len(invalid_parameters) > 1 else '',
                ', '.join(invalid_parameters)))

    @classmethod
    def __len__(cls):
        return len(cls._members)

    @classmethod
    def indexes(cls):
        return cls(**dict(zip(cls._members, range(len(cls._members)))))

    @classmethod
    def fill(cls, value):
        return cls(**dict(zip(cls._members, [value] * len(cls._members))))

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, index):
        for attribute in self.__class__._members:
            if index == getattr(self.__class__.indexes, attribute):
                return getattr(self, attribute)

        raise IndexError('column index out of range')

    def __getattr__(self, name, value):
        if name in self._members:
            object.__getattr__(self, name, value)
        else:
            raise TypeError("Attempted to get attribute {}"
                            .format(name))

    def __setattr__(self, name, value):
        if name in self._members:
            object.__setattr__(self, name, value)
        else:
            raise TypeError("Attempted to set attribute {}"
                            .format(name))


if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
