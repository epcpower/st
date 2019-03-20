from setuptools import setup, find_packages

setup(
    name="EPyQ",
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points={'gui_scripts': ['epyq = epyq.__main__:main']},
    install_requires=[
        'epyqlib>=2019.3.4',
        'PyQt5',
        'PyQtChart',
    ],
    extras_require={
        ':sys_platform == "win32"': ['pyqt5-tools'],
    },
    setup_requires=[
        'vcversioner==2.16.0.0',
    ],
    vcversioner={
        'version_module_paths': ['src/epyq/_version.py'],
        'vcs_args': ['git', '--git-dir', '%(root)s/.git', 'describe',
                     '--tags', '--long', '--abbrev=999']
    },
)
