#!/usr/bin/env python3

def convert(trc, socketcan):
    for line in trc:
        if line.startswith(';'):
            continue

        columns = line.split()
        counter = int(columns.pop(0)[:-1])
        milliseconds = float(columns.pop(0))
        seconds = milliseconds / 1000
        bus = int(columns.pop(0))
        transmit = columns.pop(0) == 'Tx'
        id = int(columns.pop(0), 16)
        reserved = columns.pop(0)
        data_length = int(columns.pop(0))
        data = columns

        socketcan.write('({seconds:020.6f}) can0 {id:08X}#{data}\n'.format(
            seconds=seconds, id=id, data=''.join(data)))

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--trc', type=argparse.FileType('r'),
                        default=None)
    parser.add_argument('-s', '--socketcan', type=argparse.FileType('w'),
                        default=None)
    args = parser.parse_args()

    convert(trc=args.trc, socketcan=args.socketcan)

    sys.exit(0)
