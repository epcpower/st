#-------------------------------------------------------------------------------
# elftools example: dwarf_die_tree.py
#
# In the .debug_info section, Dwarf Information Entries (DIEs) form a tree.
# pyelftools provides easy access to this tree, as demonstrated here.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

import collections
from elftools.dwarf.dwarfinfo import DebugSectionDescriptor
from elftools.dwarf.descriptions import describe_attr_value
import elftools.common.exceptions
import io
import os
import epyqlib.ticoff
import traceback

import attr
import bitstruct
import enum
import itertools
import textwrap

import epyqlib.twisted.cancalibrationprotocol as ccp

bits_per_byte = 16

@enum.unique
class TypeFormats(enum.Enum):
    # http://www.dwarfstd.org/doc/Dwarf3.doc
    address = 0x01
    boolean = 0x02
    complex_float = 0x03
    float = 0x04
    signed = 0x05
    signed_char = 0x06
    unsigned = 0x07
    unsigned_char = 0x08
    imaginary_float = 0x09
    packed_decimal = 0x0a
    numeric_string = 0x0b
    edited = 0x0c
    signed_fixed = 0x0d
    unsigned_fixed = 0x0e
    decimal_float = 0x0f
    lo_user = 0x80
    hi_user = 0xff

    def is_integer(self):
        return self.is_signed_integer() or self.is_unsigned_integer()

    def is_signed_integer(self):
        return self in [TypeFormats.signed, TypeFormats.signed_char]

    def is_unsigned_integer(self):
        return self in [TypeFormats.unsigned, TypeFormats.unsigned_char]

    def is_floating_point(self):
        return self in [TypeFormats.float]


class BytesProxy:
    @property
    def bytes(self):
        return self.type.bytes


def bytearray_to_bits(data):
    return ''.join(['{:08b}'.format(b) for b in data])


@attr.s
class Type:
    name = attr.ib()
    bytes = attr.ib()
    format = attr.ib()

    # def format_string(self):
    #     if self.format.is_integer():
    #         if self.format.is_unsigned_integer():
    #             type = 'u'
    #         else:
    #             type = 's'
    #     elif self.format.is_floating_point():
    #         # TODO: CAMPid 097897541967932453154321546542175421549
    #
    #         # note that this is hardcoded for two bytes/address fudge
    #         types = {
    #             2: 'f',
    #             4: 'd'
    #         }
    #         try:
    #             type = types[self.bytes]
    #         except KeyError:
    #             raise Exception(
    #                 'float type only supports lengths in [{}]'.
    #                 format(', '.join([str(t) for t in types.keys()]))
    #             )
    #     else:
    #         raise Exception('Unsupported type format: {}'.format(self.type))
    #
    #     return '{}{}{}'.format('>', type, self.bytes * bits_per_byte)

    def unpack(self, data):
        if isinstance(data, bytearray):
            bits = bytearray_to_bits(data)
        else:
            bits = data

        total_bit_count = self.bytes * bits_per_byte

        # TODO: the % seems fishy
        if self.bytes > 1 and len(bits) % bits_per_byte == 0:
            # TODO: CAMPid 08793287728743824372437983526631513679
            bits = ''.join(itertools.chain(*reversed(list(
                grouper(bits, bits_per_byte)))))

        if self.format.is_integer():
            if self.format.is_unsigned_integer():
                pad = '0'
                type = 'u'
            else:
                pad = bits[-1]
                type = 's'

            return bitstruct.unpack('>' + type + str(total_bit_count),
                                    int(bits, 2).to_bytes(
                                        self.bytes * bits_per_byte // 8,
                                        byteorder='big'))[0]
            # bits.extend(pad * (total_bit_count - len(bits)))


        elif self.format.is_floating_point():
            # TODO: CAMPid 097897541967932453154321546542175421549

            # note that this is hardcoded for two bytes/address fudge
            types = {
                4: 'f',
                8: 'd'
            }
            try:
                type = types[self.bytes * bits_per_byte]
            except KeyError:
                raise Exception(
                    'float type only supports lengths in [{}]'.
                    format(', '.join([str(t) for t in types.keys()]))
                )
        else:
            raise Exception('Unsupported type format: {}'.format(self.type))

        return '{}{}{}'.format('>', type, self.bytes * bits_per_byte)



@attr.s
class UnspecifiedType:
    name = attr.ib()


@attr.s
class SubroutineType:
    return_type = attr.ib(default=None)
    name = attr.ib(default=None)
    parameters = members = attr.ib(default=attr.Factory(list))


@attr.s
class PointerType:
    type = attr.ib()
    name = attr.ib(default='<pointer>')
    modifier = '*'

    # note that this is hardcoded and should be detected
    # DW_AT_address_class happens to be 32 but the definition
    # doesn't seem to suggest that means 32-bits
    bytes = 32 // bits_per_byte

    def format_string(self):
        return '<u{}'.format(self.bytes * bits_per_byte)


@attr.s
class VolatileType(BytesProxy):
    type = attr.ib()
    name = attr.ib(default=None)
    modifier = 'volatile'


@attr.s
class ArrayType:
    type = attr.ib()
    bytes = attr.ib()
    name = attr.ib(default=None)

    def length(self):
        return self.bytes // base_type(self.type).bytes

    def array_markup(self):
        return '[{}]'.format(self.length())

    def unpack(self, data):
        # TODO: CAMPid 078587996542145215432667431535465465421
        if isinstance(data, bytes):
            data = bytearray(data)
        elif isinstance(data, str):
            data = bytearray(int(data, 2)
                             .to_bytes(self.bytes * bits_per_byte // 8,
                                       byteorder='big'))
        bits = bytearray_to_bits(data)

        base = base_type(self.type)
        type_bit_size = base.bytes * bits_per_byte

        expected_items = self.length()

        values = []
        for group in grouper(bits, type_bit_size):
            expected_items -= 1
            values.append(base.unpack(''.join(group)))

        if expected_items != 0:
            raise Exception('wrong amount of data for array')

        return values

@attr.s
class ConstType(BytesProxy):
    type = attr.ib()
    name = attr.ib(default=None)
    modifier = 'const'


@attr.s
class RestrictType:
    type = attr.ib()
    name = attr.ib(default=None)


def name(type):
    if hasattr(type, 'name'):
        return type.name
    else:
        return name(type.type)


def full_type(type):
    if isinstance(type, (TypeDef, Type, Union)):
        return type.name
    elif hasattr(type, 'modifier'):
        return '{} {}'.format(type.modifier, full_type(type.type))
    else:
        return full_type(type.type)


def base_type(type):
    if isinstance(type, (PointerType, ArrayType, EnumerationType)):
        return type
    elif hasattr(type, 'type'):
        return base_type(type.type)
    else:
        return type


def type_name(type):
    name = None
    while type is not None:
        type = type.type

        if hasattr(type, 'name'):
            if type.name is not None and len(type.name) > 0:
                name = type.name
                break

    return name


def location(member):
    l = member.location
    if member.bit_offset is not None:
        l = '{}:{}'.format(l, member.bit_offset)
    return l


@attr.s
class Struct:
    bytes = attr.ib()
    name = attr.ib(default=None)
    members = attr.ib(default=attr.Factory(collections.OrderedDict))

    def render(self, terminate=True):
        members = []
        for member in self.members.values():
            members.append(
                '    {type} {name}{bits}; // {base_type} {size}@{location}'
                    .format(
                        type=full_type(member),
                        name=member.name,
                        bits=':{}'.format(member.bit_size)
                             if member.bit_size is not None else '',
                        base_type=base_type(member).name,
                        size=base_type(member).bytes,
                        location=location(member)
                    )
            )
        return textwrap.dedent('''\
        struct {name}{{
        {members}
        }}{terminator} /* {size} */''').format(
            name=self.name + ' ' if self.name is not None else '',
            members='\n'.join(members),
            terminator=';' if terminate else '',
            size=self.bytes)

    # def format_string(self):
    #     format = ''
    #     for member in self.padded_members():
    #         if member.name == '<padding>':
    #             f = '<p{}'.format(member.bit_size)
    #         elif member.bit_offset is None:
    #             f = member.format_string()
    #         else:
    #             f = '>{}{}'.format(member.format_string()[1], member.bit_size)
    #
    #         format += f
    #
    #     return format

    def padded_members(self):
        locations = collections.defaultdict(list)
        for member in self.members.values():
            if member.bit_offset is None:
                range = (
                    0,
                    (base_type(member).bytes * bits_per_byte) - 1,
                    member
                )
            else:
                range = (
                    member.bit_offset,
                    member.bit_offset+member.bit_size-1,
                    member
                )

            locations[member.location].append(range)

        for location, ranges in locations.items():
            ranges.sort()
            padding = []
            bit = 0
            for range in ranges:
                if range[0] > bit:
                    pad = StructMember(
                        name='<padding>',
                        type=range[2].type,
                        location=location,
                        bit_offset=bit,
                        bit_size=range[0] - bit,
                        padding=True
                    )

                    padding.append((bit, range[0] - 1, pad))
                bit = range[1] + 1
            ranges.extend(padding)
            ranges.sort()
            ranges[:] = [r[2] for r in ranges]

        ranges = []
        for location in sorted(locations.keys()):
            ranges.extend(locations[location])

        return ranges

    def unpack(self, data):
        # TODO: CAMPid 078587996542145215432667431535465465421
        if isinstance(data, bytes):
            data = bytearray(data)
        elif isinstance(data, str):
            data = bytearray(int(data, 2)
                             .to_bytes(self.bytes * bits_per_byte // 8,
                                       byteorder='big'))

        location = None
        for member in self.padded_members():
            b_type = base_type(member)
            if location != member.location:
                location = member.location
                if b_type.bytes > 1 and isinstance(b_type, Type) and member.bit_size is not None:
                    # TODO: CAMPid 08793287728743824372437983526631513679
                    byte = member.location * bits_per_byte // 8
                    s = slice(byte, byte + b_type.bytes * bits_per_byte // 8)
                    data[s] = bytearray(itertools.chain(*reversed(list(
                        grouper(data[s], bits_per_byte // 8)))))

        bits = bytearray_to_bits(data)
        values = collections.OrderedDict()
        for member in self.padded_members():
            if member.name != '<padding>':
                bit_size = (member.bit_size
                            if member.bit_size is not None
                            else member.bytes * bits_per_byte)

                bit_offset = (member.bit_offset
                              if member.bit_offset is not None
                              else 0)

                msb = (member.location * bits_per_byte) + bit_offset
                lsb = msb + bit_size

                values[member.name] = member.unpack(bits[msb:lsb])

        # return collections.OrderedDict(reversed(list(values.items())))

        # raw_values = bitstruct.unpack(self.format_string(), data)
        #
        # d = dict(
        #     zip(
        #         (m.name for m in self.padded_members() if m.name != '<padding>'),
        #         raw_values
        #     )
        # )
        #
        return collections.OrderedDict(
            (m.name, values[m.name]) for m in self.members.values())

    # TODO: refactor to *args
    def offset_of(self, names):
        offset = 0

        struct = self

        for name in names:
            member = struct.members[name]
            offset += member.location
            struct = base_type(member)

        return offset

    def member(self, names):
        struct = self

        for name in names:
            member = base_type(struct.members[name])
            struct = member

        return member

    def member_and_offset(self, names):
        return self.member(names), self.offset_of(names)

# https://docs.python.org/3/library/itertools.html
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


@attr.s
class StructMember:
    name = attr.ib()
    type = attr.ib()
    location = attr.ib()
    bit_offset = attr.ib(default=None)
    bit_size = attr.ib(default=None)
    padding = attr.ib(default=False)

    def format_string(self):
        format = base_type(self).format_string()
        # format = '>' + format[1:]
        return format

    @property
    def bytes(self):
        return base_type(self).bytes

    def unpack(self, bits):
        return base_type(self).unpack(bits)

@attr.s
class Union:
    bytes = attr.ib()
    name = attr.ib(default=None)


@attr.s
class PointerToMember:
    name = attr.ib()


@attr.s
class EnumerationType:
    bytes = attr.ib()
    name = attr.ib(default=None)
    type = attr.ib(default=None)
    values = attr.ib(default=attr.Factory(list))


@attr.s
class EnumerationValue:
    name = attr.ib()
    value = attr.ib()


@attr.s
class TypeDef:
    name = attr.ib()
    type = attr.ib()

    # @property
    # def bytes(self):
    #     return self.type.bytes
    #
    # @property
    # def format(self):
    #     return self.type.format

    # @property
    # def base_type(self):
    #     if isinstance(self.type, Type):
    #         return self.type
    #     else:
    #         return self.type.base_type

    def render(self):
        return 'typedef {type} {name};'.format(
            type=self.type.render(terminate=False),
            name=self.name)

    def unpack(self, bits):
        return base_type(self).unpack(bits)

    @property
    def bytes(self):
        return self.type.bytes


@attr.s
class LoUser(BytesProxy):
    type = attr.ib()


@attr.s
class HiUser:
    type = attr.ib()


@attr.s
class Variable:
    name = attr.ib()
    type = attr.ib()
    address = attr.ib()

    def render(self):
        base = base_type(self)
        if isinstance(base, ArrayType):
            array = base.array_markup()
        else:
            array = ''
        return '{type} {name}{array}; // {base} @ 0x{address:08X}'.format(
            type=full_type(self),
            name=name(self),
            array=array,
            base=base_type(self).name,
            address=self.address
        )

    def unpack(self, data):
        return base_type(self).unpack(data)


def get_value(variable):
    # TODO: totally stubbed...
    return 42


def is_modifier(type):
    return isinstance(type, (ConstType,
                             #PackedType,
                             PointerType,
                             #ReferenceType,
                             RestrictType,
                             #SharedType,
                             VolatileType))


def dereference(variable):
    name = '&' + variable.name

    type = variable
    while not isinstance(type, PointerType):
        type = type.type

    # one more to get past the pointer
    type = type.type

    address = get_value(variable)

    return Variable(name=name, type=type, address=address)


def fake_section(filename, section_name):

    with open(os.path.splitext(filename)[0] + section_name, 'rb') as f:
        debug_bytes = f.read()

    return DebugSectionDescriptor(
        stream=io.BytesIO(debug_bytes),
        name=section_name,
        global_offset=0,
        size=len(debug_bytes))

def process_file(filename):
    print('Processing file:', filename)
    print('Working directory:', os.getcwd())

    coff = epyqlib.ticoff.Coff()
    coff.from_file(filename)

    section_bytes = {s.name: (io.BytesIO(s.data), len(s.data))
                     for s in coff.sections
                     if s.name.startswith('.debug_')}
    debug_sections = {
        name: DebugSectionDescriptor(
            stream=stream,
            name=name,
            global_offset=0,
            size=length)
        for name, (stream, length) in section_bytes.items()
    }

    from elftools.dwarf.dwarfinfo import DWARFInfo, DwarfConfig
    dwarfinfo = DWARFInfo(
        config=DwarfConfig(
            little_endian=True,
            default_address_size=4,
            machine_arch='<unknown>'),
        debug_info_sec=debug_sections.get('.debug_info', None),
        # debug_info_sec=DebugSectionDescriptor(
        #     stream=io.BytesIO(dwarf_debug_info_bytes),
        #     name='.debug_info',
        #     global_offset=0,
        #     size=len(dwarf_debug_info_bytes)),
        debug_aranges_sec=debug_sections.get('.debug_aranges', None),
        debug_abbrev_sec=debug_sections.get('.debug_abbrev', None),
        debug_frame_sec=debug_sections.get('.debug_frame', None),
        # TODO(eliben): reading of eh_frame is not hooked up yet
        eh_frame_sec=None,
        debug_str_sec=debug_sections.get('.debug_str', None),
        debug_loc_sec=debug_sections.get('.debug_loc', None),
        debug_ranges_sec=debug_sections.get('.debug_ranges', None),
        debug_line_sec=debug_sections.get('.debug_line', None))

    objects = collections.OrderedDict((tag, []) for tag in [
        'DW_TAG_subprogram',
        'DW_TAG_variable',
        'DW_TAG_typedef',
        'DW_TAG_base_type',
        'DW_AT_encoding',
        'DW_TAG_structure_type',
        'DW_TAG_union_type',
        'DW_TAG_ptr_to_member_type',
        'DW_TAG_enumeration_type',
        'DW_TAG_pointer_type',
        'DW_TAG_array_type',
        'DW_TAG_volatile_type',
        'DW_TAG_const_type',
        'DW_TAG_restrict_type',
        'DW_TAG_lo_user',
        'DW_TAG_hi_user',
        'DW_TAG_unspecified_type',
        'DW_TAG_subroutine_type'
    ])

    for CU in dwarfinfo.iter_CUs():
    # it = dwarfinfo.iter_CUs()
    # while True:
    #     try:
    #         CU = next(it)
    #     except StopIteration:
    #         break
    #     except elftools.common.exceptions.DWARFError:
    #         traceback.print_exc()
    #         print('Skipping current CU')
    #         next

        # DWARFInfo allows to iterate over the compile units contained in
        # the .debug_info section. CU is a CompileUnit object, with some
        # computed attributes (such as its offset in the section) and
        # a header which conforms to the DWARF standard. The access to
        # header elements is, as usual, via item-lookup.
        print('  Found a compile unit at offset %s, length %s' % (
            CU.cu_offset, CU['unit_length']))

        # Start with the top DIE, the root for this CU's DIE tree
        top_DIE = CU.get_top_DIE()
        print('    Top DIE with tag=%s' % top_DIE.tag)

        path = top_DIE.get_full_path()
        # We're interested in the filename...
        print('    name=%s' % path)

        if path.endswith('__TI_internal'):
            print('__TI_internal found, terminating DWARF parsing')
            break
        else:
            # Display DIEs recursively starting with top_DIE
            die_info_rec(top_DIE, objects=objects)
            # pass

    def die_info_rec_structure_type(die, indent_level):
        for child in die.iter_children():
            # print(indent_level + str(child.attributes['DW_AT_name'].value.decode('utf-8')))
            location = str(child.attributes['DW_AT_data_member_location'].value)
            name = str(child.attributes['DW_AT_name'].value.decode('utf-8'))
            print(indent_level + name + ': ' + location)
            # print(indent_level + str(child.attributes['DW_AT_name'].value.decode('utf-8')) + ': ' + str(child.attributes['DW_AT_data_member_location'].value.decode('utf-u')))

    # this is yucky but the embedded system is weird with two bytes
    # per address and even sizeof() responds in units of addressable units
    # rather than actual bytes
    byte_size_fudge = 1

    offsets = {}

    types = []
    for die in objects['DW_TAG_base_type']:
        type = Type(
            name=die.attributes['DW_AT_name'].value.decode('utf-8'),
            bytes=die.attributes['DW_AT_byte_size'].value * byte_size_fudge,
            format=TypeFormats(die.attributes['DW_AT_encoding'].value)
        )
        types.append(type)
        offsets[die.offset] = type
        print('{: 10d} {}'.format(die.offset, type))

    variables = []
    for die in objects['DW_TAG_variable']:
        location = die.attributes['DW_AT_location'].value
        # TODO: check this better
        if len(location) != 5:
            continue
        address = int.from_bytes(bytes(location[1:5]),
                                 'little')
        variable = Variable(
            name=die.attributes['DW_AT_name'].value.decode('utf-8'),
            type=die.attributes['DW_AT_type'].value,
            address=address
        )
        variables.append(variable)
        offsets[die.offset] = variable
        print('{: 10d} {}'.format(die.offset, variable))

    lo_users = []
    for die in objects['DW_TAG_lo_user']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        lo_user = LoUser(
            type=die.attributes['DW_AT_type'].value
        )
        lo_users.append(lo_user)
        offsets[die.offset] = lo_user
        print('{: 10d} {}'.format(die.offset, lo_user))

    hi_users = []
    for die in objects['DW_TAG_hi_user']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        hi_user = HiUser(
            type=die.attributes['DW_AT_type'].value
        )
        hi_users.append(hi_user)
        offsets[die.offset] = hi_user
        print('{: 10d} {}'.format(die.offset, hi_user))

    subroutine_types = []
    for die in objects['DW_TAG_subroutine_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        type = die.attributes.get('DW_AT_type', None)
        if type is not None:
            type = type.value
        subroutine_type = SubroutineType(
            name=name,
            return_type=type
        )
        for parameter in die.iter_children():
            subroutine_type.parameters.append(
                parameter.attributes['DW_AT_type'].value)
        subroutine_types.append(subroutine_type)
        offsets[die.offset] = subroutine_type
        print('{: 10d} {}'.format(die.offset, subroutine_type))

    unspecified_types = []
    for die in objects['DW_TAG_unspecified_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        unspecified_type = UnspecifiedType(
            name=name
        )
        unspecified_types.append(unspecified_type)
        offsets[die.offset] = unspecified_type
        print('{: 10d} {}'.format(die.offset, unspecified_type))

    pointer_types = []
    for die in objects['DW_TAG_pointer_type']:
        type = die.attributes['DW_AT_type'].value
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
            pointer_type = PointerType(name=name, type=type)
        else:
            pointer_type = PointerType(type=type)
        pointer_types.append(pointer_type)
        offsets[die.offset] = pointer_type
        print('{: 10d} {}'.format(die.offset, pointer_type))

    volatile_types = []
    for die in objects['DW_TAG_volatile_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        volatile_type = VolatileType(
            name=name,
            type=die.attributes['DW_AT_type'].value
        )
        volatile_types.append(volatile_type)
        offsets[die.offset] = volatile_type
        print('{: 10d} {}'.format(die.offset, volatile_type))

    array_types = []
    for die in objects['DW_TAG_array_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        byte_size = die.attributes.get('DW_AT_byte_size', None)
        if byte_size is not None:
            byte_size = byte_size.value
        array_type = ArrayType(
            name=name,
            bytes=byte_size,
            type=die.attributes['DW_AT_type'].value
        )
        array_types.append(array_type)
        offsets[die.offset] = array_type
        print('{: 10d} {}'.format(die.offset, array_type))

    const_types = []
    for die in objects['DW_TAG_const_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        const_type = ConstType(
            name=name,
            type=die.attributes['DW_AT_type'].value
        )
        const_types.append(const_type)
        offsets[die.offset] = const_type
        print('{: 10d} {}'.format(die.offset, const_type))

    restrict_types = []
    for die in objects['DW_TAG_restrict_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        restrict_type = RestrictType(
            name=name,
            type=die.attributes['DW_AT_type'].value
        )
        restrict_types.append(restrict_type)
        offsets[die.offset] = restrict_type
        print('{: 10d} {}'.format(die.offset, restrict_type))

    structure_types = []
    for die in objects['DW_TAG_structure_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        struct = Struct(
            name=name,
            bytes=die.attributes['DW_AT_byte_size'].value
        )
        structure_types.append(struct)
        offsets[die.offset] = struct
        for member_die in die.iter_children():
            a = member_die.attributes
            bit_offset = a.get('DW_AT_bit_offset', None)
            if bit_offset is not None:
                bit_offset = bit_offset.value
            bit_size = a.get('DW_AT_bit_size', None)
            if bit_size is not None:
                bit_size = bit_size.value
            # TODO: location[1] is just based on observation
            name = a['DW_AT_name'].value.decode('utf-8')
            struct.members[name] = StructMember(
                name=name,
                type=a['DW_AT_type'].value,
                location=a['DW_AT_data_member_location'].value[1],
                bit_offset=bit_offset,
                bit_size=bit_size
            )
        print(list(die.iter_children()))
        print('{: 10d} {}'.format(die.offset, struct))

    union_types = []
    for die in objects['DW_TAG_union_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        union = Union(
            name=name,
            bytes=die.attributes['DW_AT_byte_size'].value
        )
        union_types.append(union)
        offsets[die.offset] = union
        print('{: 10d} {}'.format(die.offset, union))

    pointer_to_member_types = []
    for die in objects['DW_TAG_ptr_to_member_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        pointer_to_member = PointerToMember(name=name)
        pointer_to_member_types.append(pointer_to_member)
        offsets[die.offset] = pointer_to_member
        print('{: 10d} {}'.format(die.offset, pointer_to_member))

    enumeration_types = []
    for die in objects['DW_TAG_enumeration_type']:
        name = die.attributes.get('DW_AT_name', None)
        if name is not None:
            name = name.value.decode('utf-8')
        type = die.attributes.get('DW_AT_type', None)
        if type is not None:
            type = type.value
        enumeration = EnumerationType(
            name=name,
            bytes=die.attributes['DW_AT_byte_size'].value * byte_size_fudge,
            type=type
        )
        for value in die.iter_children():
            enumeration.values.append(
                EnumerationValue(
                    name=value.attributes['DW_AT_name'].value.decode('utf-8'),
                    value=value.attributes['DW_AT_const_value'].value
                )
            )
        enumeration_types.append(enumeration)
        offsets[die.offset] = enumeration
        print('{: 10d} {}'.format(die.offset, enumeration))
    
    typedefs = []
    for die in objects['DW_TAG_typedef']:
        typedef = TypeDef(
            name=die.attributes['DW_AT_name'].value.decode('utf-8'),
            type=(die.offset, die.attributes['DW_AT_type'].value)
        )
        typedefs.append(typedef)
        offsets[die.offset] = typedef

    offset_values = sorted(offsets.keys())
    print(len(offset_values))
    print(offset_values)
    fails = 0
    for typedef in typedefs:
        offset = typedef.type[0]
        try:
            typedef.type = offsets[typedef.type[1]]
        except KeyError:
            print('Failed to find type for {}'.format(typedef))
            fails += 1
        else:
            print('{: 10d} {}'.format(offset, typedef))
    print(fails)

    for structure in structure_types:
        for member in structure.members.values():
            member.type = offsets[member.type]

    passes = 0
    while True:
        print('Starting pass {}'.format(passes))
        pass_again = False
        for item in subroutine_types:
            if isinstance(item.return_type, int):
                item.return_type = offsets[item.return_type]
            for i, parameter in enumerate(item.parameters):
                if isinstance(parameter, int):
                    item.parameters[i] = offsets[parameter]

        for item in offsets.values():
            if hasattr(item, 'type') and isinstance(item.type, int):
                try:
                    item.type = offsets[item.type]
                except KeyError:
                    if passes >= 10:
                        print(item)
                        raise
                    pass_again = True

        passes += 1

        if not pass_again:
            break

    # for pointer_type in pointer_types:
    #     print(pointer_type)
    #     pointer_type.type = offsets[pointer_type.type]
    #     print(pointer_type)
    #
    # for array_type in array_types:
    #     print(array_type)
    #     array_type.type = offsets[array_type.type]
    #     print(array_type)
    #
    # for volatile_type in volatile_types:
    #     print(volatile_type)
    #     volatile_type.type = offsets[volatile_type.type]
    #     print(volatile_type)

    names = {None: []}
    for item in offsets.values():
        if hasattr(item, 'name'):
            if item.name is None:
                names[item.name].append(item)
            elif is_modifier(item):
                pass
            elif item.name.startswith('$'):
                pass
            else:
                if item.name in names:
                    raise Exception('{}\n{}'.format(item, names[item.name]))
                    # pass
                # else:
                #     names[item.name] = []
                # names[item.name].append(item)
                names[item.name] = item

    return names, variables, bits_per_byte

def testit(names, variables):
    def nonesorter(a):
        if a[0] is None:
            return '', a[1]
        return a

    with open('output.txt', 'w') as f:
        for name, item in sorted(names.items(), key=nonesorter):
            i = item
            print('{}: {}'.format(name, i), file=f)

    import operator
    print('\n'.join(str(v) for v in sorted(variables, key=operator.attrgetter('name'))))
    print(names['Vholdoff'].render())
    print(names['ozFpga'].render())
    print(names['FpgaRegs'].render())
    print(names['writingEE'].render())
    print(names['rxStart'].render())
    print(dereference(names['rxStart']).render())
    print(names['POR_Flags'].render())
    print(names['IEEE_1547_FreqLimit'].render())
    # print(base_type(names['IEEE_1547_FreqLimit']).format_string())
    a = b'\x01\x02\x03\x04'
    b = b'\x05\x06\x07\x08'
    c = a + b
    # print(base_type(names['IEEE_1547_FreqLimit']).unpack(c))
    print((int.from_bytes(a, byteorder='little'),
           int.from_bytes(b, byteorder='little')))


    data = b'\x00\xd1\x01\x44\x00\x06\x00\x00\x00\x07\x00\x08\x28\x09\x00\xb0'
    # data = bytes(ccp.endianness_swap_2byte(data_raw))#b'\xd1\x00\x44\x01\x06\x00\x00\x00'
    # print(data)
    # print(''.join(['{:08b}'.format(b) for b in data]))
    print(names['TestStruct'].render())
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(base_type(names['TestStruct']).padded_members())
    # print(base_type(names['TestStruct']).format_string())
    print(bytearray_to_bits(data))
    pp.pprint(base_type(names['TestStruct']).unpack(data))

    data = bytearray(data)
    for member in base_type(names['TestStruct']).padded_members():
        type = base_type(member)
        if member.bit_offset is None:
            byte = member.location * bits_per_byte // 8
            s = slice(byte, byte + type.bytes * bits_per_byte // 8)
            # print('slice: {}'.format(s))
            # print(data)
            data[s] = ccp.endianness_swap_2byte(data[s])
            # print(data)

    #                              |  |  |     |  |         |
    pp.pprint(bitstruct.unpack('<p4>u6>u3>u3<p4>u6>u6<u32<p6>u10<u16<p2>u10<u10<u10',
                               data))


    print('-----------------------------')
    print('-----------------------------')
    print('-----------------------------')

    data = collections.OrderedDict()
    data['TestStruct1'] = b'\x03\xFF\x00\x00'
    data['TestStruct2'] = b'\xFF\xFF\x00\x0F'
    data['TestStruct3'] = b'\xFF\xFF\x3F\xFF'
    data['TestStruct4'] = b'\x03\xFF'
    data['TestStruct5'] = b'\x03\xFF\x00\x00\x00\x00\x00\x00'
    data['TestStruct6'] = b'\xFF\xFF\x00\x0F\x00\x00\x00\x00'
    data['TestStruct7'] = b'\xFF\xFF\x3F\xFF\x00\x00\x00\x00'
    data['TestStruct8'] = b'\xFF\xFF\xFF\xFF\x00\xFF\x00\x00'
    data['TestStruct9'] = b'\xFF\xFF\xFF\xFF\xFF\xFF\x00\x03'
    data['TestStruct10'] = b'\xFF\xFF\xFF\xFF\xFF\xFF\x0F\xFF'
    data['TestStruct11'] = b'\xFF\xFF\xFF\xFF\xFF\xFF\x0F\xFF\x44\x05\x00\x00'
    data['TestStruct12'] = b'\xFF\xFF\xFF\xFF\xFF\xFF\x0F\xFF\x44\x05\x00\x00\x00\x2A\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x05\x00\x00'
    # huh? 6 entries listed in the debugger for a 5 entry array?
    data['testArray1'] = b'\x00\x0B\x00\x00\x00\x16\x00\x00\x00\x21\x00\x00\x00\x2C\x00\x00\x00\x37\x00\x00'#\x00\x05\x35\x4A'

    for name in data.keys():#['TestStruct{}'.format(i) for i in [1,2,3,4,5,6,7,8,9,10,11]]:
        print(names[name].render())
        base = base_type(names[name])
        if hasattr(base, 'padded_members'):
            pp.pprint(base.padded_members())
        # print(base_type(names[name]).format_string())
        print(bytearray_to_bits(data[name]))
        pp.pprint(base.unpack(data[name]))

        # data = bytearray(data)
        # for member in base_type(names[name]).padded_members():
        #     type = base_type(member)
        #     if member.bit_offset is None:
        #         byte = member.location * bits_per_byte // 8
        #         s = slice(byte, byte + type.bytes * bits_per_byte // 8)
        #         # print('slice: {}'.format(s))
        #         # print(data)
        #         data[s] = ccp.endianness_swap_2byte(data[s])
        #         # print(data)
        #
        # pp.pprint(bitstruct.unpack('<p2<u10<u10<u10',
        #                            data))
        print('\n\n-----------------------------\n\n')




    print('-----------------------------')
    print('-----------------------------')
    print('-----------------------------')
    return


    print(names['Relay'].render())
    # print(base_type(names['Relay']).bytes)
    # print(base_type(names['Relay']).format_string())
    data = b'\x00\x48\x00\x00\xd5\x13\x00\x00'
    pp.pprint(data)
    # data = bytes(ccp.endianness_swap_2byte(data))
    # <u2<u1<u2<u1<u1<p9<s16<u32
    # <u1<u1<u2<u1<u2<p9<s16<u32
    # print(''.join(['{:08b}'.format(b) for b in data]))
    # print(bitstruct.unpack('<p1<u1<u1<u2<u1<u2<p8<s16<u32', data))
    # print(bitstruct.unpack('<u1<u2<u1<u2<u1<p9<s16<u32', data))
    # print(bitstruct.unpack('<p9<u1<u1<u2<u1<u2<s16<u32', data))
    # pp.pprint(base_type(names['Relay']).padded_members())
    pp.pprint(base_type(names['Relay']).unpack(data))

    return

    indent_level = '    '
    for tag, items in objects.items():
        for die in items:
            print('{}: {}'.format(tag, die.attributes['DW_AT_name'].value.decode('utf-8')))

            if die.tag == 'DW_TAG_structure_type':
                print(indent_level + 'DIE tag=%s' % die.tag)
                try:
                    print(indent_level + '  Sibling: ' + str(
                        die.attributes['DW_AT_sibling'].value))
                except KeyError:
                    print(indent_level + '  KeyError on DW_AT_sibling')
                    pass
                print(indent_level + '  Offset: ' + str(die.offset))
                print(indent_level + '  File: ' + str(
                    die.attributes['DW_AT_decl_file'].value))
                print(indent_level + '  Line: ' + str(
                    die.attributes['DW_AT_decl_line'].value))
                print(indent_level + '  Attributes: ' + str(die.attributes))
                print(indent_level + '  DIE: ' + str(dir(die)))
                die_info_rec_structure_type(die, indent_level + '    ')
            # else:
            # print(indent_level + 'DIE tag=%s' % die.tag)
            elif die.tag == 'DW_TAG_typedef':
                print(indent_level + 'DIE tag=%s' % die.tag)
                try:
                    print(indent_level + '  Name: ' + str(
                        die.attributes['DW_AT_name'].value.decode('utf-8')))
                except KeyError:
                    print(indent_level + '  KeyError on DW_AT_name')
                    pass
                print(indent_level + '  Offset: ' + str(die.offset))
                file = die.attributes.get('DW_AT_decl_file', None)
                if file is not None:
                    file = file.value
                else:
                    file = 'not found'
                print(indent_level + '  File: ' + str(file))
                line = die.attributes.get('DW_AT_decl_line', None)
                if line is not None:
                    line = line.value
                else:
                    line = 'not found'
                print(indent_level + '  Line: ' + str(line))
                print(indent_level + '  Type: ' + str(die.attributes['DW_AT_type'].value))
                print(indent_level + '  describe_attr_value(Type): ' +
                      describe_attr_value(die.attributes['DW_AT_type'],
                                          die,
                                          die.cu.cu_offset))
                print(indent_level + '  Attributes: ' + str(die.attributes))
                print(indent_level + '  DIE: ' + str(dir(die)))
            elif die.tag == 'DW_TAG_variable':
                print(indent_level + 'DIE tag=%s' % die.tag)
            else:
                print(indent_level + 'DIE tag=%s' % die.tag)
                print(indent_level + '  Offset: ' + str(die.offset))
                for attribute, value in die.attributes.items():
                    print(indent_level + '  {}: {}'
                          .format(attribute,
                                  describe_attr_value(die.attributes[attribute],
                                                      die,
                                                      die.cu.cu_offset)))


def die_info_rec(die, indent_level='    ', objects=None):
    """ A recursive function for showing information about a DIE and its
        children.
    """
    print(indent_level + 'DIE tag=%s, name=%s' % (die.tag, die.attributes.get('DW_AT_name', None)))
    if objects is not None and die.tag in objects.keys():
        objects[die.tag].append(die)
    child_indent = indent_level + '  '
    for child in die.iter_children():
        die_info_rec(child, child_indent, objects)


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        names, variables, bits_per_byte = process_file(filename)
        testit(names, variables)
