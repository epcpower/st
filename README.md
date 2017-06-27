# EPyQ [![Build status](https://ci.appveyor.com/api/projects/status/64pjrni37k4wu4jy?svg=true)](https://ci.appveyor.com/project/KyleAltendorf/st)

## Running From Source

Instructions are for Python 3.6 but they should work with slight tweaks with 3.5.

### Windows

- Install [Python 3.6](https://www.python.org/downloads/)
- Install [Git](https://git-scm.com/download)
- `git clone https://github.com/altendky/st`
- `cd st`
- `copy .gitmodules.github .gitmodules`
- `git submodule update --init`
- `py -3.6 venv.py`
- wait
- wait some more...
- ...
- Note the links provided for possibly needed system and driver extras.
- Try running `venv\Scripts\epyq`.  If you get errors, consider installing the linked extras. 

If using with [PEAK PCAN](http://www.peak-system.com/PCAN-USB.199.0.html?&L=1) hardware, install the [PEAK drivers](http://www.peak-system.com/PCAN-USB.199.0.html?&L=1).

To launch EPyQ run `venv\Scripts\epyq.exe`.
To launch Qt Designer with the EPyQ plugins enabled run `designer.bat`.
EPyQ widgets should be visible at the bottom of the widget box on the left.
