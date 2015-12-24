from setuptools import setup, find_packages

setup(
    name="EPyQ",
    version="0.1",
    packages=find_packages(),
    entry_points={'gui_scripts': ['epyq = epyq.__main__:main']},
    include_package_data=True
)
