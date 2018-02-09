import argparse
import attr
import sunspec.core.client
import sys
import time

# d = client.SunSpecClientDevice(client.RTU, 1, 'COM1', max_count=10)
# d = sunspec.core.client.client.SunSpecClientDevice(client.TCP, 1, ipaddr='192.168.10.203', max_count=10)
# print(d.models)
#
# d.epc_control.read()
# print(d.epc_control)

@attr.s
class Flags(object):
    _model = attr.ib()
    _point = attr.ib()
    _names = attr.ib(default=attr.Factory(set), convert=set)

    def __attrs_post_init__(self):
        self._symbols = self._model.model.points[self._point].point_type.symbols
        self._valid_names = set(s.id for s in self._symbols)

        self._validate_names(*self._names)

        self._bit_map = {int(s.value): s.id for s in self._symbols}

    def _validate_names(self, *names):
        if len(names) == 0:
            return

        names = set(names)

        bad_names = names - self._valid_names

        if len(bad_names) > 0:
            raise Exception(
                'Invalid flag{} specified for {}: {}'
                .format('s' if len(bad_names) > 1 else '',
                        self._point,
                        ', '.join(str(n) for n in bad_names)
                )
            )

    def set(self, *names):
        self._validate_names(*names)
        for name in names:
            self._names.add(name)

    def clear(self, *names):
        self._validate_names(*names)
        for name in names:
            self._names.discard(name)

    def to_int(self):
        return sum(1 << int(s.value) for s in self._symbols
                   if s.id in self._names)

    def set_all(self):
        self._names = set(self._valid_names)

    def clear_all(self):
        self._names = set()

    def from_int(self, source):
        s = '{:b}'.format(source)
        highest_bit = max(self._bit_map.keys())
        if len(s) > highest_bit+1:
            raise Exception(
                'Highest bit is {} but int has bit {} set'
                .format(highest_bit, len(s)-1)
            )

        names = (self._bit_map[n] for n, b in enumerate(reversed(s))
                 if b == '1')
        self.clear_all()
        self.set(*names)

    def active(self):
        return [s.id for s in self._symbols if s.id in self._names]


def parse_args(*args):
    parser = argparse.ArgumentParser()

    interface_group = parser.add_mutually_exclusive_group()
    interface_group.add_argument('--ip')#, default='192.168.10.203')
    interface_group.add_argument('--serial-port')

    parser.add_argument('--baud-rate', default='9600')

    parser.add_argument('--invert-hw-enable', action='store_true')

    return parser.parse_args(args)


def update_cmd_bits(cmd_bits, d):
    d.epc_control.CmdBits = cmd_bits.to_int()
    print('{}: {}'.format(d.epc_control.CmdBits, cmd_bits.active()))
    d.epc_control.model.points['CmdBits'].write()
    d.epc_control.read()
    print(d.epc_control)
    time.sleep(0.5)
    d.inverter.read()
    print(d.inverter.StVnd)


@attr.s
class WriteCounter:
    sequential = attr.ib(default=0)
    total = attr.ib(default=0)
    failures = attr.ib(default=0)
    characters_per_line = attr.ib(default=70)

    def good(self):
        self.sequential += 1
        self.total += 1

        print('.', end='')
        sys.stdout.flush()
        if self.sequential % self.characters_per_line == 0:
            print('')
            self.print()

    def bad(self):
        self.sequential = 0
        self.failures += 1
        self.print()

    def print(self):
        print()
        print('successful writes since last failure: {}'.format(self.sequential))
        print('total successful writes: {}'.format(self.total))
        print('total timeouts: {}'.format(self.failures))


def main(sys_argv):
    args = parse_args(*sys_argv)

    client_args = {
        'slave_id': 1,
        'max_count': 100
    }

    if args.ip is not None:
        client_args['device_type'] = sunspec.core.client.TCP
        client_args['ipaddr'] = args.ip
    elif args.serial_port is not None:
        client_args['device_type'] = sunspec.core.client.RTU
        client_args['name'] = args.serial_port
        client_args['baudrate'] = args.baud_rate

    d = sunspec.core.client.SunSpecClientDevice(**client_args)

    cmd_bits = Flags(model=d.epc_control, point='CmdBits')

    d.epc_control.CtlSrc = 1
    d.epc_control.model.points['CtlSrc'].write()
    # stop
    cmd_bits.clear_all()
    cmd_bits.set('InvertHwEnable')
    cmd_bits.set('FltClr')
    d.epc_control.CmdBits = cmd_bits.to_int()
    d.epc_control.model.points['CmdBits'].write()

    write_counter = WriteCounter()

    try:
        while True:
            try:
                while True:
                    # enable and run
                    cmd_bits.set('En')
                    # remove fault clear command
                    cmd_bits.clear('FltClr')
                    d.epc_control.CmdBits = cmd_bits.to_int()
                    d.epc_control.DcVLim = 900
                    d.epc_control.DcILim = 175
                    d.epc_control.LineILim = 140
                    d.epc_control.CmdV = 480
                    d.epc_control.CmdHz = 600

                    d.epc_control.model.points['CmdBits'].write()
                    write_counter.good()

                    d.epc_control.model.points['CmdV'].write()
                    write_counter.good()

                    d.epc_control.model.points['CmdHz'].write()
                    write_counter.good()
            except sunspec.core.client.SunSpecClientError:
                write_counter.bad()
                time.sleep(2)
    finally:
        write_counter.print()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
