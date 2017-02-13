import collections
import itertools
import math
import os
import time
import zipfile

import attr

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@attr.s
class AverageValueRate:
    _seconds = attr.ib(convert=float)
    _deque = attr.ib(default=attr.Factory(collections.deque))

    @attr.s
    class Event:
        time = attr.ib()
        value = attr.ib()
        delta = attr.ib()

    def add(self, value):
        now = time.monotonic()

        if len(self._deque) > 0:
            delta = now - self._deque[-1].time

            cutoff_time = now - self._seconds

            while self._deque[0].time < cutoff_time:
                self._deque.popleft()
        else:
            delta = 0

        event = self.Event(time=now, value=value, delta=delta)
        self._deque.append(event)

    def rate(self):
        if len(self._deque) > 0:
            dv = self._deque[-1].value - self._deque[0].value
            dt = self._deque[-1].time - self._deque[0].time
        else:
            dv = -1
            dt = 0

        if dv <= 0:
            return 0
        elif dt == 0:
            return math.inf

        return dv / dt

    def remaining_time(self, final_value):
        rate = self.rate()
        if rate <= 0:
            return math.inf
        else:
            return (final_value - self._deque[-1].value) / rate


def write_device_to_zip(zip_path, epc_dir, referenced_files, code=None,
                        sha=None, checkout_dir=None):
    # TODO: stdlib zipfile can't create an encrypted .zip
    #       make a good solution that will...
    with zipfile.ZipFile(file=zip_path, mode='w') as zip:
        for device_path in referenced_files:
            filename = os.path.join(epc_dir, device_path)
            zip.write(filename=filename,
                      arcname=os.path.relpath(filename, start=epc_dir))

        if sha is not None:
            sha_file_name = 'sha'
            sha_file_path = os.path.join(checkout_dir, sha_file_name)
            with open(sha_file_path, 'w') as sha_file:
                sha_file.write(sha + '\n')
            zip.write(
                filename=sha_file_path,
                arcname=sha_file_name
            )


# https://docs.python.org/3/library/itertools.html
def pairwise(iterable):
    's -> (s0,s1), (s1,s2), (s2, s3), ...'
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def generate_ranges(ids):
    start = ids[0]

    for previous, next in pairwise(itertools.chain(ids, (None,))):
        if previous + 1 != next:
            yield (start, previous)

            start = next


def filler_attribute():
    return attr.ib(
        default='',
        init=False,
        metadata={
            'editable': False,
            'to_file': False
        }
    )


class indexable_attrs:
    def __init__(self, ignore=lambda a: not a.name.startswith('_'),
                 convert_on_set=False):
        self.ignore = ignore
        self.convert_on_set = convert_on_set

    def __call__(self, cls):
        ignore = self.ignore
        convert_on_set = self.convert_on_set

        if hasattr(cls, '__attrs_post_init__'):
            old = cls.__attrs_post_init__
        else:
            old = None

        def __attrs_post_init__(self, *args, **kwargs):
            if old is not None:
                old(self, *args, **kwargs)

            self.public_fields = tuple(a for a in attr.fields(type(self))
                                       if ignore(a))

        def __getitem__(self, index):
            return getattr(self, self.public_fields[index].name)

        def __setitem__(self, index, value):
            attribute = self.public_fields[index]

            if convert_on_set and attribute.convert is not None:
                value = attribute.convert(value)

            return setattr(self,
                           attribute.name,
                           value)

        def __iter__(self):
            return (getattr(self, a.name) for a in self.public_fields)

        methods = (__getitem__, __setitem__, __iter__)

        for name in methods:
            if hasattr(cls, name.__name__):
                raise Exception(
                    'Unable to make indexable, {} already defined'.format(
                        name.__name__))

        for name in methods:
            setattr(cls, name.__name__, name)

        cls.__attrs_post_init__ = __attrs_post_init__

        return cls
