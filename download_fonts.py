import errno
import io
import os
import shutil
import stat
import sys
import tempfile
import zipfile

import requests


def download_zips(directory):
    src_zips = {
        "fontawesome": "https://github.com/FortAwesome/Font-Awesome/archive/v4.6.3.zip",
        # i think this was for the embedded touch display
        # "metropolis": "https://github.com/chrismsimpson/Metropolis/archive/16882c2c2cb58405fd6a7d6a932a1dfc573b6813.zip",
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
            rmtree(directory=destination)
            # if os.path.exists(destination):
            #     raise FileExistsError(
            #         '`{}` already exists while extracting Zip'.format(destination))

            shutil.move(zip_path, destination)


def is_readonly_path(fn):
    """Check if a provided path exists and is readonly.
    Permissions check is `bool(path.stat & stat.S_IREAD)` or `not os.access(path, os.W_OK)`
    """
    if os.path.exists(fn):
        return (os.stat(fn).st_mode & stat.S_IREAD) or not os.access(fn, os.W_OK)

    return False


def set_write_bit(fn):
    if isinstance(fn, str) and not os.path.exists(fn):
        return
    os.chmod(fn, stat.S_IWRITE | stat.S_IWUSR | stat.S_IRUSR)
    return


def rmtree(directory, ignore_errors=False):
    shutil.rmtree(
        directory, ignore_errors=ignore_errors, onerror=handle_remove_readonly
    )


def handle_remove_readonly(func, path, exc):
    """Error handler for shutil.rmtree.
    Windows source repo folders are read-only by default, so this error handler
    attempts to set them as writeable and then proceed with deletion."""
    # Check for read-only attribute
    default_warning_message = (
        "Unable to remove file due to permissions restriction: {!r}"
    )
    # split the initial exception out into its type, exception, and traceback
    exc_type, exc_exception, exc_tb = exc
    if is_readonly_path(path):
        # Apply write permission and call original function
        set_write_bit(path)
        try:
            func(path)
        except (OSError, IOError) as e:
            if e.errno in [errno.EACCES, errno.EPERM]:
                return


download_zips(sys.argv[1])
