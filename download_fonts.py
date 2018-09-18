import io
import os
import shutil
import sys
import tempfile
import zipfile

import requests


def download_zips(directory):
    src_zips = {
        'fontawesome':
            'https://github.com/FortAwesome/Font-Awesome/archive/v4.6.3.zip',
        'metropolis':
            'https://github.com/chrismsimpson/Metropolis/archive/16882c2c2cb58405fd6a7d6a932a1dfc573b6813.zip'
    }

    os.makedirs(directory, exist_ok=True)

    for name, url in src_zips.items():
        response = requests.get(url)

        zip_data = io.BytesIO()
        zip_data.write(response.content)
        zip_file = zipfile.ZipFile(zip_data)
        zip_dir = os.path.split(zip_file.namelist()[0])[0]

        with tempfile.TemporaryDirectory() as td:
            zip_file.extractall(path=td)

            zip_path = os.path.join(td, zip_dir)

            destination = os.path.join(directory, name)
            if os.path.exists(destination):
                raise FileExistsError(
                    '`{}` already exists while extracting Zip'.format(destination))

            shutil.move(zip_path, destination)

download_zips(sys.argv[1])
