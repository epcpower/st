#!/usr/bin/env python3

import argparse
from collections import OrderedDict
import os
import platform
import shutil
import subprocess
import sys

# TODO: CAMPid 097541134161236179854863478319
try:
    import pip
except ImportError:
    print('')
    print('')
    print('    pip not installed:')
    print('')
    print('        Use your package manager to install')
    print('')
    print('        e.g. sudo apt-get install python3-pip')
    print('')

    sys.exit(1)

# TODO: redo as a bootstrap script
#       https://virtualenv.readthedocs.org/en/latest/reference.html#extending-virtualenv

parser = argparse.ArgumentParser()
parser.add_argument('--bin')
parser.add_argument('--activate')
parser.add_argument('--no-ssl-verify', action='store_true')
parser.add_argument('--virtualenv', '--venv', default='venv')
parser.add_argument('--in-virtual', action='store_true', default=False)
parser.add_argument('--rebuild', action='store_true')
parser.add_argument('--no-designer', action='store_true')

args = parser.parse_args()

# TODO: let this be the actual working directory
myfile = os.path.realpath(__file__)
mydir = os.path.dirname(myfile)

# TODO: CAMPid 9811163648546549994313612126896
def pip_install(package, no_ssl_verify, virtual=False):
    pip_parameters = ['install']
    if no_ssl_verify:
        pip_parameters.append('--index-url=http://pypi.python.org/simple/')
        pip_parameters.append('--trusted-host')
        pip_parameters.append('pypi.python.org')
    if not virtual:
        pip_parameters.append('--user')
    pip_parameters.append(package)
    if pip.main(pip_parameters):
        raise Exception('Failed to install {}'.format(package))

if not args.in_virtual:
    if args.rebuild:
        shutil.rmtree(args.virtualenv, ignore_errors=True)

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

    if sys.platform not in ['win32', 'linux']:
        raise Exception("Unsupported sys.platform: {}".format(sys.platform))

    if sys.platform == 'win32':
        bin = os.path.join(args.virtualenv, 'Scripts')
    else:
        bin = os.path.join(args.virtualenv, 'bin')

    activate = os.path.join(bin, 'activate')

    pip_install('virtualenv', args.no_ssl_verify)

    virtualenv_command = [sys.executable, '-m', 'virtualenv', '--system-site-packages', args.virtualenv]
    returncode = subprocess.call(virtualenv_command)

    if returncode != 0:
        raise Exception("Received return code {} when running {}"
                        .format(result.returncode, virtualenv_command))

    virtualenv_python = os.path.realpath(os.path.join(bin, 'python'))
    virtualenv_python_command = [virtualenv_python,
                                 myfile,
                                 '--bin', bin,
                                 '--activate', activate,
                                 '--in-virtual']
    if args.no_ssl_verify:
        virtualenv_python_command.append('--no-ssl-verify')

    if args.no_designer:
        virtualenv_python_command.append('--no-designer')

    returncode = subprocess.call(virtualenv_python_command)

    sys.exit(returncode)
else:
    def setup(path):
        backup = os.getcwd()
        os.chdir(path)
        subprocess.run([sys.executable, os.path.join(path, 'setup.py'), 'develop'])
        os.chdir(backup)

    src = os.path.join(mydir, args.virtualenv, 'src')
    os.makedirs(src, exist_ok=True)

    packages = [
        'pyqt5'
    ]

    if not args.no_designer:
        arch = platform.architecture()
        if arch[1].lower().startswith('win'):
            packages.append('pyqt5-tools')

    for package in packages:
        pip_install(package, args.no_ssl_verify, virtual=True)

    zip_repos = OrderedDict([
        ('python-can', 'https://bitbucket.org/altendky/python-can/get/'
                      '076a7864f1e292647a501ae60ea90f62b5703d71.zip'),
        ('canmatrix', 'https://github.com/ebroecker/canmatrix/archive/'
                     '0b2c6679b732b0849484d958d63782526a18f6ca.zip'),
        ('bitstruct', 'https://github.com/altendky/bitstruct/archive/'
                     '129a72e290c533654a91bd556b1d4b0822df423f.zip')
    ])

#    pip_install('gitpython', args.no_ssl_verify)
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

    pip_install('git-app-version', args.no_ssl_verify, virtual=True)
    pip_install('requests', args.no_ssl_verify, virtual=True)
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
        try:
            shutil.rmtree(os.path.join(src, name))
        except FileNotFoundError:
            pass
        shutil.move(os.path.join(src, zip_dir),
                    os.path.join(src, name))
        # TODO: remove this because it is a goofy workaround for the issue being discussed
        #       over in https://github.com/ebroecker/canmatrix/commit/084e1e01eb750adb46e9e33a0d94fadcbf2cc896
        if name == 'canmatrix':
            import shutil
            shutil.copy('canmatrix.setup.py', os.path.join('venv', 'src', 'canmatrix', 'setup.py'))
        setup(os.path.join(src, name))

    # TODO: Figure out why this can't be moved before other installs
    #       Dependencies maybe?
    setup(mydir)

    with open(os.path.join(args.bin, 'qt.conf'), 'w') as f:
        import PyQt5.QtCore
        pyqt5 = os.path.dirname(PyQt5.__file__)
        pyqt5_plugins = PyQt5.QtCore.QLibraryInfo.location(
            PyQt5.QtCore.QLibraryInfo.PluginsPath)

        content = [
            '[Paths]',
            'Prefix = "{}"'.format(pyqt5),
            'Binaries = "{}"'.format(pyqt5)
        ]

        if sys.platform == 'win32':
            content = [l.replace('\\', '/') for l in content]

        if sys.platform == 'linux':
            content.append('Plugins = "{}"'.format(pyqt5_plugins))

        f.write('\n'.join(content) + '\n')

    activate = args.activate
    if sys.platform == 'win32':
        path_variables = OrderedDict([
            ('PYQTDESIGNERPATH', [
                ['epyq'],
                ['epyq', 'widgets']
            ]),
            ('PYTHONPATH', [
                ['']
            ])
        ])

        set_commands = []
        for name, paths in path_variables.items():
            command = 'set {}='.format(name)
            paths = [os.path.join('%cd%', *p) for p in paths]
            command += ';'.join(paths)
            set_commands.append(command)
        
        with open(os.path.join(mydir, 'activate.bat'), 'w') as f:
            activate = activate.replace('\\', '/')
            for command in set_commands:
                f.write(command + '\n')
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
