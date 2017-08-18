import subprocess
import sys


def test_exits():
    subprocess.check_call(
        [
            sys.executable,
            '-c',
            '; '.join([
                'import sys',
                'import epyq.__main__',
                '''sys.exit(epyq.__main__.main(('--quit-after', '10', '--load-offline', 'test_customer')))''',
            ]),
        ],
        timeout=30,
    )


def test_exits_just_device():
    subprocess.check_call(
        [
            sys.executable,
            '-c',
            'import sys; import epyq.tests.run_device; sys.exit(epyq.tests.run_device.run())',
        ],
        # TODO: returns immediately
        # [os.path.join(epyqlib.tests.common.scripts_path, 'epyq.exe')],
        timeout=30,
    )
