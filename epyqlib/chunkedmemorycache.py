import attr
import bisect
import collections


class ChunkExistsError(Exception):
    pass


class ChunkNotFoundError(Exception):
    pass


class ByteLengthError(Exception):
    pass


@attr.s
class Subscriber:
    callback = attr.ib()
    reference = attr.ib()


@attr.s
class Cache:
    _chunks = attr.ib(init=False, default=attr.Factory(list))
    _subscribers = attr.ib(init=False, default=attr.Factory(dict))
    _bits_per_byte = attr.ib(default=8)

    def __attrs_post_init__(self):
        self.address_to_chunks = collections.defaultdict(set)

    def __repr__(self):
        return object.__repr__(self)

    def __str__(self):
        return object.__str__(self)

    def add(self, chunk):
        if any(chunk is c for c in self._chunks):
            raise ChunkExistsError(chunk)

        bisect.insort_left(self._chunks, chunk)
        self._subscribers[chunk] = set()

        for address in chunk.addresses():
            self.address_to_chunks[address].add(chunk)

    def subscribe(self, subscriber, chunk, reference=None):
        if not any(chunk is c for c in self._chunks):
            raise ChunkNotFoundError(chunk)

        s = Subscriber(callback=subscriber, reference=reference)
        self._subscribers[chunk].add(s)

    # def unsubscribe(self, subscriber, chunk, reference=None):
    #     to_discard = []
    #     for subscriber in self._subscribers[chunk]:
    #         if
    #         .discard(subscriber)

    def unsubscribe_by_reference(self, reference, chunk=None):
        chunks = (self._subscribers.items()
                  if chunk is None
                  else [chunk])

        to_discard = set()
        for chunk, subscribers in chunks:
            for subscriber in subscribers:
                # TODO: perhaps should be `is` not `==`?
                if subscriber.reference == reference:
                    to_discard.add(subscriber)

            self._subscribers[chunk] -= to_discard

    def unsubscribe_all(self, *chunks):
        if len(chunks) == 0:
            chunks = self._chunks

        for chunk in chunks:
            self._subscribers[chunk] = set()

    def update(self, update_chunk):

        intersected_chunks = set()
        for address in update_chunk.addresses():
            intersected_chunks |= self.address_to_chunks[address]

        for chunk in intersected_chunks:
            chunk.update(update_chunk)

            for subscriber in self._subscribers[chunk]:
                subscriber.callback(chunk._bytes)

    def chunk_from_variable(self, variable, reference=None):
        data = bytearray([0] * variable.type.bytes * (self._bits_per_byte // 8))
        if reference is None:
            reference = variable
        return Chunk(address=variable.address,
                     bytes=data,
                     bits_per_byte=self._bits_per_byte,
                     reference=reference)

    def new_chunk(self, address, bytes, reference=None):
        return Chunk(address=address,
                     bytes=bytes,
                     bits_per_byte=self._bits_per_byte,
                     reference=reference)

    def contiguous_chunks(self):
        chunks = []

        addresses = set()
        for chunk in self._chunks:
            addresses.update(chunk._address + offset
                             for offset in range(len(chunk._bytes) //
                                                 (self._bits_per_byte // 8)))

        addresses = sorted(list(addresses))

        addresses.append(None)

        if len(addresses) > 0:
            start = None
            for address in addresses:
                if start is None:
                    start = address
                    end = start
                elif address == end + 1:
                    end = address
                else:
                    chunk = self.new_chunk(
                        address=start,
                        bytes=b'\x00'
                              * (end - start + 1)
                              * (self._bits_per_byte // 8)
                    )
                    chunks.append(chunk)
                    start = address
                    end = start

        return chunks

@attr.s(hash=False)
class Chunk:
    _address = attr.ib()
    _bytes = attr.ib(convert=bytearray)
    _bits_per_byte = attr.ib(default=8)
    reference = attr.ib(cmp=False, default=None)

    def __len__(self):
        # TODO: maybe...
        #       return len(self._bytes) // (self._bits_per_byte // 8)
        return len(self._bytes)

    def addresses(self):
        start, end = self.bounds()
        return range(start, end)

    def bounds(self):
        # TODO: is this returning one too long?
        return (self._address,
                self._address + len(self) // (self._bits_per_byte // 8))

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self._address < other._address or (
            self._address == other._address and len(self) < len(other)
        ) 

    def set_bytes(self, new_bytes):
        if len(new_bytes) != len(self):
            raise ByteLengthError("A chunk's byte array may not change length")

        self._bytes = bytearray(new_bytes)

    def overlaps_address_length(self, address, length):
        # TODO: CAMPid 4317784316796754167954114314396
        my_bounds = self.bounds()
        address_bounds = (address, address + length)

        start = max(my_bounds[0], address_bounds[0])
        end = min(my_bounds[1], address_bounds[1])

        _length = end - start

        return _length >= 1

    def update(self, chunk):
        # TODO: CAMPid 4317784316796754167954114314396
        my_bounds = self.bounds()
        chunk_bounds = chunk.bounds()

        start = max(my_bounds[0], chunk_bounds[0])
        end = min(my_bounds[1], chunk_bounds[1])

        _length = end - start

        if _length >= 1:
            slice_start = (start - self._address) * (self._bits_per_byte // 8)
            slice_end = slice_start + (_length * self._bits_per_byte // 8)
            self_slice = slice(slice_start, slice_end)

            slice_start = (start - chunk._address) * (self._bits_per_byte // 8)
            slice_end = slice_start + (_length * self._bits_per_byte // 8)
            chunk_slice = slice(slice_start, slice_end)

            self._bytes[self_slice] = chunk._bytes[chunk_slice]

            return True
        
        return False


def testit(filename):
    import epyqlib.cmemoryparser
    import functools
    import random

    names, variables, bits_per_byte = epyqlib.cmemoryparser.process_file(filename)

    cache = Cache(bits_per_byte=bits_per_byte)

    for variable in variables:
        chunk = cache.chunk_from_variable(variable)
        cache.add(chunk)
        partial = functools.partial(testit_updated,
                                    variable)
        cache.subscribe(subscriber=partial, chunk=chunk)
        print('added {}: {}'.format(variable.name, chunk))

    chunk = cache.chunk_from_variable(names['Vholdoff'])
    new_bytes = [random.randint(0, 255) for _ in range(len(chunk))]
    chunk.set_bytes(new_bytes)
    print('sending update: {}'.format(chunk))
    cache.update(chunk)

    testStruct12 = names['testStruct12']
    TestStruct12 = epyqlib.cmemoryparser.base_type(testStruct12)
    members = ['sA', 'm10']
    member, offset = TestStruct12.member_and_offset(members)
    def all_set_byte(): return 255
    def random_byte(): return random.randint(0, 255)
    chunk = cache.new_chunk(
        address=testStruct12.address + offset,
        bytes=[random_byte() for _ in
               range(member.bytes * (bits_per_byte // 8))]
    )
    print('sending update: {}'.format(chunk))
    cache.update(chunk)


def testit_updated(variable, bytes):
    print('{} was updated: {} -> {}'.format(variable.name, bytes, variable.unpack(bytes)))


if __name__ == '__main__':
    import sys

    sys.exit(testit(sys.argv[1]))
