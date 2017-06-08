import collections

import attr


def create_helpers(cls):
    lengths = cls.lengths()
    offsets = (sum(lengths[:i]) for i in range(len(lengths)))
    cls_offsets = cls(*offsets)
    cls_slices = cls(
        *(slice(o, o + l) for l, o in zip(lengths, attr.astuple(cls_offsets))))

    sf = '{{:0{}b}}'.format(sum(lengths))

    def unpack(n):
        sn = sf.format(n)
        return cls(*(int(sn[s], 2) for s in attr.astuple(cls_slices)))

    def pgn(id):
        strings = ('{:0{}b}'.format(n, l) for n, l, b in
                   zip(attr.astuple(id), lengths, cls.pgns()) if b)
        return int(''.join(strings), 2)

    def pack(id):
        strings = ('{:0{}b}'.format(n, l) for n, l in
                   zip(attr.astuple(id), lengths))
        return int(''.join(strings), 2)

    return unpack, pgn, pack


def add_helpers(cls):
    cls.unpack, cls.pgn, cls.pack = create_helpers(cls)

    return cls


class IncorrectFormat(Exception):
    pass


@add_helpers
@attr.s
class Id:
    priority = attr.ib(metadata={'length': 3, 'pgn': False})
    extended_data_page = attr.ib(metadata={'length': 1, 'pgn': True})
    data_page = attr.ib(metadata={'length': 1, 'pgn': True})
    pdu_format = attr.ib(metadata={'length': 8, 'pgn': True})
    pdu_specific = attr.ib(metadata={'length': 8, 'pgn': True})
    source_address = attr.ib(metadata={'length': 8, 'pgn': False})

    @classmethod
    def lengths(cls):
        return tuple(f.metadata['length'] for f in attr.fields(cls))

    @classmethod
    def offsets(cls):
        return tuple(
            sum(cls.lengths()[:i]) for i in range(len(attr.fields(cls))))

    @classmethod
    def slices(cls):
        return tuple(
            slice(o, o + l) for l, o in zip(cls.lengths(), cls.offsets()))

    @classmethod
    def pgns(cls):
        return tuple(f.metadata['pgn'] for f in attr.fields(cls))

    def is_proprietary_a(self):
        return all((
            self.extended_data_page == 0,
            self.data_page == 0,
            self.pdu_format == 239,
        ))

    def is_proprietary_a2(self):
        return all((
            self.extended_data_page == 0,
            self.data_page == 1,
            self.pdu_format == 239,
        ))

    def is_proprietary_b(self):
        return all((
            self.extended_data_page == 0,
            self.data_page == 0,
            self.pdu_format == 255,
        ))

    def is_iso15765_3(self):
        return all((
            self.extended_data_page == 1,
            self.data_page == 1,
        ))

    def is_pdu1(self):
        return 0 <= self.pdu_format <= 239

    def is_pdu2(self):
        return 240 <= self.pdu_format <= 255

    @property
    def destination_address(self):
        if not self.is_pdu1():
            raise IncorrectFormat(
                'Requested destination address for non-PDU1 identifer')

        return self.pdu_specific

    @destination_address.setter
    def destination_address(self, value):
        if not self.is_pdu1():
            raise IncorrectFormat(
                'Attempted to set destination address for non-PDU1 identifer')

        self.pdu_specific = value

    @property
    def group_extension(self):
        if not self.is_pdu2():
            raise IncorrectFormat(
                'Requested group extension for non-PDU2 identifer')

        return self.pdu_specific

    @group_extension.setter
    def group_extension(self, value):
        if not self.is_pdu2():
            raise IncorrectFormat(
                'Attempted to set group extension for non-PDU2 identifer')

        self.pdu_specific = value


def example():
    print(Id(*Id.lengths()))
    print(Id(*Id.offsets()))
    print(Id(*Id.slices()))

    iid = 0x0cffc2f6
    sid = '{:029b}'.format(iid)
    print(sid)
    print(' '.join(sid[s] for s in Id.slices()))
    id = Id(*(int(sid[s], 2) for s in Id.slices()))
    print(id)

    print(Id.unpack(iid))

    print()
    # grep 'ID=' .sym | sed 's/ID=\([0-9A-Fa-f]\+\)h.*/    0x\1,/'
    ids = [
        0x1DEFF741,
        0x0CEFF741,
        0x1DEF41F7,
        0x18FFD0F7,
        0x18FFD1F7,
        0x18FFD2F7,
        0x1CFFC0F7,
        0x0CFFCAF7,
        0x18FFC4F7,
        0x0CFFC3F7,
        0x18FFCBF7,
        0x0CFFC2F7,
        0x1CFFC7F7,
        0x1CFFCCF7,
        0x0CFFC1F7,
        0x18FFD3F7,
        0x18FFD4F7,
        0x1FFFFFF7,
        0x1FFFFFFF,
    ]

    for id in ids:
        cls_id = Id.unpack(id)
        print('PGN: 0x{pgn: 7X} {pgn: 7d} 0x{id:08x}: {cls}'.format(
            pgn=Id.pgn(cls_id), id=id, cls=cls_id))

    print()
    i_id = 247
    st_id = 65

    process_to_i = Id(priority=3, extended_data_page=0, data_page=0,
                      pdu_format=239, pdu_specific=i_id, source_address=st_id)
    setup_to_i = Id(priority=7, extended_data_page=0, data_page=1,
                    pdu_format=239, pdu_specific=i_id, source_address=st_id)
    process_from_i = Id(priority=3, extended_data_page=0, data_page=0,
                        pdu_format=239, pdu_specific=st_id, source_address=i_id)
    setup_from_i = Id(priority=7, extended_data_page=0, data_page=1,
                      pdu_format=239, pdu_specific=st_id, source_address=i_id)

    ids = collections.OrderedDict((
        ('process_to_i', process_to_i),
        ('setup_to_i', setup_to_i),
        ('process_from_i', process_from_i),
        ('setup_from_i', setup_from_i)
    ))

    print()
    for name, id in ids.items():
        raw_id = Id.pack(id)
        print(
        '{:>20s}: PGN: {: 7d} 0x{:08x} {}'.format(name, Id.pgn(id), raw_id, id))
