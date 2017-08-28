import os


library_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..',
))

project_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..',
))

scripts_path = os.path.join(project_path, 'venv', 'Scripts')

device_path = os.path.join(library_path, 'examples', 'devices')

devices = {
    'customer': os.path.join('customer', 'distributed_generation.epc'),
    'factory': os.path.join('factory', 'distributed_generation_factory.epc'),
}

devices = {
    k: os.path.normpath(os.path.join(device_path, v))
    for k, v in devices.items()
}
