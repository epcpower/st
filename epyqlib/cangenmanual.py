import logging
import os
import signal

import attr
import canmatrix.formats
import click
import docx
import docx.enum.section
import docx.enum.text
import docx.table

import epyqlib.utils.general

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


@attr.s
class Table:
    title = attr.ib()
    headings = attr.ib()
    comment = attr.ib(default='')
    rows = attr.ib(default=attr.Factory(list))

    def fill_docx(self, table):
        row = table.add_row()
        row.cells[0].merge(row.cells[-1])
        row.cells[0].text = self.title
        row.cells[0].paragraphs[0].alignment = (
            docx.enum.text.WD_PARAGRAPH_ALIGNMENT.CENTER)
        if len(self.comment) > 0:
            row = table.add_row()
            row.cells[0].merge(row.cells[-1])
            row.cells[0].text = self.comment
        row = table.add_row()
        for cell, heading in zip(row.cells, self.headings):
            cell.text = heading
        for r in self.rows:
            row = table.add_row()
            for cell, text in zip(row.cells, r):
                cell.text = str(text)


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


def doc_signals(signals):
    rows = []

    for signal in signals:
        startbit = signal.getStartbit()
        enumeration = (
            signal.enumeration
            if signal.enumeration is not None
            else ''
        )
        rows.append((
            signal.name,
            '{}/{}'.format(startbit % 8, startbit // 8),
            signal.signalsize,
            signal.factor,
            signal.unit,
            enumeration,
            signal.comment,
        ))

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

    mux_table_header = (
        'Mux Name', 'Mux ID', 'Name', 'Start', 'Length', 'Scaling', 'Units',
        'Enumeration', 'Comment'
    )
    mux_table = epyqlib.utils.general.TextTable()
    mux_table.append(mux_table_header)
    mux_table_header = mux_table_header[2:]

    frame_table_header = (
        'Frame', 'ID', 'Name', 'Start', 'Length', 'Scaling', 'Units',
        'Enumeration', 'Comment'
    )
    frame_table = epyqlib.utils.general.TextTable()
    frame_table.append(frame_table_header)
    frame_table_header = frame_table_header[2:]

    enum_table_header = ('Value', 'Name')

    frame_tables = []
    multiplex_tables = []
    enumeration_tables = []

    for frame in sorted(matrix.frames, key=lambda f: f.name):
        frame_table.append(
            frame.name,
            id_string(frame.id),
        )

        a_ft = Table(
            title='{} ({})'.format(frame.name, id_string(frame.id)),
            comment=frame.comment,
            headings=frame_table_header,
        )
        frame_tables.append(a_ft)

        mux_table.append(
            '{} ({})'.format(frame.name, id_string(frame.id)),
        )

        multiplex_signal = frame.signals[0]
        if multiplex_signal.multiplex is None:
            multiplex_signal = None

        if multiplex_signal is None:
            signals = sorted(frame.signals, key=lambda s: s.name)
            table = tabulate_signals(signals)
            frame_table.extend(table)

            a_ft.rows.extend(doc_signals(signals))
        else:
            signals = (multiplex_signal,)
            table = tabulate_signals(signals)
            frame_table.extend(table)
            a_ft.rows.extend(doc_signals(signals))
            # multiplex_signal.values = {
            #     int(k): v for k, v in multiplex_signal.values.items()
            # }

            for value, name in sorted(multiplex_signal.values.items()):
                if value == 0:
                    continue

                a_mt = Table(
                    title='{} ({}) - {} ({})'.format(
                        frame.name,
                        id_string(frame.id),
                        name,
                        value
                    ),
                    # comment=frame.comment,
                    headings=mux_table_header,
                )
                multiplex_tables.append(a_mt)

                mux_table.append(
                    '',
                    value,
                    name,
                )

                signals = tuple(
                    s for s in frame.signals
                    if s.multiplex == value and s.name != 'ReadParam_command'
                )

                mux_table.extend(tabulate_signals(sorted(
                    signals, key=lambda s: s.name)))

                a_mt.rows.extend(doc_signals(signals))

    print('\n\n - - - - - - - Multiplexes\n')
    print(mux_table)

    print('\n\n - - - - - - - Frames\n')
    print(frame_table)

    enumeration_table = epyqlib.utils.general.TextTable()
    enumeration_table.append('Name', '', 'Value')
    for name, values in sorted(matrix.valueTables.items()):
        a_et = Table(
            title=name,
            headings=enum_table_header,
        )
        enumeration_tables.append(a_et)
        a_et.rows.extend(sorted(values.items()))

        enumeration_table.append(name)
        for i, s in sorted(values.items()):
            enumeration_table.append('', s, i)

    print('\n\n - - - - - - - Enumerations\n')
    print(enumeration_table)

    doc = docx.Document()
    for tables in (frame_tables, multiplex_tables, enumeration_tables):
        # section = doc.add_section()
        # section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
        for table in tables:
            doc_table = doc.add_table(rows=0, cols=len(table.headings))
            doc.add_paragraph()

            table.fill_docx(doc_table)
    doc.save('doc.docx')
    pass


def _entry_point():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return main()
