#!/usr/bin/env python3

import os
import requests
import subprocess


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
    encoding='utf-8'
)

hash = s.split()[2]

subprocess.check_call(
    [
        'git',
        '-C', os.path.join('sub', 'epyqlib'),
        'checkout', hash,
    ],
)

peak = 'PeakOemDrv.exe'
r = requests.get('http://www.peak-system.com/produktcd/Drivers/PeakOemDrv.exe')
b = io.BytesIO(r.content)
with open(peak, 'wb') as f:
    f.write(b.read())

subprocess.check_call(
    [
        peak,
        '/exenoui',
        '/qn',
        'ADDLOCAL=F_PNP_DVRS,F_PCANBASIC',
    ],
)
