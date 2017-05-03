#!/usr/bin/env python3

import os
import shutil
import stat
import subprocess

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


rmtree(os.path.join('dist'))
pyinstaller = os.path.join('venv', 'Scripts', 'pyinstaller')
spec_file = os.path.join('installer', 'pyinstaller.spec')
subprocess.check_call([pyinstaller, spec_file])


makensis = os.path.join('c:/', 'program files (x86)', 'nsis', 'bin', 'makensis.exe')
nsi_script = os.path.join('installer', 'script.nsi')
subprocess.check_call([makensis, nsi_script])
