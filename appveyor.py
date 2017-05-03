#!/usr/bin/env python3

import io
import itertools
import os
import platform
import shutil
import stat
import subprocess
import sys
import zipfile

import requests


subprocess.check_call(
    [
        'git',
        'clone',
        'https://github.com/altendky/st',
        os.path.join('sub', 'epyqlib'),
    ],
)

s = subprocess.check_output(
    [
        'git',
        'ls-tree',
        '{}:sub'.format(os.environ['APPVEYOR_REPO_BRANCH']),
    ],
)

hash = s.split()[2]

subprocess.check_call(
    [
        'git',
        '-C', os.path.join('sub', 'epyqlib'),
        'checkout', hash,
    ],
)
