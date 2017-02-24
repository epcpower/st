#!/usr/bin/env python3

# TODO: get some docstrings in here!

import sys
import time

# See file COPYING in this source tree
__copyright__ = 'Copyright 2015, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(template, output):
    with open(template, 'r') as template_file:
        config = template_file.read()
        replacements = {
            'VERSION_EPOCH': str(int(round(time.time())))
        }

        for key, value in replacements.items():
            config = config.replace('**' + key + '**', value)

    with open(output, 'w') as output_file:
        output_file.write(config)

    return 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--template', '-t')
    parser.add_argument('--output', '-o')
    args = parser.parse_args()

    sys.exit(main(template=args.template, output=args.output))
