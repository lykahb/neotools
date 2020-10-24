import logging
from collections import OrderedDict

from usb import util

from alphatools.message import Message, MessageConst, send_message
from alphatools.util import calculate_data_checksum, buf_to_string, buf_to_int

logger = logging.getLogger(__name__)
FILE_ATTRIBUTES_FORMAT = OrderedDict([
    # Zero terminated file name string (this appears to be reported wrongly in some cases - bugs in some Neo firmware?)
    ('name', (0x00, 15)),
    ('password', (0x10, 7)),  # Zero terminated file password string (max six characters?)
    ('min_size', (0x18, 4)),  # Minimum file allocation size
    ('alloc_size', (0x1c, 4)),  # Actual file allocation size
    ('flags', (0x20, 4)),  # Flags (only the lowest 3 bits are used?)
    ('unknown1', (0x24, 1)),
    ('space', (0x25, 1)),  # file space code
    ('unknown2', (0x26, 2)),  # appears to be ignored on write and quasi-random on read
])


class FileConst:
    SIZE = 40  # The number of bytes in the file attributes object. */

    # Values for the flags word.
    # If you create a new AlphaWord file with a set of flags of zero, they will end up as 0x04 or 0x06
    # once the file has been opened on the Neo.

    FLAGS_UNKNOWN_0 = 0x01  # Unknown flag (always clear). */
    FLAGS_CURRENT = 0x02  # Set if the file is the currently active file for the applet. */
    FLAGS_UNKNOWN_1 = 0x04  # Unknown flag (always set for ASWordFiles, clear for others?). */

    # List of file space codes.
    # REVIEW: this is presumably hard wired (since otherwise a backup and restore following an OS update
    # would corrupt backup data unless it were changed). However, the numbers used seem to make little
    # sense. Using values other than in this table will generally upset the Neo...
    FILE_SPACE_CODES = [0xff, 0x2d, 0x2c, 0x04, 0x0f, 0x0e, 0x0a, 0x01, 0x27]


def get_file_attributes(device, applet_id, index):
    logger.info('Getting file attributes', applet_id, index)
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_GET_FILE_ATTRIBUTES, [{
        'value': index, 'offset': 4, 'width': 1
    }, {
        'value': applet_id, 'offset': 5, 'width': 2
    }])
    response = send_message(device, message)
    if response.command() == MessageConst.ERROR_PARAMETER:
        # Entry not found. This probably just means that the iteration has exceeded the number of files available.
        return None
    if response.command() != MessageConst.RESPONSE_GET_FILE_ATTRIBUTES:
        raise ValueError('Unexpected response %s' % response)
    length = response.argument(1, 4)
    checksum = response.argument(5, 2)
    assert length == FileConst.SIZE
    buf = device.read(FileConst.SIZE)
    assert checksum == calculate_data_checksum(buf)
    device.dialogue_end()
    return FileAttributes.from_raw(buf)


class FileAttributes:
    def __init__(self, buf, name, space, password):
        self.buf = buf
        self.name = name
        # TODO: consider renaming to index
        self.space = space
        self.password = password

    @staticmethod
    def from_raw(buf):
        string_fields = ['name', 'password']
        attrs = {
            k: buf_to_int(buf, offset, width)
            for k, (offset, width) in FILE_ATTRIBUTES_FORMAT.items()
            if k not in string_fields
        }
        for k in string_fields:
            (offset, width) = FILE_ATTRIBUTES_FORMAT[k]
            attrs[k] = buf_to_string(buf, offset, width)
        # The file space number. Zero => unbound, 1 to 8 => file spaces 1 to 8 respectively.
        attrs['space'] = FileConst.FILE_SPACE_CODES.index(attrs['space'])
        return attrs


def load_file(device, applet_id, index):
    attrs = get_file_attributes(device, applet_id, index)
    if attrs is None:
        return None
    size = attrs['alloc_size']
    device.dialogue_start()
    result = raw_read_file(device, size, applet_id, index, True)
    device.dialogue_end()
    return result


def read_extended_data(device, size):
    """
    Read binary data blocks in response to some other command, handling segmentation
    and checksum validation.

    The command sequence is:

        While data left to read
            OUT:    0x10    ASMESSAGE_REQUEST_BLOCK_READ
            IN:     0x4d    ASMESSAGE_RESPONSE_BLOCK_READ
            OUT:    data
    """
    logger.debug('Reading extended data of file')
    remaining = size
    message = Message(MessageConst.REQUEST_BLOCK_READ, [])
    result = util.create_buffer(0)

    while remaining > 0:
        response = send_message(device, message)
        if response.command() == MessageConst.RESPONSE_BLOCK_READ_EMPTY:
            break
        if response.command() == MessageConst.RESPONSE_BLOCK_READ:
            blocksize = response.argument(1, 4)
            checksum = response.argument(5, 2)
            buf = device.read(blocksize)
            assert calculate_data_checksum(buf) == checksum
            result.extend(buf)
            remaining = remaining - len(buf)
        else:
            raise ValueError('Unexpected response %s' % response)

    return result.tobytes()


def raw_read_file(device, size, applet_id, index, raw):
    """
    Transfer sequence:
      OUT:    0x12|0x1c   ASMESSAGE_REQUEST_READ_FILE | ASMESSAGE_REQUEST_READ_RAW_FILE
      IN:     0x53        ASMESSAGE_RESPONSE_READ_FILE
      [block read sequence]
    """
    logger.info('Requesting to read a file')
    command = MessageConst.REQUEST_READ_RAW_FILE if raw else MessageConst.REQUEST_READ_FILE
    message = Message(command, [{
        'value': size, 'offset': 1, 'width': 3
    }, {
        'value': index, 'offset': 4, 'width': 1
    }, {
        'value': applet_id, 'offset': 5, 'width': 2
    }])
    send_message(device, message)
    return read_extended_data(device, size)
