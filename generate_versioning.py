import toml
import subprocess


def get_git_revision_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()


__version__ = "2021.5.1.post97"
print(__version__)

print(get_git_revision_hash())

versionfile = open("src\epyq\_version.py", "w")
versioninfo = [
    "#This file is generated from generate_versioning.py\n"
    '__version__ = "' + __version__ + '"\n'
    '__sha__ = "' + get_git_revision_hash() + '"\n'
    '__revision__ = "' + get_git_revision_hash() + '"\n'
]
versionfile.writelines(versioninfo)
