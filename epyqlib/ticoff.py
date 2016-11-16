#!/usr/bin/env python
"""
Read TI COFF file into a python object
"""


from __future__ import print_function

from builtins import bytes, object, range
from array import array
from collections import namedtuple
from optparse import OptionParser
from struct import unpack, calcsize


# See file COPYING in this source tree
# See file ticoff.asi_license.txt in this source tree
__copyright__ = ('\n'.join([
    'Copyright 2011 "Eliot Blennerhassett" <eblennerhassett@audioscience.com>',
    # https://gist.github.com/eliotb/1073231

    'Copyright 2016, EPC Power Corp.'
    # Added Python3 support and a few tweaks
]))
__license__ = 'GPLv2+'


def read_struct(file, format):
    '''read struct data formatted according to format'''
    datalen = calcsize(format)
    data = file.read(datalen)
    if len(data) != datalen:
        raise EOFError
    ret = unpack(format, data)
    if len(ret) < 2:
        ret = ret[0]
    return ret


def read_cstr(file):
    '''read zero terminated c string from file'''
    output = ""
    while True:
        char = file.read(1)
        if len(char) == 0:
            raise RuntimeError ("EOF while reading cstr")
        char = chr(bytes(char)[0])
        if char == '\0':
            break
        output += char
    return output

# From spraao8.pdf table 7
class Section(namedtuple('Section',
    'name, virt_size, virt_addr, raw_data_size, raw_data_ptr, relocation_ptr,' +
    'linenum_ptr, linenum_count, reloc_count, flags, reserved, mem_page, data')):

    __slots__ = () # prevent creation of instance dictionaries
    section_fmt = '<8s9L2H'
    section_flags = [
        (0x00000001, 'STYP_DSECT'), (0x00000002, 'STYP_NOLOAD'),
        (0x00000004, 'STYP_GROUPED'), (0x00000008, 'STYP_PAD'),
        (0x00000010, 'STYP_COPY'), (0x00000020, 'STYP_TEXT'),
        (0x00000040, 'STYP_DATA'), (0x00000080, 'STYP_BSS'),
        (0x00000100, 'STYP_100'), (0x00000200, 'STYP_200'),
        (0x00000200, 'STYP_400'), (0x00000800, 'STYP_800'),
        (0x00001000, 'STYP_BLOCK'), (0x00002000, 'STYP_PASS'),
        (0x00004000, 'STYP_CLINK'),(0x00008000, 'STYP_VECTOR'),
        (0x00010000, 'STYP_PADDED'),
    ]

    @property
    def is_zero_filled(self):
        return (self.data is not None) and not any([d != '\0' for d in self.data])

    def fill_value(self):
        if self.data is  None:
            return None

        if len(self.data) % 4:
            return None # only handle 32 bit fill

        a = array('I', self.data)
        if all([d == a[0] for d in a]):
            return a[0]
        else:
            return None

    @property
    def is_loadable(self):
        return not(self.flags & 0x00000010 or self.data is None)

    def __str__(self):
        s = 'Section %s' % self.name
        if self.flags:
            s += ' Flags ='
            for f in Section.section_flags:
                if self.flags & f[0]:
                    s = s + ' ' + f[1]
        for fv in self._asdict().items():
            if fv[0] == 'data' or fv[0] == 'name': continue
            s = s + '\n\t%s = 0x%X' % fv
        return s

class Coff(object):
    Header = namedtuple('Header',
        'machine_type, section_count, time_date, symbol_table_ptr, ' +
        'symbol_count, optional_header_size, flags, target_id')
    header_fmt = '<2H3L3H'

    OptionalHeader = namedtuple('OptionalHeader',
        'magic, version, exe_size, init_data_size, uninit_data_size, entry_point, exe_start, init_start')
    optheader_fmt = '<2H6L'

    def __init__(self, filename=None):
        self.header = None
        self.optheader = None
        self.sections = []
        if filename is not None:
            self.from_file(filename)

    def from_file(self, name):
        with open(name, 'rb') as f:
            self.from_stream(f)

    def from_stream(self, f):
        self.header = self.Header(*read_struct(f, self.header_fmt))
        self.optheader = self.OptionalHeader(*read_struct(f, self.optheader_fmt))
        self.sections = []
        for i in range(self.header.section_count):
            section = Section(*read_struct(f, Section.section_fmt), data=None)
            section = section._replace(name=self.symname(f, section.name))
            if section.raw_data_ptr and section.raw_data_size:
                here = f.tell()
                f.seek(section.raw_data_ptr)
                # TODO: `2 *` is hard coded to handle the 2-bytes per
                #       address scenario.  This should obviously be
                #       detected somehow, unless it is always correct.
                data = bytes(f.read(2 * section.raw_data_size))
                f.seek(here)
                section = section._replace(data=data)
            self.sections.append(section)

        self.entry_point = self.optheader.entry_point
        self.sections.sort(key=lambda s: s.virt_addr)

    @property
    def loadable_sections(self):
        return [s for s in self.sections if s.is_loadable]

    def string_table_entry (self, f, offset):
        here = f.tell()
        seek = self.header.symbol_table_ptr + self.header.symbol_count * 18 + offset
        f.seek(seek)
        s = read_cstr(f)
        f.seek(here)
        return s

    def symname(self, f, value):
        parts = unpack("<2L", value)
        if parts[0] == 0:
            return self.string_table_entry(f, parts[1])
        else:
            return str(value.decode('ascii').rstrip('\0'))

    def __str__(self):
        s = 'TI coff file'
        if self.header is not None:
            for fv in self.header._asdict().items():
                s = s + '\n\t%s = 0x%X' % fv
        if self.optheader is not None:
            s += '\nOptional Header'
            for fv in self.optheader._asdict().items():
                s = s + '\n\t%s = 0x%X' % fv
        return s

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--dump_data",
                      action="store_true", dest="dump", default=False,
                      help="dump section data")

    options, args = parser.parse_args()

    c = Coff(args[0])
    print(c)

    for section in c.sections:
        print(section)
        if section.data is not None and options.dump:
            print(repr(section))

