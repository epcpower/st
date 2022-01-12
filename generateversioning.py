import toml
import subprocess

def get_git_revision_hash() -> str:
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()

toml_data = toml.load('./pyproject.toml')
version = toml_data['tool']['poetry']['version']
print(version)

print(get_git_revision_hash())

versionfile = open("src\epyq\_version.py", "w")
versioninfo = [
    "#This file is generated from generateversioning.py\n"
    "__version__ = \""+version+"\"\n"
    "__sha__ = \""+get_git_revision_hash()+"\"\n"
    "__revision__ = \""+get_git_revision_hash()+"\"\n"

]
versionfile.writelines(versioninfo)