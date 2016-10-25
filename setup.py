import platform

from setuptools import setup, find_packages

conditional_requires = []

arch = platform.architecture()
if arch[1].lower().startswith('win'):
    conditional_requires.append('PyQt5-tools')

setup(
    name="EPyQ",
    version="0.1",
    author="EPC Power Corp.",
    classifiers=[
        ("License :: OSI Approved :: "
         "GNU General Public License v2 or later (GPLv2+)")
    ],
    packages=find_packages(),
    entry_points={'gui_scripts': ['epyq = epyq.__main__:main']},
    install_requires=[
        'PyQt5',
        *conditional_requires
    ]
)
