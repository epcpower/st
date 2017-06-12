import os
import textwrap

import click


@click.command()
@click.argument('target', type=click.File('w'), default='-')
def write_build_file(target):
    template = textwrap.dedent('''\
    # This file has been generated


    ''')

    target.write(template)

    values = {name: None for name in (
        'build_system',
        'build_id',
        'build_number',
        'build_version',
        'job_id',
        'job_url',
    )}

    if os.environ.get('APPVEYOR') == 'True':
        values['build_system'] = 'AppVeyor'
        mapping = {
            'build_id': 'APPVEYOR_BUILD_ID',
            'build_number': 'APPVEYOR_BUILD_NUMBER',
            'build_version': 'APPVEYOR_BUILD_VERSION',
            'job_id': 'APPVEYOR_JOB_ID',
        }
        values = {k: os.environ[v] for k, v in mapping.items()}
        values['job_url'] = (
            'https://ci.appveyor.com/'
            'project/{account}/{slug}/build/job/{id}'.format(
                account=os.environ['APPVEYOR_ACCOUNT_NAME'],
                slug=os.environ['APPVEYOR_PROJECT_SLUG'],
                id=os.environ['APPVEYOR_JOB_ID'],
            )
        )

    for k, v in values.items():
        target.write('{} = {}\n'.format(k, repr(v)))
