import os


interface = os.path.join('..', 'control', 'interface')

devices = {
    'customer': os.path.join(interface, 'distributed_generation.epc'),
    'factory': os.path.join(interface, 'distributed_generation_factory.epc'),
}

project_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..',
))

scripts_path = os.path.join(project_path, 'venv', 'Scripts')
