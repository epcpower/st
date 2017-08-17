import os


project_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..',
))

scripts_path = os.path.join(project_path, 'venv', 'Scripts')

interface = os.path.join(project_path, '..', 'control', 'interface')

devices = {
    'customer': os.path.join(interface, 'distributed_generation.epc'),
    'factory': os.path.join(interface, 'distributed_generation_factory.epc'),
}
