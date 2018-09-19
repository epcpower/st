from __future__ import print_function

import argparse
import errno
import functools
import os
import os.path
import shlex
import shutil
import stat
import subprocess
import sys
import time


this = os.path.normpath(os.path.abspath(__file__))
project_root = os.path.dirname(this)
venv_path = os.path.join(project_root, 'venv')
venv_common_bin = os.path.join(venv_path, 'Scripts')
venv_python = os.path.join(venv_common_bin, 'python')

lib_src = os.path.join(project_root, 'src', 'libs')

requirements_stem = os.path.join(project_root, 'requirements')

py3 = sys.version_info[0] == 3


class ExitError(Exception):
    pass


def check_call(command, *args, **kwargs):
    command = list(command)
    print('Launching: ')
    for arg in command:
        print('    {}'.format(arg))

    return subprocess.check_call(command, *args, **kwargs)


def check_output(command, *args, **kwargs):
    command = list(command)
    print('Launching: ')
    for arg in command:
        print('    {}'.format(arg))

    return subprocess.check_output(command, *args, **kwargs)



def read_dot_env():
    env = {}
    with open(os.path.join(project_root, '.env')) as f:
        for line in f:
            line = line.strip()

            if line.startswith('#'):
                continue

            k, _, v = line.partition('=')
            env[k] = v

    return env


custom_env = {
    'PIP_SRC': lib_src,
}


def create():
    d = {
        'linux': linux_create,
        'win32': windows_create,
    }

    dispatch(d)


def common_create(
    python,
    venv_bin,
    requirements_platform,
    symlink,
):
    if os.path.exists(venv_path):
        raise ExitError(
            'venv already exists. if you know it is safe, remove it with:\n'
            '    {} rm'.format(str(this))
        )

    try:
        os.mkdir(lib_src)
    except OSError:
        pass

    env = dict(os.environ)
    env.update(read_dot_env())
    env.update(custom_env)

    check_call(
        [
            python,
            '-m', 'venv',
            '--prompt', os.path.join('st', os.path.basename(venv_path)),
            venv_path,
        ],
        cwd=project_root,
        env=env,
    )

    if symlink:
        os.symlink(venv_bin, venv_common_bin)

    check_call(
        [
            venv_python,
            '-m', 'pip',
            'install',
            '--upgrade', 'pip',
        ],
        cwd=project_root,
        env=env,
    )

    install_requirements(
        requirements_platform=requirements_platform,
    )
    download_zips(lib_src)


def install_requirements(requirements_platform):
    base = requirements_stem

    base += '.' + requirements_platform

    to_install = [base]

    env = dict(os.environ)
    env.update(read_dot_env())
    env.update(custom_env)

    for requirements in to_install:
        install_requirements_file(
            python=venv_python,
            env=env,
            requirements=requirements,
        )


def install_requirements_file(python, env, requirements):
    check_call(
        [
            python,
            '-m', 'pip',
            'install',
            '-r', requirements,
        ],
        cwd=project_root,
        env=env,
    )


def linux_create():
    venv_bin = os.path.join(venv_path, 'bin')
    common_create(
        python='python3.7',
        venv_bin=venv_bin,
        requirements_platform='linux',
        symlink=True,
    )


def windows_create():
    python_path = check_output(
        [
            'py',
            '-3.7-32',
            '-c', 'import sys; print(sys.executable)',
        ],
        cwd=str(project_root),
    )
    if py3:
        python_path = python_path.decode()
    python_path = python_path.strip()

    common_create(
        python=python_path,
        venv_bin=venv_common_bin,
        requirements_platform='windows',
        symlink=False,
    )


def rm(ignore_missing):
    try:
        rmtree(venv_path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

        if not ignore_missing:
            raise ExitError('venv not found at: {}'.format(venv_path))


def ensure(quick):
    d = {
        'linux': functools.partial(
            common_ensure,
            requirements_platform='linux',
        ),
        'win32': functools.partial(
            common_ensure,
            requirements_platform='windows',
        ),
    }

    dispatch(d, quick=quick)


def common_ensure(quick, requirements_platform):
    existed = os.path.exists(venv_path)

    if not existed:
        create()
    elif not quick:
        install_requirements(
            requirements_platform=requirements_platform,
        )
        download_zips(lib_src)


    check()

    if existed:
        print('venv already present and passes some basic checks')
    else:
        print('venv created and passed some basic checks')


def download_zips(directory):
    check_call(
        [
            venv_python,
            os.path.join(project_root, 'download_fonts.py'),
            directory,
        ],
        cwd=project_root,
    )



def clean_path(path):
    return os.path.normpath(os.path.abspath(path))


def check():
    activate = os.path.join(venv_common_bin, 'activate')
    expected_name = 'VIRTUAL_ENV'

    # try:
    with open(activate) as f:
        for line in f:
            line = line.strip()
            try:
                name, original_venv_path = line.split('=', 1)
            except ValueError:
                continue

            if name == expected_name:
                original_venv_path, = shlex.split(original_venv_path)
                break
        else:
            raise Exception(
                '{} assignment not found '
                'in "{}"'.format(expected_name,activate),
            )
    # except OSError as e:
    #     if e.errno == errno.ENOENT:
    #
    #
    #     raise

    if clean_path(venv_path) != clean_path(original_venv_path):
        raise ExitError(
            'venv should be at "{}" but has been moved to "{}"'.format(
                original_venv_path,
                venv_path,
            ),
        )

    # epyq = os.path.join(venv_common_bin, 'epyq')

    executables = []

    for executable in executables:
        try:
            check_call(
                [
                    executable,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise ExitError(
                    'required file "{}" not found'.format(executable),
                )
            elif e.errno == errno.EACCES:
                raise ExitError(
                    'required file "{}" not runnable'.format(executable),
                )

            raise


def dispatch(d, *args, **kwargs):
    for name, f in d.items():
        if sys.platform.startswith(name):
            f(*args, **kwargs)
            break
    else:
        raise ExitError('Platform not supported: {}'.format(sys.platform))


def main():
    parser = argparse.ArgumentParser(description='Create and manage the venv')
    parser.set_defaults(func=parser.print_help)
    subparsers = parser.add_subparsers()

    check_parser = subparsers.add_parser(
        'check',
        description='Do some basic validity checks against the venv',
    )
    check_parser.set_defaults(func=check)

    create_parser = subparsers.add_parser(
        'create',
        description='Create the venv',
    )
    create_parser.set_defaults(func=create)

    ensure_parser = subparsers.add_parser(
        'ensure',
        description='Create the venv if not already present',
    )
    ensure_parser.add_argument(
        '--quick',
        action='store_true',
        help=(
            'Consider valid if venv directory exists, '
            'do not make sure that all packages are installed'
        ),
    )
    ensure_parser.set_defaults(func=ensure)

    rm_parser = subparsers.add_parser('rm', description='Remove the venv')
    rm_parser.add_argument(
        '--ignore-missing',
        action='store_true',
        help='Do not raise an error if no venv is present',
    )
    rm_parser.set_defaults(func=rm)

    args = parser.parse_args()

    cleaned = {k: v for k, v in vars(args).items() if k != 'func'}

    args.func(**cleaned)


# TODO: CAMPid 0238493420143087667542054268097120437916848
# http://stackoverflow.com/a/21263493/228539
def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    if os.path.isdir(name):
        os.rmdir(name)
    else:
        os.remove(name)


def rmtree(path, retries=4):
    for remaining in reversed(range(retries)):
        try:
            shutil.rmtree(path, onerror=del_rw)
        except OSError as e:
            if remaining == 0 or e.errno == errno.ENOENT:
                raise
        else:
            break

        print('{} remaining removal attempts'.format(remaining))
        time.sleep(0.5)


def _entry_point():
    try:
        sys.exit(main())
    except ExitError as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(1)


if __name__ == '__main__':
    _entry_point()