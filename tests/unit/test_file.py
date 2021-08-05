from unittest import mock

import neotools.commands
import pytest
from neotools.applet.constants import AppletIds
from neotools.device import Device
from neotools.file import FileAttributes, FileConst


# fmt: off
@pytest.fixture
def raw_attributes():
    return bytes([0x61, 0x72, 0x74, 0x00, 0x6C, 0x69, 0x6F, 0x6E,
                  0x00, 0x74, 0x73, 0x00, 0x00, 0x02, 0x40, 0x00,
                  0x77, 0x72, 0x69, 0x74, 0x65, 0x00, 0x00, 0x0A,
                  0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x04, 0x1D,
                  0x00, 0x00, 0x00, 0x04, 0x00, 0x0E, 0xA7, 0xA7])
# fmt: on


@pytest.fixture
def file_attributes():
    return FileAttributes(
        file_index=5,
        name="art",
        space=5,
        password="write",
        min_size=512,
        alloc_size=1053,
        flags=FileConst.FLAGS_UNKNOWN_1,
    )


@pytest.fixture
def device():
    return mock.create_autospec(Device)


@pytest.fixture
def file_list():
    return [
        FileAttributes(
            file_index=0,
            name="foo",
            space=1,
            password="bar",
            min_size=512,
            alloc_size=1053,
            flags=FileConst.FLAGS_UNKNOWN_1,
        ),
        FileAttributes(
            file_index=1,
            name="bar",
            space=2,
            password="bar",
            min_size=512,
            alloc_size=1053,
            flags=FileConst.FLAGS_UNKNOWN_1,
        ),
        FileAttributes(
            file_index=2,
            name="hello",
            space=0,
            password="bar",
            min_size=512,
            alloc_size=1053,
            flags=FileConst.FLAGS_UNKNOWN_1,
        ),
        FileAttributes(
            file_index=3,
            name="world",
            space=5,
            password="bar",
            min_size=512,
            alloc_size=1053,
            flags=FileConst.FLAGS_UNKNOWN_1,
        ),
    ]


@pytest.fixture
def patch_list_files(monkeypatch, file_list):
    def mockreturn(device, applet_id):
        return file_list

    monkeypatch.setattr(neotools.file, "list_files", mockreturn)


def test_get_file_attributes_from_raw(file_attributes, raw_attributes):
    file_index = 5
    for attr in [file_attributes, FileAttributes.from_raw(file_index, raw_attributes)]:
        assert attr.file_index == file_index
        assert attr.space == 5
        assert attr.name == "art"
        assert attr.password == "write"
        assert attr.min_size == 512
        assert attr.alloc_size == 1053
        assert attr.flags == FileConst.FLAGS_UNKNOWN_1


def test_get_file_by_name_or_space_no_files(device, monkeypatch):
    def mockreturn(device, applet_id):
        return []

    monkeypatch.setattr(neotools.file, "list_files", mockreturn)
    assert (
        neotools.file.get_file_by_name_or_space(device, AppletIds.ALPHAWORD, "test")
        is None
    )


def test_get_file_by_name_or_space(device, patch_list_files, file_list):
    assert (
        neotools.file.get_file_by_name_or_space(device, AppletIds.ALPHAWORD, "1")
        is file_list[0]
    )
    assert (
        neotools.file.get_file_by_name_or_space(
            device, AppletIds.ALPHAWORD, "hello"
        )
        is file_list[2]
    )
