import logging

import epyqlib.busproxy
import epyqlib.device
import epyqlib.twisted.busproxy
import epyqlib.tests.common

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def test_range_override_hidden(qtbot):
    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['customer'],
        node_id=247,
    )

    for view in device.ui.findChildren(epyqlib.nvview.NvView):
        assert view.ui.enforce_range_limits_check_box.isHidden()


def test_range_override_visible(qtbot):
    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['factory'],
        node_id=247,
    )

    for view in device.ui.findChildren(epyqlib.nvview.NvView):
        assert not view.ui.enforce_range_limits_check_box.isHidden()


def test_secret_masked(qtbot):
    secret_mask = '<secret>'

    device = epyqlib.device.Device(
        file=epyqlib.tests.common.devices['factory'],
        node_id=247,
    )

    secret_nv = tuple(nv for nv in device.nvs.all_nv() if nv.secret)

    assert len(secret_nv) > 0
    for nv in secret_nv:
        assert nv.fields.default == secret_mask
        nv.set_human_value('1234')
        assert nv.fields.value == secret_mask


def logit(it):
    logging.debug('logit(): ({}) {}'.format(type(it), it))
