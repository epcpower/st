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
import os
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

def runit(args, cwd, env=None):
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

shutil.rmtree('build', ignore_errors=True)

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

import epyq.revision

shutil.copy(
    os.path.join('build', 'EPyQ.exe'),
    os.path.join('..', 'EPyQ-{}.exe'.format(epyq.revision.hash))
)
