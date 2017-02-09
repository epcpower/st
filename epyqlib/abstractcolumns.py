#!/usr/bin/env python3

#TODO: """DocString if there is one"""

import functools

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

    @classmethod
    def as_title_case(cls):
        return cls(**dict(zip(cls._members, (s.title() for s in cls._members))))

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    @functools.lru_cache(maxsize=None)
    def index_from_attribute(self, index):
        for attribute in self.__class__._members:
            if index == getattr(self.__class__.indexes, attribute):
                return attribute

        raise IndexError('column index out of range')

    def __getitem__(self, index):
        if index < 0:
            index += len(self)
        return getattr(self, self.index_from_attribute(index))

    def __setitem__(self, index, value):
        if index < 0:
            index += len(self)
        return setattr(self, self.index_from_attribute(index), value)

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
