#!/usr/bin/env python3

import argparse
import collections
import epyqlib.device
try:
    import git
except ImportError as e:
    raise ImportError('Package gitpython expected but not found') from e
import json
import os
import pip
import shutil
import stat
import sys
import tempfile
import traceback
import zipfile


# TODO: CAMPid 0238493420143087667542054268097120437916848
# http://stackoverflow.com/a/21263493/228539
def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    if os.path.isdir(name):
        os.rmdir(name)
    else:
        os.remove(name)


def collect_blobs(tree):
    blobs = tree.blobs
    for subtree in tree.trees:
        blobs.extend(collect_blobs(subtree))

    return blobs


class DeviceLoadError(Exception):
    pass


def collect(devices, output_directory, dry_run, groups=None):
    if groups is None:
        groups = [None]

    with tempfile.TemporaryDirectory() as checkout_dir:
        os.makedirs(output_directory, exist_ok=True)

        all_urls = set()
        all_remotes = set()
        all_devices = set()

        dirs = []

        for name, values in devices.items():
            dir = os.path.join(checkout_dir, name)
            dirs.append(dir)
            print('  Handling {}'.format(name))

            print('    Cloning {}'.format(values['repository']))
            repo = git.Repo.clone_from(values['repository'], dir)
            repo.git.checkout(values['branch'])

            if values['repository'] not in all_urls:
                all_urls.add(values['repository'])
                all_remotes.add(repo)
            all_devices.add((values['repository'], values['branch'], values['file']))

            device_groups = values.get('groups', [None])
            if set(device_groups).isdisjoint(set(groups)):
                print('    Skipping {}'.format(values['file']))
                print('        Device groups {} not in selected groups {}'.format(device_groups, groups))
                continue

            device_path = os.path.join(dir, values['file'])
            print('    Loading {}'.format(values['file']))
            try:
                device = epyqlib.device.Device(file=device_path,
                                               only_for_files=True)
            except Exception as e:
                try:
                    raise DeviceLoadError("Unable to open '{}'".format(device_path)) from e
                except:
                    print()
                    traceback.print_exc()
                    print()
                    continue
            device_dir = os.path.dirname(device_path)
            device_file_name = os.path.basename(device_path)
            referenced_files = [
                device_file_name,
                *device.referenced_files
            ]

            zip_file_name = name + '.epz'
            zip_path = os.path.join(output_directory, zip_file_name)
            print('    {} {}'.format({False: 'Writing', True: 'Not writing'}[dry_run],
                                     zip_file_name))

            if not dry_run:
                with zipfile.ZipFile(file=zip_path, mode='w') as zip:
                    for device_path in referenced_files:
                        filename = os.path.join(device_dir, device_path)
                        zip.write(filename=filename,
                                  arcname=os.path.relpath(filename, start=device_dir)
                                  )

        all_devices_strings = ['{}:{}:{}'.format(url, branch, file) for url, branch, file in all_devices]

        other_devices = set()

        for repo in all_remotes:
            origin_heads = [
                r for r in repo.refs
                if str(r).startswith('origin/')
            ]

            for branch in origin_heads:
                tree = repo.tree(str(branch))
                blobs = collect_blobs(tree=tree)
                for blob in blobs:
                    if blob.path.endswith('.epc'):
                        s = '{}:{}:{}'.format(repo.remotes.origin.url, str(branch)[len('origin/'):], blob.path)
                        if s not in all_devices_strings:
                            other_devices.add(s)

        other_devices = sorted(other_devices)
        if len(other_devices) > 0:
            print()
            print('Other devices available from the referenced repositories:')
            for device in other_devices:
                print('    {}'.format(device))

        for dir in dirs:
            # http://bugs.python.org/issue26660
            shutil.rmtree(dir, onerror=del_rw)


class LoadJsonFiles(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [])

        for value in values:
            getattr(namespace, self.dest).append(
                (value.name, json.loads(value.read(), object_pairs_hook=collections.OrderedDict))
            )


def parse_args(args):
    parser =  argparse.ArgumentParser()
    parser.add_argument('--device-file', '-d', type=argparse.FileType('r'),
                        action=LoadJsonFiles, dest='device_files', nargs='+',
                        required=True)
    parser.add_argument('--output-directory', '-o', default=os.getcwd())
    parser.add_argument('--dry-run', '-n', action='store_true')

    return parser.parse_args(args)


def main(args=None, device_files=None, output_directory=None):
    if args is None:
        args = sys.argv[1:]

    if device_files is not None:
        for device in device_files:
            args.extend(['-d', device])

    if output_directory is not None:
        args.extend(['-o', output_directory])

    args = parse_args(args=args)

    for name, devices in args.device_files:
        print('Processing {}'.format(name))
        collect(devices=devices,
                output_directory=args.output_directory,
                dry_run=args.dry_run)


if __name__ == '__main__':
    os.environ['PATH'] = os.pathsep.join((
        os.environ['PATH'],
        os.path.join('c:/', 'Program Files', 'Git', 'bin')
    ))

    sys.exit(main())
