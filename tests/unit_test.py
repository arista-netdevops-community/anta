import ast
from unittest.mock import Mock
import pytest
import eos_testing.functions


def id_func(param):
    return str(param)

def runCmds(version, commands, format):
    if commands == ['show version'] and format == 'json':
        data_string = open('mock_data/show_version_json_4.27.1.1F.out').read()
        data_list = ast.literal_eval(data_string)
    elif commands == ['show uptime'] and format == 'json':
        data_string = open('mock_data/show_uptime_json_1000000.out').read()
        data_list = ast.literal_eval(data_string)
    elif commands == ['show ntp status'] and format == 'text':
        data_string = open('mock_data/show_ntp_status_text_synchronised.out').read()
        data_list = ast.literal_eval(data_string)
    return data_list

@pytest.fixture
def mock_device():
    mock_device = Mock(spec_set=['runCmds'])
    mock_device.runCmds.side_effect = runCmds
    return mock_device

@pytest.mark.parametrize("versions,expected",[(['4.27.1.1F'], True),
                                                (['4.24.0F', '4.27.1.1F'], True),
                                               (['4.24.0F'], False),
                                               (['4.24.0F', '4.27.0F'], False),
                                               (None, None)],
                                               ids = id_func
                                               )

def test_verify_eos_version(mock_device, versions, expected):
    check = eos_testing.functions.verify_eos_version(device = mock_device, enable_password = 'enable_password', versions = versions)
    assert check == expected

@pytest.mark.parametrize("uptime,expected", [(100, True),
                                             (10000000, False),
                                             (None, None)])

def test_verify_uptime(mock_device, uptime, expected):
    check = eos_testing.functions.verify_uptime(device = mock_device, enable_password = 'enable_password', min = uptime)
    assert check == expected

def test_verify_ntp(mock_device):
    check = eos_testing.functions.verify_ntp(device = mock_device, enable_password = 'enable_password')
    assert check is True