import pathlib

import alqtendpy.compileui
import setuptools
import setuptools.command.build_py


alqtendpy.compileui.compile_ui(
    directory_paths=[pathlib.Path(__file__).parent  / 'src' / 'epyq'],
)


setuptools.setup(
    name="EPyQ",
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    entry_points={'gui_scripts': ['epyq = epyq.__main__:main']},
    install_requires=[
        'alqtendpy',
        'epyqlib>=2019.9.10',
        'PyQt5',
        'PyQtChart',
    ],
    setup_requires=[
        'vcversioner==2.16.0.0',
    ],
    vcversioner={
        'version_module_paths': ['src/epyq/_version.py'],
        'vcs_args': ['git', '--git-dir', '%(root)s/.git', 'describe',
                     '--tags', '--long', '--abbrev=999']
    },
)
