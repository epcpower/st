import logging
import functools
import sys

import can
import pytest
from PyQt5.QtCore import QTimer

import epyqlib.busproxy
import epyqlib.device
import epyqlib.tests.common
import epyqlib.twisted.busproxy

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@pytest.mark.require_device
def test_self_toggling(qtbot):
    # TODO: CAMPid 03127876954165421679215396954697
    # https://github.com/kivy/kivy/issues/4182#issuecomment-253159955
    # fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
    if 'twisted.internet.reactor' in sys.modules:
        del sys.modules['twisted.internet.reactor']

    import qt5reactor
    qt5reactor.install()

    from twisted.internet import reactor
    try:
        real_bus = can.interface.Bus(bustype='socketcan', channel='can0')
    except Exception:
        # Yep, it really raises just an Exception...
        real_bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS1')
    bus = epyqlib.busproxy.BusProxy(bus=real_bus)

    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['customer'],
        node_id=247,
        bus=bus,
    )

    tx_signal_path = ('ParameterQuery', 'ManageDIO', 'InvertHwEnable')
    tx_signal = device.nvs.neo.signal_by_path(*tx_signal_path)
    rx_signal = tx_signal.status_signal

    receive_count = 0
    def received():
        nonlocal receive_count
        receive_count += 1
    rx_signal.value_changed.connect(received)

    value_changed_count = 0
    def value_changed(i):
        nonlocal value_changed_count
        value_changed_count += 1
    widget, = [
        w for w in device.ui.findChildren(epyqlib.widgets.toggle.Toggle)
        if w.signal_path == ';'.join(tx_signal_path)
    ]

    widget.value.valueChanged.connect(value_changed)


    # can.Message(
    #     arbitration_id=,
    #
    # )

    value = False

    def toggle(n=5):
        nonlocal value

        if n > 0:
            value = not value
            rx_signal.set_value(value)
            rx_signal.frame.update_from_signals()
            bus.notifier.message_received(rx_signal.frame.to_message())
            print(' + - + - receiving message now')

            # rx_signal.frame.send_now()
            # widget.value.
            # rx_signal.value_changed.emit()
            import time
            print('toggle here', time.monotonic())
            n -= 1

        if n > 0:
            QTimer.singleShot(
                0.010 * 1000,
                functools.partial(
                    toggle,
                    n=n,
                ),
            )

    def toggle(n=5):
        value = False
        for _ in range(n):
            value = not value
            rx_signal.set_value(value)
            rx_signal.frame.update_from_signals()
            bus.notifier.message_received(rx_signal.frame.to_message())
            print(' + - + - receiving message now')

            import time
            print('toggle here', time.monotonic())

    toggle_count = 4
    QTimer.singleShot(1 * 1000, functools.partial(toggle, n=toggle_count))

    QTimer.singleShot(10 * 1000, reactor.stop)
    reactor.run()

    print('receive_count', receive_count)
    print('value_changed_count', value_changed_count)
    assert value_changed_count < 2 * toggle_count