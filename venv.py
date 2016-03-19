#!/usr/bin/env python3

import argparse
from distutils.core import run_setup
import os
import pip
import subprocess
import sys

# TODO: redo as a bootstrap script
#       https://virtualenv.readthedocs.org/en/latest/reference.html#extending-virtualenv

parser = argparse.ArgumentParser()
parser.add_argument('--pyqt5')
parser.add_argument('--pyqt5-plugins')
parser.add_argument('--bin')
parser.add_argument('--activate')
parser.add_argument('--no-ssl-verify', action='store_true')
parser.add_argument('--virtualenv', '--venv', default='venv')
parser.add_argument('--in-virtual', action='store_true', default=False)

args = parser.parse_args()

# TODO: let this be the actual working directory
myfile = os.path.realpath(__file__)
mydir = os.path.dirname(myfile)

if not args.in_virtual:
    try:
        os.mkdir(args.virtualenv)
    except FileExistsError:
        print('')
        print('')
        print('    Directory already exists and must be deleted to create the virtual environment')
        print('')
        print('        {args.virtualenv}'.format(**locals()))
        print('')

        sys.exit(1)

    try:
        import PyQt5.QtCore
    except ImportError:
        print('')
        print('')
        print('    PyQt5 not installed:')
        print('')

        if sys.platform == 'win32':
            print('        https://riverbankcomputing.com/software/pyqt/download5')
            print('')
            print('        Select the appropriate architecture to match your python install')
        else:
            print('        Use your package manager to install')
            print('')
            print('        e.g. sudo apt-get install python3-pyqt5')
        print('')

        sys.exit(1)

    if sys.platform not in ['win32', 'linux']:
        raise Exception("Unsupported sys.platform: {}".format(sys.platform))

    if sys.platform == 'win32':
        bin = os.path.join(args.virtualenv, 'Scripts')
    else:
        bin = os.path.join(args.virtualenv, 'bin')

    pyqt5 = os.path.dirname(PyQt5.__file__)
    pyqt5_plugins = PyQt5.QtCore.QLibraryInfo.location(
        PyQt5.QtCore.QLibraryInfo.PluginsPath)

    activate = os.path.join(bin, 'activate')

    pip.main(['install', '--user', 'virtualenv'])

    virtualenv_command = [sys.executable, '-m', 'virtualenv', '--system-site-packages', args.virtualenv]
    returncode = subprocess.call(virtualenv_command)

    if returncode != 0:
        raise Exception("Received return code {} when running {}"
                        .format(result.returncode, virtualenv_command))

    virtualenv_python = os.path.realpath(os.path.join(bin, 'python'))
    virtualenv_python_command = [virtualenv_python,
                                 myfile,
                                 '--pyqt5', pyqt5,
                                 '--pyqt5-plugins', pyqt5_plugins,
                                 '--bin', bin,
                                 '--activate', activate,
                                 '--in-virtual']
    if args.no_ssl_verify:
        virtualenv_python_command.append('--no-ssl-verify')

    returncode = subprocess.call(virtualenv_python_command)

    sys.exit(returncode)
else:
    def setup(path):
        backup = os.getcwd()
        os.chdir(path)
        run_setup(os.path.join(path, 'setup.py'), script_args=['develop'])
        os.chdir(backup)

    src = os.path.join(mydir, args.virtualenv, 'src')
    os.makedirs(src, exist_ok=True)

    zip_repos = {
        'python-can': 'https://bitbucket.org/altendky/python-can/get/'
                      'a8973411ef9c.zip',
        'canmatrix': 'https://github.com/ebroecker/canmatrix/archive/'
                     '5b8f2855578bcd5373825e40df03bf0f7f9af69d.zip',
        'bitstruct': 'https://github.com/altendky/bitstruct/archive/'
                     'b0b13785630dc10e749f89f035deb2b9be18601e.zip'
    }

#    pip.main(['install', 'gitpython'])
#    import git
#
#    git_repos = {
#        'canmatrix': 'https://github.com/ebroecker/canmatrix.git',
#        'bitstruct': 'https://github.com/altendky/bitstruct.git'
#    }
#
#    for name, url in git_repos.items():
#        dir = os.path.join(src, name)
#        git.Repo.clone_from(url, dir)
#        setup(dir)

    pip.main(['install', 'requests'])
    import requests
    import zipfile
    import io
    import shutil
    for name, url in zip_repos.items():
        try:
            response = requests.get(url, verify=not args.no_ssl_verify)
        except requests.exceptions.SSLError:
            print('')
            print('        SSL error occurred while requesting:')
            print('            {}'.format(url))
            print('')
            print('        You probably want to use --no-ssl-verify')
            print('')

            sys.exit(1)

        zip_data = io.BytesIO()
        zip_data.write(response.content)
        zip_file = zipfile.ZipFile(zip_data)
        zip_dir = os.path.split(zip_file.namelist()[0])[0]
        zip_file.extractall(path=src)
        shutil.move(os.path.join(src, zip_dir),
                    os.path.join(src, name))
        setup(os.path.join(src, name))

    # TODO: Figure out why this can't be moved before other installs
    #       Dependencies maybe?
    setup(mydir)

    with open(os.path.join(args.bin, 'qt.conf'), 'w') as f:
        content = [
            '[Paths]',
            'Prefix = "{}"'.format(args.pyqt5),
            'Binaries = "{}"'.format(args.pyqt5)
        ]

        if sys.platform == 'win32':
            content = [l.replace('\\', '/') for l in content]

        if sys.platform == 'linux':
            content.append('Plugins = "{}"'.format(args.pyqt5_plugins))

        f.write('\n'.join(content) + '\n')

    activate = args.activate
    if sys.platform == 'win32':
        with open(os.path.join(mydir, 'activate.bat'), 'w') as f:
            activate = activate.replace('\\', '/')
            f.write('set PYQTDESIGNERPATH="{root}\epyq;{root}\epyq\widgets"\n'
                    .format(root=mydir))
            f.write('set PYTHONPATH="{root}\epyq;{root}\epyq\widgets"\n'
                    .format(root=mydir))
            f.write('{}\n'.format(activate))

    with open(os.path.join(mydir, 'activate'), 'w', newline='') as f:
        f.write('export PYQTDESIGNERPATH="{root}/epyq:{root}/epyq/widgets"\n'
                .format(root=mydir))
        f.write('source {}\n'.format(activate))

    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.LoadLibrary("PCANBasic")
        except OSError:
            print('')
            print('')
            print('    Unable to load PCANBasic.dll, it is recommended you')
            print('    install the PEAK drivers: ')
            print('')
            print('        http://www.peak-system.com/produktcd/Drivers/PeakOemDrv.exe')

    print('')
    print('')
    print('    To use the new virtualenv:')
    print('')
    print('        posix: source activate')
    if sys.platform == 'win32':
        print('        win32: activate')
    print('')

    sys.exit(0)
