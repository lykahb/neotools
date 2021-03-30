import pytest
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
        name="art",
        space=5,
        password="write",
        min_size=512,
        alloc_size=1053,
        flags=FileConst.FLAGS_UNKNOWN_1,
    )


def test_get_file_attributes_from_raw(file_attributes, raw_attributes):
    for attr in [file_attributes, FileAttributes.from_raw(raw_attributes)]:
        assert attr.space == 5
        assert attr.name == "art"
        assert attr.password == "write"
        assert attr.min_size == 512
        assert attr.alloc_size == 1053
        assert attr.flags == FileConst.FLAGS_UNKNOWN_1
