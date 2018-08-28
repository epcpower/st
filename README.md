# EPyQ [![Build status](https://ci.appveyor.com/api/projects/status/64pjrni37k4wu4jy?svg=true)](https://ci.appveyor.com/project/KyleAltendorf/st)

![EPyQ screenshot](/screenshot.png?raw=true)

## About

EPyQ is a cross-platform PC service tool for [EPC Power](http://epcpower.com/) power conversion modules.  It is distributed for Windows and developed in Linux but has been run once on OSX (to the point of loading the GUI).
Primary communication is done over CANbus using pythoncan and Twisted.
The GUI is written in PyQt5.
Most of the interesting parts of the GUI are loaded from device configuration files including `.ui` Qt GUI files and PEAK PCAN `.sym` files for CANbus message definitions.

## Running From Source

Instructions are for Python 3.7 but they should work with slight tweaks with 3.6.

### Windows

- Install [Python 3.7](https://www.python.org/downloads/)
- Install [Git](https://git-scm.com/download)
- `git clone https://github.com/altendky/st`
- `cd st`
- `git submodule update --init`
- `py -3.7 venv.py`
- wait
- wait some more...
- ...
- Note the links provided for possibly needed system and driver extras.
- Try running `venv\Scripts\epyq`.  If you get errors, consider installing the linked extras. 

If using with [PEAK PCAN](http://www.peak-system.com/PCAN-USB.199.0.html?&L=1) hardware, install the [PEAK drivers](http://www.peak-system.com/PCAN-USB.199.0.html?&L=1).

To launch EPyQ run `venv\Scripts\epyq.exe`.
To launch Qt Designer with the EPyQ plugins enabled run `designer.bat`.
EPyQ widgets should be visible at the bottom of the widget box on the left.

### Linux

This procedure will install `virtualenv` and `tox` using `pip --user`.
Expecting the user to handle properly installing these would be better but is not how it works presently.

- Install Python 3.7
  - Consider [pyenv](https://github.com/pyenv/pyenv) to get Python versions
- Install git
- `git clone https://github.com/altendky/st`
- `cd st`
- `git submodule update --init`
- `python3.7 venv.py`
- wait
- a bit more, but not nearly as much as Windows
- Try running `venv/bin/epyq`
- If it works, continue below regarding CAN bus setup

In Linux, EPyQ does not attempt to configure or bring up the socketcan links despite still showing the baud rates.
Presently the user must set these up themselves prior to opening EPyQ since it detects on startup.
As reference, the script below is used during development on Ubuntu 16.04 (Xenial) with a PEAK PCAN USB adapter for a 500kbps bus.

```
#!/bin/bash

sudo modprobe -a can can_raw
for e in 0 1; do
    sudo sh -c "echo $e > $(dirname $(sudo grep --files-with-matches --recursive --include=idVendor 0c72 /sys/bus/usb/devices/* | head -n 1))/authorized"
done
sudo ip link set can0 type can bitrate 500000 restart-ms 500
sudo ip link set can0 txqueuelen 1000
sudo ip link set can0 up
```
