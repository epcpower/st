#!/usr/bin/env python3

import epyqlib.twisted.cancalibrationprotocol as ccp
import argparse


class Frame:
    def __init__(self, index, time, type, id, data, comment):
        self.index = int(index)
        self.time = float(time)
        self.type = type
        self.id = (int(id, 16), len(id) > 3)
        self.data = [int(d, 16) for d in data]
        self.comment = comment

    @classmethod
    def len(cls):
        return 6

    def __str__(self):
        format = ('Index: {{}}, Time: {{:.4f}}, Type: {{}}, ID: {{:0{}X}}, '
                  'Data: {{}}, Comment: {{}}').format(8 if self.id[1] else 3)
        data = ['{:02X}'.format(d) for d in self.data]
        data = ' '.join(data)
        return format.format(self.index, self.time, self.type, self.id[0],
                             data, self.comment)


def load_trc(file):
    frame_length = Frame.len()

    for line in file:
        if line.lstrip().startswith(';'):
            continue

        elements = line.replace(')', '').split()
        data_length = int(elements[frame_length - 2])
        meta = elements[:frame_length - 2]
        data = elements[frame_length - 1:frame_length + data_length - 1]
        try:
            comment = elements[frame_length + data_length - 1]
        except IndexError:
            comment = None

        frame = Frame(*meta, data, comment)
        if data_length != len(frame.data):
            raise Exception('blue')

        frame.time /= 1000

        yield frame


def load_sock(file):
    frame_length = Frame.len()

    for line in file:
        elements = line.replace('(', '').replace(')', '').replace('#', ' ').split()
        id = elements[2]
        if id == 'FFFFFFFF':
            comment = elements[3].lstrip('0123456789')
            data = elements[3][:-len(comment)]
        else:
            data = elements[3]
            data = [data[i:i+2] for i in range(0, len(data), 2)]

        frame = Frame(index=0,
                      time=elements[0],
                      type='Rx',
                      id=id,
                      data=data,
                      comment=None)

        yield frame


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace', '-t',
                        type=argparse.FileType('r'))
    parser.add_argument('--sock', '-s',
                        type=argparse.FileType('r'))

    return parser.parse_args(args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    args = parse_args(args=args)

    blocks = []

    if not ((args.trace is not None) ^ (args.sock is not None)):
        print('You must specify one and only one file type')
        return -1

    if args.trace:
        frames = load_trc(args.trace)
    elif args.sock:
        frames = load_sock(args.sock)

    for frame in frames:
        if (frame.type == 'Rx'
                and frame.id[1]
                and frame.id[0] == ccp.bootloader_can_id):
            if frame.data[0] == ccp.CommandCode.set_mta:
                address = sum(v << (8*(3-p)) for p, v in enumerate(frame.data[-4:]))
                # print('Raw Address: {}'.format(frame.data[-4:]))
                # print('Address: {}'.format(address))
                # if len(blocks) != 0:
                #     print('Latest block: {}'.format(blocks[-1]))
                #     print('Latest start: {}'.format(blocks[-1][0]))
                #     print('Latest length: {}'.format(blocks[-1][1]))
                if (len(blocks) == 0
                        or blocks[-1][0] + blocks[-1][1]/2 != address):
                    blocks.append([address, 0])
            elif frame.data[0] == ccp.CommandCode.download_6:
                blocks[-1][1] += 6
            elif frame.data[0] == ccp.CommandCode.download:
                blocks[-1][1] += frame.data[2]

    print('Note that separate blocks will be detected as one if they are contiguous.')
    for block in blocks:
        print('Start: {:08X}, Length: {}, Bytes: {}'.format(
            block[0], int(block[1]/2), block[1]
        ))


if __name__ == '__main__':
    import sys

    sys.exit(main())
