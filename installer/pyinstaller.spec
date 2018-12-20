# -*- mode: python -*-

import os

import canmatrix.formats
# import vcversioner


# version = vcversioner.find_version().version

block_cipher = None


def collect(prefix, search_in, *extensions):
    for dir_name, subdirs, files in os.walk(search_in):
        for filename in (f for f in files if f.endswith(extensions)):
            filename = os.path.join(dir_name, filename)
            yield (filename, os.path.join('.', dir_name[len(prefix):]))


hidden_imports = set()
data_files = []

prefix = os.path.join('epyq', '')
search_in = prefix
data_files.extend(collect(prefix, search_in, '.ui', '.ico', '.png'))

prefix = os.path.join('sub', 'epyqlib', '')
search_in = os.path.join(prefix, 'epyqlib')
data_files.extend(collect(prefix, search_in, '.ui', '.svg', '.csv'))

prefix = os.path.join('sub', 'epyqlib', '')
search_in = os.path.join(prefix, 'epyqlib')
extension = '.py'
for dir_name, subdirs, files in os.walk(search_in):
    for py in (f for f in files if f.endswith(extension)):
        py = os.path.join(dir_name, py)
        py = py[len(prefix):-len(extension)]
        py = py.lstrip(os.path.sep)
        py = py.replace(os.path.sep, '.')
        hidden_imports.add(py)

for format in canmatrix.formats.moduleList:
    hidden_imports.add('canmatrix.' + format)

data_files.append(('PCANBasic.dll', '.'))
data_files.append((
    os.path.join('src', 'libs', 'fontawesome', 'fonts', 'FontAwesome.otf'),
    '.'
))

print('-- data files')
for data_file in data_files:
    print(data_file)
print()

a = Analysis(
    [os.path.join('..', 'src', 'epyq', '__main__.py')],
    pathex=['..'],
    binaries=[],
    datas=[(os.path.join(os.getcwd(), p), pp) for p, pp in data_files],
    hiddenimports=list(hidden_imports),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='epyq',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join('epyq', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='epyq',
)
