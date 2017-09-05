#!/usr/bin/env python3

import argparse
import collections
import io
import os
import platform
import requests
import shutil
import sys
import tempfile
import textwrap
import zipfile


Activate = collections.namedtuple(
    'Activate',
    [
        'windows',
        'set_format',
        'path_separator',
        'pwd',
        'comment_marker',
        'insert_before'
    ]
)

activate_scripts = {
    'activate': Activate(
        windows=False,
        set_format='export {name}={value}',
        path_separator=':',
        pwd='$(pwd)',
        comment_marker='#',
        insert_before=None
    ),
    'activate.bat': Activate(
        windows=True,
        set_format='set {name}={value}',
        path_separator=';',
        pwd='%cd%',
        comment_marker='REM',
        insert_before = None
    ),
    'activate.ps1': Activate(
        windows=True,
        set_format='${name} = "{value}"',
        path_separator=';',
        pwd="$((Get-Location).Path)",
        comment_marker='#',
        insert_before='# SIG'
    ),
}


def download_zips(directory):
    src_zips = {
        'fontawesome':
            'https://github.com/FortAwesome/Font-Awesome/archive/v4.6.3.zip',
        'metropolis':
            'https://github.com/chrismsimpson/Metropolis/archive/16882c2c2cb58405fd6a7d6a932a1dfc573b6813.zip'
    }

    os.makedirs(directory, exist_ok=True)

    for name, url in src_zips.items():
        response = requests.get(url)

        zip_data = io.BytesIO()
        zip_data.write(response.content)
        zip_file = zipfile.ZipFile(zip_data)
        zip_dir = os.path.split(zip_file.namelist()[0])[0]

        with tempfile.TemporaryDirectory() as td:
            zip_file.extractall(path=td)

            zip_path = os.path.join(td, zip_dir)

            destination = os.path.join(directory, name)
            if os.path.exists(destination):
                raise FileExistsError(
                    '`{}` already exists while extracting Zip'.format(destination))

            shutil.move(zip_path, destination)


def write_patch_notice(file, comment_marker):
    file.write(textwrap.dedent('''\


    {c}
    {c} ==== Patch below added to support EPyQ

    '''.format(c=comment_marker)))


def patch_activate(bin):
    path_variables = collections.OrderedDict([
        ('PYQTDESIGNERPATH', [
            ['sub', 'epyqlib', 'epyqlib'],
            ['sub', 'epyqlib', 'epyqlib', 'widgets'],
        ])
    ])

    for name, script in activate_scripts.items():
        path = os.path.join(bin, name)

        if os.path.exists(path):
            set_commands = []

            for variable, paths in path_variables.items():
                paths = [os.path.join(script.pwd, *p) for p in paths]

                command = script.set_format.format(
                    name=variable,
                    value=script.path_separator.join(paths)
                )
                set_commands.append(command)

            if script.insert_before is not None:
                with open(path, 'r') as f:
                    contents = f.read()
                with open(path, 'w') as f:
                    written = False
                    for line in contents.splitlines():
                        if line.startswith(script.insert_before) and not written:
                            written = True
                            write_patch_notice(f, script.comment_marker)

                            for command in set_commands:
                                f.write(command + '\n')
                            f.write('\n\n')

                        f.write(line + '\n')
            else:
                with open(path, 'a') as f:
                    write_patch_notice(f, script.comment_marker)

                    for command in set_commands:
                        f.write(command + '\n')


def write_activate_shortcuts(root, bin):
    for name, script in activate_scripts.items():
        caller = os.path.join(root, name)
        target = os.path.join(bin, name)
        if os.path.isfile(target):
            with open(caller, 'w') as f:
                if script.windows:
                    target = '"{}"'.format(target.replace('\\', '/'))
                else:
                    target = 'source "{}"'.format(target)
                f.write(target + '\n')


def copy_designer_files(root):
    files = ['designer', 'designer.bat', 'designer.ps1', 'designer.vbs']

    for file in files:
        shutil.copy(os.path.join(os.path.dirname(__file__), '..', file),
                    os.path.join(root, file))


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '--src', '-s', required=True)
    parser.add_argument('--bin', '-b', required=True)
    parser.add_argument('--root', '-r', required=True)
    parser.add_argument('--for-test', action='store_true')

    return parser.parse_args(args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    args = parse_args(args=args)

    download_zips(directory=args.source)
    patch_activate(bin=args.bin)
    if not args.for_test:
        write_activate_shortcuts(root=args.root, bin=args.bin)
        copy_designer_files(root=args.root)
        if platform.system() != 'Windows':
            backup_cwd = os.getcwd()
            os.chdir(os.path.dirname(args.bin))
            os.symlink(os.path.basename(args.bin), 'Scripts')
            os.chdir(backup_cwd)


if __name__ == '__main__':
    sys.exit(main())
