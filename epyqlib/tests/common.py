import os


project_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..',
))

scripts_path = os.path.join(project_path, 'venv', 'Scripts')

interface = os.path.join(project_path, '..', 'control', 'interface')

devices = {
    'customer': 'distributed_generation.epc',
    'factory': 'distributed_generation_factory.epc',
}

devices = {
    k: os.path.normpath(os.path.join(interface, v))
    for k, v in devices.items()
}
