import epyqlib.ccp as ccp
import pytest

def test_print_some_stuff():
    print(ccp.CommandCode(2))
    print(ccp._command_code_properties[16].timeout)
    print(ccp._command_code_properties[ccp.CommandCode.clear_memory].timeout)

    print(ccp.CommandCode.connect.timeout)


def test_IdentifierTypeError():
    with pytest.raises(ccp.IdentifierTypeError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        extended_id=False)


def test_PayloadLengthError():
    with pytest.raises(ccp.PayloadLengthError):
        hc = ccp.HostCommand(code=ccp.CommandCode.connect)
        hc.payload = [0] * 20


def test_MessageLengthError():
    with pytest.raises(ccp.MessageLengthError):
        ccp.HostCommand(code=ccp.CommandCode.connect,
                        dlc=5)


def test_UnexpectedMessageReceived():
    handler = ccp.Handler(bus=None)
    packet = ccp.HostCommand(code=ccp.CommandCode.connect)
    packet.data[0] = 0

    with pytest.raises(ccp.UnexpectedMessageReceived):
        handler.packet_received(packet)
