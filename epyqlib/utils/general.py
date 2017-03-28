import collections
import itertools
import math
import os
import threading
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


# https://docs.python.org/3/library/itertools.html
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def generate_ranges(ids):
    start = ids[0]

    for previous, next in pairwise(itertools.chain(ids, (None,))):
        if previous + 1 != next:
            yield (start, previous)

            start = next


@attr.s
class append_to_method:
    callable = attr.ib()
    name = attr.ib(default=None)

    def __attrs_post_init__(self):
        if self.name is None:
            self.name = self.callable.__name__

    def __call__(self, cls):
        old = getattr(cls, self.name, None)
        to_call = self.callable

        def f(s, *args, **kwargs):
            if old is not None:
                old(s, *args, **kwargs)

            to_call(s)

        setattr(cls, self.name, f)
        print('assigned {} to {}.{}'.format(f, cls.__name__, self.name))

        return cls


def spy(*ignore):
    """
    Make sure to ignore callables that are more than just their __call__
    because this will destroy everything else.
    """
    def inner(cls):
        class Spy(cls):
            def __getattribute__(self, name):
                attribute = super().__getattribute__(name)
                if hasattr(attribute, '__call__') and name not in ignore:

                    def mark(self, marker):
                        print('{marker} '
                              '>Thread Id 0x{thread_id:012x}< '
                              '{repr} '
                              '{marker} '
                              '{name}()'.format(
                                marker=marker,
                                repr='<{cls} object at 0x{id:012x}>'.format(
                                    cls=type(self).__bases__[0].__name__,
                                    id=id(self)
                                ),
                                name=name,
                                thread_id=threading.get_ident()
                        ))

                    def report(*args, **kwargs):
                        mark(self, ' +')
                        result = attribute(*args, **kwargs)
                        mark(self, '- ')

                        return result

                    return report
                else:
                    return attribute

        return Spy

    return inner
