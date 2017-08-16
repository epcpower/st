import os


interface = os.path.join('..', 'control', 'interface')

devices = {
    'customer': os.path.join(interface, 'distributed_generation.epc'),
    'factory': os.path.join(interface, 'distributed_generation_factory.epc'),
}
