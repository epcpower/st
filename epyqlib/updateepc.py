import collections
import distutils.dir_util
import importlib
import json
import logging
import os
import shutil
import tempfile
import textwrap

import attr
import click
import lxml.etree

import epyqlib.deviceextension
import epyqlib.utils.general
import epyqlib.utils.click

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger(__name__)


@attr.s
class Converter:
    old_version = attr.ib()
    new_version = attr.ib()
    description = attr.ib()
    function = attr.ib()

    def __call__(self, *args, **kwargs):
        return self.function(self, *args, **kwargs)


converters = epyqlib.utils.general.Collector(Converter, 'function')


def get_ui_paths_0(device_dict):
    for ui_path_name in ['ui_path', 'ui_paths', 'menu']:
        ui_paths = device_dict.get(ui_path_name)

        if ui_paths is not None:
            break
    else:
        ui_paths = {}

    if not isinstance(ui_paths, dict):
        ui_paths = {"Dash": ui_paths}

    return ui_paths


@converters.append(
    old_version=(0,8),
    new_version=(0,9),
    description='_frame/_signal -> _signal_path_element_...')
def cf(self, source_directory, source_file_name, destination_path):
    with open(os.path.join(source_directory, source_file_name)) as f:
        device_dict = json.load(f, object_pairs_hook=collections.OrderedDict)

    ui_paths = get_ui_paths_0(device_dict)

    module_path = device_dict.get('module', None)
    if module_path is None:
        module = epyqlib.deviceextension
    else:
        spec = importlib.util.spec_from_file_location(
            'extension', os.path.join(source_directory, module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    referenced_files = (
        source_file_name,
        *(
            device_dict.get(name) for name in
            (
                'module',
                'can_path',
                'compatibility',
                'parameter_defaults',
                'parameter_hierarchy',
            )
            if name in device_dict
        ),
        *ui_paths.values(),
        *module.referenced_files(device_dict),
    )

    referenced_files = {f: False for f in referenced_files}

    for ui in referenced_files:
        if os.path.splitext(ui)[1].casefold() != '.ui':
            continue

        with open(os.path.join(source_directory, ui)) as f:
            root = lxml.etree.parse(f)

        widgets = root.xpath(
            "//widget[property[re:match(@name, '(_|^)(signal|frame)')]]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        for widget in widgets:
            logging.debug('Widget: {}'.format(widget.get('name')))
            signal_paths = widget.xpath(
                "property[re:match(@name, '(_|^)(signal|frame)')]",
                namespaces={"re": "http://exslt.org/regular-expressions"},
            )
            full_names = tuple(e.get('name') for e in signal_paths)

            signal_path_names = set()
            for name in full_names:
                left, underscore, right = name.rpartition('_')
                if len(underscore) > 0:
                    signal_path_names.add(left)
                else:
                    signal_path_names.add(right)

            for name in signal_path_names:
                logging.debug('  Signal path name: {}'.format(name))
                xpath = "property[contains(@name, '{}')]".format(name)
                properties = widget.xpath(xpath)
                logging.debug('    Properties: {}'.format(
                    tuple(e.get('name') for e in properties),
                ))

                for i, p in enumerate(properties):
                    left, underscore, right = p.get('name').rpartition('_')
                    p.set(
                        'name',
                        ''.join((
                            left,
                            underscore,
                            'signal_path_element_',
                            str(i),
                        ))
                    )

        with open(os.path.join(destination_path, ui), 'wb') as f:
            root.write(f, xml_declaration=True, encoding='UTF-8')
            f.write('\n'.encode('utf-8'))

        logging.info('Updated {}'.format(ui))
        referenced_files[ui] = True

    device_dict['format_version'] = self.new_version
    device_dict.move_to_end('format_version', last=False)

    destination_device_file = os.path.join(destination_path, source_file_name)
    with open(destination_device_file, 'w') as f:
        json.dump(device_dict, f, indent=4)
        f.write('\n')
    referenced_files[source_file_name] = True

    for f, handled in referenced_files.items():
        if not handled:
            logging.info('Copying {}'.format(f))
            shutil.copy(
                src=os.path.join(source_directory, f),
                dst=destination_path,
            )

    return destination_device_file


@converters.append(
    old_version=(0,9),
    new_version=(1,),
    description='signal_path_element_0,1,2 to ; delimited signal_path '
                'properties in .ui')
def cf(self, source_directory, source_file_name, destination_path):
    with open(os.path.join(source_directory, source_file_name)) as f:
        device_dict = json.load(f, object_pairs_hook=collections.OrderedDict)

    ui_paths = get_ui_paths_0(device_dict)

    referenced_files = (
        source_file_name,
        *(
            device_dict.get(name) for name in
            (
                'module',
                'can_path',
                'compatibility',
                'parameter_defaults',
                'parameter_hierarchy',
            )
            if name in device_dict
        ),
        *ui_paths.values(),
    )

    referenced_files = {f: False for f in referenced_files}

    module = device_dict.get('module')
    if module is not None:
        referenced_files_string = textwrap.dedent('''\
        def referenced_files(raw_dict):
            return ()
        ''')

        with open(os.path.join(source_directory, module)) as f_in:
            with open(os.path.join(destination_path, module), 'w') as f_out:
                written = any(
                    l.startswith('def referenced_files(') for l in f_in
                )

                f_in.seek(0)

                for line in f_in:
                    if not written and line.startswith(('class ', 'def ')):
                        logging.info('Adding referenced_files() to module')

                        f_out.write(referenced_files_string)
                        f_out.write('\n\n')

                        written = True

                    f_out.write(line)

                if not written:
                    f_out.write('\n\n')
                    f_out.write(referenced_files_string)

        referenced_files[module] = True

    ui_files = tuple(
        f
        for f in referenced_files
        if f.endswith('.ui')
    )

    for ui in ui_files:
        with open(os.path.join(source_directory, ui)) as f:
            root = lxml.etree.parse(f)

        widgets = root.xpath(
            "//widget[property[contains(@name, '_path_element_0')]]"
        )

        for widget in widgets:
            logging.debug('Widget: {}'.format(widget.get('name')))
            signal_paths = widget.xpath(
                "property[contains(@name, '_path_element_')]")
            full_names = tuple(e.get('name') for e in signal_paths)
            signal_path_names = set(
                name.rpartition('_element_')[0] for name in full_names
            )
            for name in signal_path_names:
                logging.debug('  Signal path name: {}'.format(name))
                xpath = "property[contains(@name, '{}')]".format(name)
                properties = widget.xpath(xpath)
                logging.debug('    Properties: {}'.format(
                    tuple(e.get('name') for e in properties),
                ))

                modify, to_remove = properties[0], properties[1:]
                strings = widget.xpath(xpath + '/string')
                modify.set('name', modify.get('name').rpartition('_element')[0])
                modify[0].text = ';'.join(s.text for s in strings)
                for e in to_remove:
                    e.getparent().remove(e)

        with open(os.path.join(destination_path, ui), 'wb') as f:
            root.write(f, xml_declaration=True, encoding='UTF-8')
            f.write('\n'.encode('utf-8'))

        logging.info('Updated {}'.format(ui))
        referenced_files[ui] = True

    device_dict['format_version'] = self.new_version
    device_dict.move_to_end('format_version', last=False)

    destination_device_file = os.path.join(destination_path, source_file_name)
    with open(destination_device_file, 'w') as f:
        json.dump(device_dict, f, indent=4)
        f.write('\n')
    referenced_files[source_file_name] = True

    for f, handled in referenced_files.items():
        if not handled:
            logging.info('Copying {}'.format(f))
            shutil.copy(
                src=os.path.join(source_directory, f),
                dst=destination_path,
            )

    return destination_device_file


@converters.append(
    old_version=(1,),
    new_version=None,
    description='template for next format version')
def cf(self, source_directory, source_file_name, destination_path):
    with open(os.path.join(source_directory, source_file_name)) as f:
        device_dict = json.load(f, object_pairs_hook=collections.OrderedDict)

    ui_paths = get_ui_paths_0(device_dict)

    module_path = device_dict.get('module', None)
    if module_path is None:
        module = epyqlib.deviceextension
    else:
        spec = importlib.util.spec_from_file_location(
            'extension', os.path.join(source_directory, module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    referenced_files = (
        source_file_name,
        *(
            device_dict.get(name) for name in
            (
                'module',
                'can_path',
                'compatibility',
                'parameter_defaults',
                'parameter_hierarchy',
            )
            if name in device_dict
        ),
        *ui_paths.values(),
        *module.referenced_files(device_dict),
    )

    referenced_files = {f: False for f in referenced_files}

    device_dict['format_version'] = self.new_version
    device_dict.move_to_end('format_version', last=False)

    destination_device_file = os.path.join(destination_path, source_file_name)
    with open(destination_device_file, 'w') as f:
        json.dump(device_dict, f, indent=4)
        f.write('\n')
    referenced_files[source_file_name] = True

    for f, handled in referenced_files.items():
        if not handled:
            logging.info('Copying {}'.format(f))
            shutil.copy(
                src=os.path.join(source_directory, f),
                dst=destination_path,
            )

    return destination_device_file


def just_copy(source_directory, source_file_name, destination_path):
    distutils.dir_util.copy_tree(source_directory, destination_path)


def conversion_summaries():
    return tuple(
        '{} -> {}: {}'.format(c.old_version, c.new_version, c.description)
        for c in sorted(
            converters, key=lambda c: (c.old_version, c.new_version)
        )
    )


def version(path):
    with open(path) as f:
        device_dict = json.load(f, object_pairs_hook=collections.OrderedDict)

    v = device_dict.get('format_version', None)

    ui_paths = get_ui_paths_0(device_dict)

    module_path = device_dict.get('module', None)
    if module_path is None:
        module = epyqlib.deviceextension
    else:
        spec = importlib.util.spec_from_file_location(
            'extension', os.path.join(os.path.dirname(path), module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    referenced_files = (
        path,
        *(
            device_dict.get(name) for name in
            (
                'module',
                'can_path',
                'compatibility',
                'parameter_defaults',
                'parameter_hierarchy',
            )
            if name in device_dict
        ),
        *ui_paths.values(),
    )

    try:
        referenced_files += tuple(module.referenced_files(device_dict))
    except:
        pass

    ui_files = tuple(
        f
        for f in referenced_files
        if f.endswith('.ui')
    )

    if v is None:
        fragment = '_path_element_'

        for ui in ui_files:
            with open(os.path.join(os.path.dirname(path), ui)) as f:
                if any(fragment in line for line in f):
                    v = (0,9)
                    break

    if v is None:
        v = (0,8)

    return tuple(v)


# TODO: calculate by largest version number in converts?
current_version = max(
    c.new_version for c in converters if c.new_version is not None
)


def is_latest(path):
    return version(path) == current_version


def get_converter(old_version, new_version=current_version):
    converter, = (
        c for c in converters
        if c.old_version == old_version and c.new_version == new_version
    )

    return converter


def get_converters(old_version=None, new_version=None):
    return tuple(
        c for c in converters
        if (
            (c.old_version == old_version or old_version is None)
            and (c.new_version == new_version or new_version is None)
        )
    )


def get_converter_chain(old_version, new_version=current_version):
    converter_chain = []

    old = old_version

    while True:
        cs = get_converters(old_version=old)
        converter = max(cs, key=lambda c: c.new_version)
        converter_chain.append(converter)
        old = converter.new_version

        if converter.new_version == new_version:
            break

    return converter_chain


def convert(source_path, destination_path, destination_version=None):
    if destination_version is None:
        destination_version = current_version

    source_version = version(source_path)

    chain = get_converter_chain(source_version, destination_version)
    chain.append(just_copy)

    temporary_directories = tuple(
        tempfile.TemporaryDirectory() for _ in range(len(chain) - 1)
    )

    directories = (
        os.path.dirname(source_path),
        *(d.name for d in temporary_directories),
        destination_path,
    )

    directory_pairs = tuple(epyqlib.utils.general.pairwise(directories))

    for c, (source, destination) in zip(chain, directory_pairs):
        if c is not just_copy:
            logging.info(
                'Converting {} -> {}'.format(c.old_version, c.new_version)
            )

        c(
            source_directory=source,
            source_file_name=os.path.basename(source_path),
            destination_path=destination,
        )

    for temporary_directory in temporary_directories:
        temporary_directory.cleanup()

    logging.info('New device file saved to: {}'.format(destination_path))

    return os.path.join(destination_path, os.path.basename(source_path))


@click.command()
@epyqlib.utils.click.verbose_option
@click.option('--target-version', '-t', default=None)
@click.argument('epc', type=click.Path(exists=True), required=True)
@click.argument('destination', type=click.Path(exists=True),
                required=True)
def main(epc, destination, target_version):
    if target_version is not None:
        target_version = tuple(
            int(s) for s in target_version.rstrip('0.').split('.')
        )

    epc_version = version(epc)
    if epc_version == current_version:
        logging.warning('Already at latest version (v{})'.format(
                '.'.join(str(s) for s in epc_version)
        ))
    else:
        convert(
            source_path=epc,
            destination_path=destination,
            destination_version=target_version,
        )
