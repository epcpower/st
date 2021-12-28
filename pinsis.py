#!/usr/bin/env python3

import argparse
import glob
import io
import os
import requests
import shutil
import stat
import subprocess
import sys

__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


# TODO: CAMPid 0238493420143087667542054268097120437916848
# http://stackoverflow.com/a/21263493/228539
def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    if os.path.isdir(name):
        os.rmdir(name)
    else:
        os.remove(name)


def rmtree(path, retries=5):
    for remaining in reversed(range(retries)):
        if os.path.isdir(path):
            try:
                shutil.rmtree(path, onerror=del_rw)
            except PermissionError as e:
                if remaining == 0:
                    raise Exception('Unable to delete: {}'.format(path)) from e
            else:
                break


parser =  argparse.ArgumentParser()
installer_group = parser.add_mutually_exclusive_group(required=True)
installer_group.add_argument('--qtifw', action='store_true')
installer_group.add_argument('--nsis', action='store_true')

args = parser.parse_args()

peak = 'PCANBasic.dll'
r = requests.get('http://www.peak-system.com/produktcd//Develop/PC%20interfaces/Windows/PCAN-Basic%20API/x64/PCANBasic.dll')
b = io.BytesIO(r.content)
with open(peak, 'wb') as f:
    f.write(b.read())

rmtree(os.path.join('dist'))

resource_files = glob.glob(os.path.join('sub', 'epyqlib', 'epyqlib', 'resources', '*.qrc'))
for f in resource_files:
    print('Starting pyrcc5')
    subprocess.call(
        [
            os.path.join('.venv', 'Scripts', 'pyrcc5'),
            '-o', os.path.splitext(f)[0] + '.py',
            f
        ]
    )

pyinstaller = os.path.join('.venv', 'Scripts', 'pyinstaller')
spec_file = os.path.join('installer', 'pyinstaller.spec')
subprocess.check_call([pyinstaller, spec_file])

shutil.copy(
    os.path.join('installer', 'api-ms-win-core-synch-l1-2-0.dll'),
    os.path.join('dist', 'epyq', 'api-ms-win-core-synch-l1-2-0.dll.win7'),
)

if args.nsis:
    makensis = os.path.join('c:/', 'program files (x86)', 'nsis', 'bin', 'makensis.exe')
    nsi_script = os.path.join('installer', 'script.nsi')
    subprocess.check_call([makensis, nsi_script])
elif args.qtifw:
    subprocess.check_call([
        sys.executable,
        os.path.join('sub', 'epyqlib', 'deploy_win.py'),
        '--name',
        'epyq',
    ])
