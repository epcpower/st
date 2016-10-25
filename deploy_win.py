#!/usr/bin/env python3

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
import epyqlib.tee
import glob
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


import os
import shutil

from subprocess import Popen

def runit(args, cwd=None, env=None):
    proc = Popen(
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

runit(
    args=[
        sys.executable,
        os.path.join('..', 'sub','epyqlib', 'epyqlib',
	             'generaterevision.py')
    ],
    cwd='epyq'
)


qt_root = os.path.join('C:/', 'Qt', 'Qt5.7.0')

env = os.environ

env['INTERPRETER'] = sys.executable
env['CL'] = '/MP'
env['PATH'] = ';'.join([
        os.path.join(qt_root, '5.7', 'msvc2015', 'bin'),
        os.environ['PATH']
    ])
env['QMAKESPEC'] = 'win32-msvc2015'

env = get_environment_from_batch_command(
    [
        os.path.join('C:/', 'Program Files (x86)', 'Microsoft Visual Studio 14.0', 'VC', 'vcvarsall.bat'),
        'x86'
    ],
    initial=env
)

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
def pip_install(package, no_ssl_verify, site=False):
    pip_parameters = ['install']
    if no_ssl_verify:
        pip_parameters.append('--index-url=http://pypi.python.org/simple/')
        pip_parameters.append('--trusted-host')
        pip_parameters.append('pypi.python.org')
    if not site:
        pip_parameters.append('--user')
    pip_parameters.append(package)
    return pip.main(pip_parameters)

pip_install('pyqtdeploy', no_ssl_verify=False, site=True)

runit(
    args=[
        os.path.expandvars(os.path.join(
            '%APPDATA%', 'Python', 'Python35', 'Scripts', 'pyqtdeploycli.exe'
        )),
        '--project', 'epyq.pdy',
        'build'
    ],
    env=env,
)

runit(
    args=[
        'qmake',
    ],
    cwd='build',
    env=env,
)

runit(args='nmake', cwd='build', env=env)

runit(args=[
    os.path.join('c:/', 'Qt', 'Qt5.7.0', '5.7', 'msvc2015', 'bin', 'windeployqt.exe'),
    os.path.join('build', 'release', 'epyq.exe')
])

files = []

pip_install('gitpython', no_ssl_verify=False, site=True)
os.environ['PATH'] = os.pathsep.join([
    os.environ['PATH'],
    os.path.join('c:/', 'Program Files', 'Git', 'bin')
])
import epyqlib.collectdevices

collected_devices_directory = os.path.join('build', 'devices')
epyqlib.collectdevices.main(
    device_files=[os.path.join('installer', 'devices.json')],
    output_directory=collected_devices_directory
)
files.extend(glob.glob(os.path.join(collected_devices_directory, '*.epz')))

for extension in ['sym', 'epc', 'epz', 'py', 'ui']:
    files.extend(glob.glob('*.' + extension))
files.append(os.path.join('c:/', 'Program Files (x86)', 'Microsoft Visual Studio 14.0', 'VC', 'redist', 'x86', 'Microsoft.VC140.CRT', 'msvcp140.dll'))
files.append(os.path.join('c:/', 'Windows', 'SysWOW64', 'PCANBasic.dll'))
for file in files:
    shutil.copy(file, os.path.join('build', 'release'))

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

copy_files(os.path.join('build', 'release'), os.path.join('build', 'installer', 'packages', 'com.epcpower.st', 'data'))

shutil.copy('COPYING', os.path.join('build', 'installer', 'packages', 'com.epcpower.st', 'meta', 'epyq-COPYING.txt'))


third_party_license = os.path.join(
    'build', 'installer', 'packages', 'com.epcpower.st', 'meta',
    'third_party-LICENSE.txt'
)

with open(third_party_license, 'w', encoding='utf-8') as out:
    licenses = [
        ('bitstruct', ('venv', 'src', 'bitstruct', 'LICENSE'), None),
        ('canmatrix', ('venv', 'src', 'canmatrix', 'LICENSE'), None),
        ('python-can', ('venv', 'src', 'python-can', 'LICENSE.txt'), None),
        ('Python', ('c:/', 'Program Files (x86)', 'python35-32', 'LICENSE.txt'), None),
        ('PyQt5', ('$SYSROOT', '..', 'src', 'PyQt5_gpl-5.7', 'LICENSE'), None),
        ('Qt', ('c:/', 'Qt', 'Qt5.7.0', 'Licenses', 'LICENSE'), None),
        ('PEAK-System', ('installer', 'peak-system.txt'), 'http://www.peak-system.com/produktcd/Develop/PC%20interfaces/Windows/API-ReadMe.txt'),
        ('Microsoft Visual C++ Build Tools', ('installer', 'microsoft_visual_cpp_build_tools_eula.html'), 'https://www.visualstudio.com/en-us/support/legal/mt644918')
    ]

    widest = max([len(name) for name, _, _ in licenses])
    minimum = 4
    for name, path, url in licenses:
        print('Appending {} to third party license file'.format(name))
        header = '  == ' + name + ' '
        header += '=' * ((widest + 6 + minimum) - len(header))
        out.write(header + '\n\n')

        encodings = [None, 'utf-8']
        
        in_path = os.path.expandvars(os.path.join(*path))
        
        for encoding in encodings:
            try:
                with open(in_path, encoding=encoding) as in_file:
                    if url is not None:
                        out.write(url + '\n\n')

                    contents = in_file.read()
                    out.write(contents)
                    out.write('\n\n\n')
            except UnicodeDecodeError:
                pass
            else:
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

runit(args=[
    os.path.join('c:/', 'Qt', 'QtIFW2.0.3', 'bin', 'binarycreator.exe'),
    '-c', os.path.join('installer', 'config', 'config.xml'),
    '-p', os.path.join('installer', 'packages'),
    'epyq.exe'],
    cwd='build'
)

import epyq.revision

installer_file = 'epyq-{}.exe'.format(epyq.revision.hash)
shutil.copy(
    os.path.join('build', 'epyq.exe'),
    os.path.join('..', installer_file)
)

print('Created {}'.format(installer_file))