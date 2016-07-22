#!/usr/bin/env python3

# TODO: CAMPid 98852142341263132467998754961432
import epyq.tee
import os
import sys

log = open(os.path.join(os.getcwd(), 'build.log'), 'w', encoding='utf-8')

if sys.stdout is None:
    sys.stdout = log
else:
    sys.stdout = epyq.tee.Tee([sys.stdout, log])

if sys.stderr is None:
    sys.stderr = log
else:
    sys.stderr = epyq.tee.Tee([sys.stderr, log])


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

proc = Popen(
    args=[
        'c:/python34/python.exe',
        'epyq/generaterevision.py'
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
    )

for line in proc.stdout:
    sys.stdout.write(str(line, 'UTF-8'))

proc.wait()

try:
    shutil.rmtree('venv')
except FileNotFoundError:
    pass

proc = Popen(
    args=[
        'c:/python34/python.exe',
        'venv.py'
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
    )

for line in proc.stdout:
    sys.stdout.write(str(line, 'UTF-8'))

proc.wait()

qt_root = 'C:/qt/Qt5.5.1'

env = os.environ

env['SYSROOT'] = 'C:/epc/t/134/pqd/sysroot'
env['INTERPRETER'] = 'C:/Python34/python.exe'
env['CL'] = '/MP'
env['PATH'] = ';'.join([
        qt_root + '/5.5/msvc2010/bin',
        qt_root + '/qtbase/bin',
        qt_root + '/gnuwin32/bin',
        os.environ['PATH']
    ])
env['QMAKESPEC'] = 'win32-msvc2010'

env = get_environment_from_batch_command(
    ['C:/Program Files (x86)/Microsoft Visual Studio 10.0/VC/vcvarsall.bat', 'x86'],
    initial=env
)

try:
    shutil.rmtree('build')
except FileNotFoundError:
    pass

proc = Popen(
    args=[
        'c:/python34/scripts/pyqtdeploycli.exe',
        '--project', 'epyq.pdy',
        'build'
    ],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
    )

for line in proc.stdout:
    sys.stdout.write(str(line, 'UTF-8'))

proc.wait()

proc = Popen(
    args=[
        'qmake',
    ],
    cwd='build',
    shell=True,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
    )

for line in proc.stdout:
    sys.stdout.write(str(line, 'UTF-8'))

proc.wait()

proc = Popen(
    args=[
        'nmake',
    ],
    cwd='build',
    shell=True,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
    )

for line in proc.stdout:
    sys.stdout.write(str(line, 'UTF-8'))

proc.wait()

import epyq.revision

shutil.copy(
    os.path.join('build', 'EPyQ.exe'),
    os.path.join('..', 'EPyQ-{}.exe'.format(epyq.revision.hash))
)
