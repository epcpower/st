import os
import subprocess

hash = subprocess.check_output([os.path.join('c:/', 'Program Files', 'Git', 'bin', 'git.exe'), 'rev-parse', 'HEAD'])

out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'revision.py')

with open(out_file, 'w') as file:
    file.write("hash = '{}'".format(hash.decode('utf-8').rstrip()))
