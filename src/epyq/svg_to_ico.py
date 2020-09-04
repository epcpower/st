import os
import shutil
import subprocess


def print_check_call(command, *args, **kwargs):
    print("Launching {}".format(repr(command[0])))
    print("\n".join("    {}".format(repr(c)) for c in command))
    subprocess.check_call(command, *args, **kwargs)


subprocess.check_call(
    [
        "inkscape",
        "-z",
        "-e",
        "icon.png",
        "-w",
        "256",
        "-h",
        "256",
        "icon.svg",
    ]
)

subprocess.check_call(
    [
        "convert",
        "icon.png",
        "-define",
        "icon:auto-resize=256,128,96,64,48,32,24,16",
        "icon.ico",
    ]
)

for f in ("icon.ico", "icon.png"):
    shutil.copy(f, os.path.join("..", "sub", "epyqlib", "epyqlib"))
