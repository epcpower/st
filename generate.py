#!/usr/bin/env python3

import os
import subprocess
import sys


# can be helpful cleaning... find . -name 'generated' -type d -exec rm -rf {} \;

def find_files_by_type(path, extension, exclude_dirs=[]):
    if not extension.startswith('.'):
        extension = '.' + extension

    exclude_dirs = [os.path.abspath(d) for d in exclude_dirs]

    matches = []
    for root, dirs, files in os.walk(path):
        if True not in [os.path.abspath(root).startswith(d) for d in
                        exclude_dirs]:
            for file in files:
                if file.endswith(extension):
                    matches.append(os.path.join(root, file))

    return matches


def make_dir_ready(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        if os.path.isdir(path):
            pass
        else:
            raise


def generic(extension, program, out_lambda, in_option=None, out_option=None,
            out_dir_lambda=lambda d: os.path.join(d, 'generated'),
            in_dir_exclude=[]):
    if not extension.startswith('.'):
        extension = '.' + extension

    for f in find_files_by_type('.', extension, in_dir_exclude):
        print('Processing: ' + f)

        out_dir = out_dir_lambda(os.path.dirname(f))
        make_dir_ready(out_dir)
        out_file = os.path.join(out_dir, out_lambda(os.path.basename(f)))

        command_line = [program, in_option, f, out_option, out_file]
        command_line = [e for e in command_line if e is not None]

        print('Executing: ' + ' '.join(command_line))
        subprocess.call(command_line, shell=True)


def generate():
    generic(extension='.ui',
            program='pyuic5',
            out_lambda=lambda f: os.path.splitext(f)[0] + '_ui.py',
            out_option='-o')

    return 0


if __name__ == '__main__':
    sys.exit(generate())
