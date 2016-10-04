#!/usr/bin/env python3

# TODO: get some docstrings in here!

# See file COPYING in this source tree
__copyright__ = 'Copyright 2016, EPC Power Corp.'
__license__ = 'GPLv2+'


application = '''
QWidget {{
    font-size: {base_font_size_px}px;
    qproperty-focusPolicy: NoFocus;
    color: {foreground};
}}

QWidget#MainForm {{
    background-color: {background};
}}

QWidget[fontawesome=false] {{
    font-family: Metropolis;
}}

QWidget[fontawesome=true] {{
    font-size: 36px;
    icon-size: 36px
}}

Epc {{
    qproperty-show_enumeration_value: false;
}}

QAbstractScrollArea {{
    qproperty-frameShape: NoFrame;
}}

QPushButton {{
    font-size: {base_font_size_px}px;
    min-width: 40px;
    min-height: 40px;
    height: 40px;
    color: black;
}}

QPushButton[fontawesome=true] {{
    min-width: 46px;
    width: 46px;
    max-width: 46px;
    min-height: 46px;
    height: 46px;
    max-height: 46px;
}}

QFrame {{
    qproperty-frameShadow: Plain;
}}

QLineEdit, QPushButton {{
    border-radius: 10px;
    border-width: 0px;
    border-style: solid;
}}

QLineEdit {{
    qproperty-focusPolicy: NoFocus;
    background-color: {background_blue};
}}

QPushButton:enabled {{
    background-color: {green};
}}

QPushButton:!enabled {{
    background-color: {gray};
}}

QPushButton[active=true] {{
    background: {blue};
}}

QLineEdit {{
    qproperty-frame: false;
}}

QLineEdit:!enabled {{
    background-color: {gray};
}}

QLineEdit:enabled {{
    padding: 0 8px;
    selection-background-color: darkgray;
}}

QSlider {{
    min-height: 40px;
    min-width: 30px;
}}

QSlider::groove {{
    width: 4px;
    border-radius: 2px;
    background-color: {gray};
}}

QSlider::handle {{
    height: 10px;
    border-radius: 3px;
    margin: 0 -8px;
    background-color: {blue};
}}
'''

small = '''
QWidget[fontawesome=false] {{
    font-size: 15px;
}}

QPushButton[fontawesome=false] {{
    min-height: 25px;
}}

QLineEdit, QPushButton {{
    border-radius: 5px;
}}
'''

if __name__ == '__main__':
    import sys

    print('No script functionality here')
    sys.exit(1)     # non-zero is a failure
