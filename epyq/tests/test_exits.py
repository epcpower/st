import subprocess
import sys
import textwrap

import PyQt5.QtWidgets
import pytest


@pytest.mark.manual
def test_exits(qtbot):
    PyQt5.QtWidgets.QMessageBox.information(
        None,
        'EPyQ Manual Test Instructions',
        textwrap.dedent('''\
            Testing to confirm the application actually terminates.
            You have 30 seconds.
        
            1. Open device
            2. Close application'''
        ),
    )

    subprocess.check_call(
        [
            sys.executable,
            '-c',
            'import sys; import epyq.__main__; sys.exit(epyq.__main__.main())',
        ],
        # TODO: returns immediately
        # [os.path.join(epyqlib.tests.common.scripts_path, 'epyq.exe')],
        timeout=30,
    )
