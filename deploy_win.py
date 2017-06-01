#!/usr/bin/env python3

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


# TODO: CAMPid 98852142341263132467998754961432
import epyq
import epyqlib.tee
import glob
import io
import json
import os
import stat
import sys

log = open(os.path.join(os.getcwd(), 'build.log'), 'w', encoding='utf-8')

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyqlib.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyqlib.tee.Tee([sys.stderr, log])


# http://stackoverflow.com/a/2214292/228539
import sys
import subprocess
import itertools

def validate_pair(ob):
    try:
        if not (len(ob) == 2):
            print("Unexpected result:", ob, file=sys.stderr)
            raise ValueError
    except:
        return False
    return True

def consume(iter):
    try:
        while True: next(iter)
    except StopIteration:
        pass

def get_environment_from_batch_command(env_cmd, initial=None):
    """
    Take a command (either a single command or list of arguments)
    and return the environment created after running that command.
    Note that if the command must be a batch file or .cmd file, or the
    changes to the environment will not be captured.

    If initial is supplied, it is used as the initial environment passed
    to the child process.
    """
    if not isinstance(env_cmd, (list, tuple)):
        env_cmd = [env_cmd]
    # construct the command that will alter the environment
    env_cmd = subprocess.list2cmdline(env_cmd)
    # create a tag so we can tell in the output when the proc is done
    tag = bytes('Done running command', 'UTF-8')
    # construct a cmd.exe command to do accomplish this
    cmd = 'cmd.exe /s /c "{env_cmd} && echo "{tag}" && set"'.format(**vars())
    # launch the process
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=initial)
    # parse the output sent to stdout
    lines = proc.stdout
    # consume whatever output occurs until the tag is reached
    consume(itertools.takewhile(lambda l: tag not in l, lines))
    # define a way to handle each KEY=VALUE line
    handle_line = lambda l: str(l, 'UTF-8').rstrip().split('=',1)
    # parse key/values into pairs
    pairs = map(handle_line, lines)
    # make sure the pairs are valid
    valid_pairs = filter(validate_pair, pairs)
    # construct a dictionary of the pairs
    result = dict(valid_pairs)
    # let the process finish
    proc.communicate()
    return result


import argparse
import os
import shutil
import tempfile
import zipfile

import subprocess


parser =  argparse.ArgumentParser()
parser.add_argument('--device-file', '-d', type=str, default=None)
parser.add_argument('--name', '-n', type=str, required=True)

args = parser.parse_args()

def runit(args, cwd=None, env=None):
    proc = subprocess.Popen(
        args=args,
        cwd=cwd,
        shell=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
        )

    for line in proc.stdout:
        sys.stdout.write(str(line, 'UTF-8'))

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, args)

qt_root = os.path.join('C:/', 'Qt', 'Qt5.7.0')

env = os.environ

env['INTERPRETER'] = sys.executable

# TODO: CAMPid 0238493420143087667542054268097120437916848
# http://stackoverflow.com/a/21263493/228539
def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    if os.path.isdir(name):
        os.rmdir(name)
    else:
        os.remove(name)

if os.path.isdir('build'):
    shutil.rmtree('build', onerror=del_rw)

# TODO: CAMPid 9811163648546549994313612126896
def pip_install(package, no_ssl_verify, site=False, parameters=[]):
    pip_parameters = ['install']
    if no_ssl_verify:
        pip_parameters.append('--index-url=http://pypi.python.org/simple/')
        pip_parameters.append('--trusted-host')
        pip_parameters.append('pypi.python.org')
    if not site:
        pip_parameters.append('--user')
    pip_parameters.extend(parameters)
    pip_parameters.append(package)
    return pip.main(pip_parameters)

resource_files = glob.glob(os.path.join('sub', 'epyqlib', 'epyqlib', 'resources', '*.qrc'))
for f in resource_files:
    print('Starting pyrcc5')
    runit(
        args=[
            'pyrcc5',
            '-o', os.path.splitext(f)[0] + '.py',
            f
        ]
    )


files = []

if args.device_file is not None:
    pip_install('gitpython', no_ssl_verify=False, site=True)
    os.environ['PATH'] = os.pathsep.join([
        os.environ['PATH'],
        os.path.join('c:/', 'Program Files', 'Git', 'bin')
    ])

    import epyqlib.collectdevices

    for group in ('release', 'factory', 'dev'):
        with tempfile.TemporaryDirectory() as device_dir:
            epyqlib.collectdevices.main(
                args=[],
                device_files=[args.device_file],
                output_directory=device_dir,
                groups=[group]
            )

            zip_path = os.path.join('..', '{}-{}-{}.zip'.format(
                args.name, group, epyq.__version_tag__))
            with zipfile.ZipFile(file=zip_path, mode='w') as zip:
                for path in glob.glob(os.path.join(device_dir, '*.epz')):
                    zip.write(filename=path,
                              arcname=os.path.basename(path)
                    )


shutil.copytree('installer', os.path.join('build', 'installer'))

def copy_files(src, dst):
    os.makedirs(dst)
    src_files = os.listdir(src)
    for file_name in src_files:
        full_file_name = os.path.join(src, file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, dst)
        else:
            shutil.copytree(full_file_name, os.path.join(dst, file_name))

copy_files(os.path.join('dist', 'epyq'), os.path.join('build', 'installer', 'packages', 'com.epcpower.st', 'data'))

shutil.copy('COPYING', os.path.join('build', 'installer', 'packages', 'com.epcpower.st', 'meta', 'epyq-COPYING.txt'))


third_party_license = os.path.join(
    'build', 'installer', 'packages', 'com.epcpower.st', 'meta',
    'third_party-LICENSE.txt'
)

def write_license(name, contents, url, collapse_double_newlines):
        print('Appending {} to third party license file'.format(name))
        header = '  == ' + name + ' '
        header += '=' * ((widest + 6 + minimum) - len(header))
        out.write(header + '\n\n')

        if collapse_double_newlines:
            contents = contents.replace('\n\n', '\n')
        out.write(contents)
        out.write('\n\n\n')

pip_install('requests', no_ssl_verify=False, site=True)
import requests

pyqt5_license_path = os.path.join('build', 'PyQt5_LICENSE')
qt_license_path = os.path.join('build', 'Qt_LICENSE')
zipped_licenses = (
    (
        pyqt5_license_path,
        'https://sourceforge.net/projects/pyqt/files/PyQt5/PyQt-5.8.2/PyQt5_gpl-5.8.2.zip',
        'PyQt5_gpl-5.8.2/LICENSE',
    ),
)

for zipped in zipped_licenses:
    r = requests.get(zipped[1])
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(zipped[2]) as i:
            with open(zipped[0], 'wb') as o:
                o.write(i.read())

# The Qt Installer Framework (QtIFW) likes to do a few things to license files...
#  * '\n' -> '\r\n'
#   * even such that '\r\n' -> '\r\r\n'
#  * Recodes to something else (probably cp-1251)
#
# So, we'll just try force '\n' can become something still acceptable after being messed with
if 'PYTHON' not in os.environ:
    os.environ['PYTHON'] = os.path.join('c:/', 'Program Files (x86)', 'python35-32')
with open(third_party_license, 'w', encoding='utf-8', newline='\n') as out:
    licenses = [
        ('bitstruct', ('venv', 'src', 'bitstruct', 'LICENSE'), None, False),
        ('canmatrix', ('venv', 'src', 'canmatrix', 'LICENSE'), None, False),
        ('python-can', ('venv', 'src', 'python-can', 'LICENSE.txt'), None, False),
        ('Python', (os.environ['PYTHON'], 'LICENSE.txt'), None, False),
        ('PyQt5', (pyqt5_license_path,), None, False),
        ('Qt', (), 'https://www.gnu.org/licenses/gpl-3.0.txt', True),
        ('PEAK-System', ('installer', 'peak-system.txt'), 'http://www.peak-system.com/produktcd/Develop/PC%20interfaces/Windows/API-ReadMe.txt', False),
        ('Microsoft Visual C++ Build Tools', ('installer', 'microsoft_visual_cpp_build_tools_eula.html'), 'https://www.visualstudio.com/en-us/support/legal/mt644918', False),
        ('Microsoft Visual C++ 2010 x86 Redistributable SP1', ('installer', 'microsoft_visual_cpp_2010_x86_redistributable_setup_sp1.rtf'), None, False),
        ('Qt5Reactor', ('venv', 'src', 'qt5reactor', 'LICENSE'), None, False),
        ('win32', ('venv', 'Lib', 'site-packages', 'win32', 'license.txt'), None, False),
        ('win32com', ('venv', 'Lib', 'site-packages', 'win32com', 'License.txt'), None, False),
        ('constantly', (), 'https://github.com/twisted/constantly/raw/master/LICENSE', False),
        ('incremental', (), 'https://github.com/hawkowl/incremental/raw/master/LICENSE', False),
        ('twisted', (), 'https://github.com/twisted/twisted/raw/trunk/LICENSE', False),
        ('zope.interface', (), 'https://github.com/zopefoundation/zope.interface/raw/master/LICENSE.txt', False),
        ('ASI TICOFF', ('sub', 'epyqlib', 'epyqlib', 'ticoff.asi_license.txt'), 'https://gist.github.com/eliotb/1073231', False),
        ('pyelftools', ('venv', 'src', 'pyelftools', 'LICENSE'), None, False),
        ('attrs', ('installer', 'attrs.txt'), 'https://raw.githubusercontent.com/hynek/attrs/5516d5452c76416b3fea0c9d9f2b7505fae82c2b/LICENSE', False),
        ('FontAwesome', (), 'http://scripts.sil.org/OFL', False),
    ]

    widest = max([len(name) for name, _, _, _ in licenses])
    minimum = 4
    for name, path, url, collapse_double_newlines in licenses:
        if len(path) == 0:
            contents = requests.get(url).text
            write_license(name, contents, url, collapse_double_newlines)
        else:
            encodings = [None, 'utf-8']

            in_path = os.path.expandvars(os.path.join(*path))

            for encoding in encodings:
                try:
                    with open(in_path, encoding=encoding) as in_file:
                        contents = in_file.read()
                except UnicodeDecodeError:
                    pass
                else:
                    write_license(name, contents, url, collapse_double_newlines)
                    break
            else:
                raise Exception("Unable to parse '{}' without an error".format(in_path))

config = os.path.join('build', 'installer', 'config')
ico = 'icon.ico'
png = 'icon.png'

to_copy = [
    (ico, ''),
    (png, ''),
    (png, 'icon_duplicate.png'),
    (png, 'aicon.png'),
    (png, 'wicon.png')
]

for source, destination in to_copy:
    shutil.copy(os.path.join('epyq', source), os.path.join(config, destination))


runit(
    args=[
        sys.executable,
        os.path.join('installer', 'config.py'),
        '--template', os.path.join('installer', 'config', 'config_template.xml'),
        '--output', os.path.join('installer', 'config', 'config.xml')
    ],
    cwd='build'
)

base = os.path.join('build', 'installer', 'packages')
for path in os.listdir(base):
    package_file = os.path.join(base, path, 'meta', 'package.xml')
    runit(
        args=[
            sys.executable,
            os.path.join('installer', 'config.py'),
            '--template', package_file,
            '--output', package_file
        ]
    )

runit(args=[
    os.path.join('c:/', 'Qt', 'QtIFW2.0.1', 'bin', 'binarycreator.exe'),
    '-c', os.path.join('installer', 'config', 'config.xml'),
    '-p', os.path.join('installer', 'packages'),
    'epyq.exe'],
    cwd='build'
)

installer_file = '{}-{}.exe'.format(args.name, epyq.__version_tag__)
shutil.copy(
    os.path.join('build', 'epyq.exe'),
    os.path.join('..', installer_file)
)

print('Created {}'.format(installer_file))
