import logging
import os
import signal

import canmatrix.formats
import click

import epyqlib.utils.general

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


def id_string(id):
    return '0x{:08X}'.format(id)


def tabulate_signals(signals):
    rows = []

    for signal in signals:
        # if len(signal.unit) == 0 and signal.factor != 1:
            # table.append(('***',) * 5)
        startbit = signal.getStartbit()
        rows.append((
            '', '',
            signal.name,
            '{}/{}'.format(startbit % 8, startbit // 8),
            signal.signalsize,
            signal.factor,
            signal.unit,
            '{}: {}'.format(signal.enumeration, signal.values) if
            signal.enumeration is not None else '',
        ))
        if len(signal.comment) > 0:
            rows.append((*(('',) * 7), signal.comment))

    return rows


@click.command()
@click.option('--can', '-c', type=click.File('rb'), required=True)
@click.option('--verbose', '-v', count=True)
def main(can, verbose):
    if verbose >= 1:
        logger.setLevel(logging.DEBUG)

    matrix, = canmatrix.formats.load(
        can,
        os.path.splitext(can.name)[1].lstrip('.')
    ).values()

    mux_table = epyqlib.utils.general.TextTable()
    mux_table.append(
        'Mux Name', 'Mux ID', 'Name', 'Start', 'Length', 'Scaling', 'Units',
        'Values/Comment')

    frame_table = epyqlib.utils.general.TextTable()
    frame_table.append(
        'Frame', 'ID', 'Name', 'Start', 'Length', 'Scaling', 'Units',
        'Values/Comment')

    for frame in sorted(matrix.frames, key=lambda f: f.name):
        frame_table.append(
            frame.name,
            id_string(frame.id),
        )
        mux_table.append(
            '{} ({})'.format(frame.name, id_string(frame.id)),
        )

        multiplex_signal = frame.signals[0]
        if multiplex_signal.multiplex is None:
            multiplex_signal = None

        if multiplex_signal is None:
            frame_table.extend(tabulate_signals(sorted(
                frame.signals, key=lambda s: s.name)))
        else:
            frame_table.extend(tabulate_signals((multiplex_signal,)))
            # multiplex_signal.values = {
            #     int(k): v for k, v in multiplex_signal.values.items()
            # }

            for value, name in sorted(multiplex_signal.values.items()):
                if value == 0:
                    continue

                mux_table.append(
                    '',
                    value,
                    name,
                )

                signals = (
                    s for s in frame.signals
                    if s.multiplex == value and s.name != 'ReadParam_command'
                )

                mux_table.extend(tabulate_signals(sorted(
                    signals, key=lambda s: s.name)))

    print('\n\n - - - - - - - Multiplexes\n')
    print(mux_table)

    print('\n\n - - - - - - - Frames\n')
    print(frame_table)

    enumeration_table = epyqlib.utils.general.TextTable()
    enumeration_table.append('Name', '', 'Value')
    for name, values in sorted(matrix.valueTables.items()):
        enumeration_table.append(name)
        for i, s in sorted(values.items()):
            enumeration_table.append('', s, i)

    print('\n\n - - - - - - - Enumerations\n')
    print(enumeration_table)


def _entry_point():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return main()
