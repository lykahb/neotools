import logging
from collections import OrderedDict

from usb import util

from neotools.applet.applet import get_applet_resource_usage
from neotools.device import get_available_space
from neotools.message import Message, MessageConst, send_message, receive_message, assert_success
from neotools.util import calculate_data_checksum, NeotoolsError, data_from_buf, \
    data_to_buf

logger = logging.getLogger(__name__)
FILE_ATTRIBUTES_FORMAT = {
    'size': 40,  # The number of bytes in the file attributes object.
    'fields': OrderedDict([
        # Zero terminated file name string
        # (this appears to be reported wrongly in some cases - bugs in some Neo firmware?)
        ('name', (0x00, 15, str)),
        ('password', (0x10, 7, str)),  # Zero terminated file password string (max six characters?)
        ('min_size', (0x18, 4, int)),  # Minimum file allocation size
        ('alloc_size', (0x1c, 4, int)),  # Actual file allocation size
        ('flags', (0x20, 4, int)),  # Flags (only the lowest 3 bits are used?)
        ('unknown1', (0x24, 1, int)),
        ('space', (0x25, 1, int)),  # file space code
        ('unknown2', (0x26, 2, int)),  # appears to be ignored on write and quasi-random on read
    ])
}


class FileConst:
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
    logger.info('Getting file attributes applet_id=%s index=%s', applet_id, index)
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_GET_FILE_ATTRIBUTES, [(index, 4, 1), (applet_id, 5, 2)])
    response = send_message(device, message)
    if response.command() == MessageConst.ERROR_PARAMETER:
        # Entry not found. This probably just means that the iteration has exceeded the number of files available.
        return None
    assert_success(response, MessageConst.RESPONSE_GET_FILE_ATTRIBUTES)
    length = response.argument(1, 4)
    checksum = response.argument(5, 2)
    assert length == FILE_ATTRIBUTES_FORMAT['size']
    buf = device.read(FILE_ATTRIBUTES_FORMAT['size'])
    assert checksum == calculate_data_checksum(buf)
    device.dialogue_end()
    return FileAttributes.from_raw(index, buf)


class FileAttributes:
    def __init__(self, file_index, name, space, password, min_size, alloc_size, flags):
        self.file_index = file_index
        self.name = name
        # The file space number. Zero => unbound, 1 to 8 => file spaces 1 to 8 respectively.
        self.space = space
        self.password = password
        self.min_size = min_size
        self.alloc_size = alloc_size
        self.flags = flags

    def __str__(self):
        return str(self.__dict__)

    @staticmethod
    def from_raw(file_index: int, buf: bytes):
        attrs = data_from_buf(FILE_ATTRIBUTES_FORMAT, buf)
        space = FileConst.FILE_SPACE_CODES.index(attrs['space'])
        attrs['space'] = space
        attrs['file_index'] = file_index
        del attrs['unknown1']
        del attrs['unknown2']
        return FileAttributes(**attrs)

    def to_raw(self):
        buf = [0] * FILE_ATTRIBUTES_FORMAT['size']
        obj = self.__dict__
        obj['space'] = FileConst.FILE_SPACE_CODES[self.space]
        data_to_buf(FILE_ATTRIBUTES_FORMAT, buf, self.__dict__)
        return buf


def read_file(device, applet_id, file_attrs):
    device.dialogue_start()
    result = raw_read_file(device, applet_id, file_attrs, True)
    device.dialogue_end()
    return result


def clear_file(device, applet_id, file_index):
    attrs = get_file_attributes(device, applet_id, file_index)
    if attrs is None:
        return None
    attrs.alloc_size = attrs.min_size = 0

    device.dialogue_start()
    raw_set_file_attributes(device, attrs, applet_id, file_index)
    message = Message(MessageConst.REQUEST_COMMIT, [(file_index, 4, 1), (applet_id, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_COMMIT)
    raw_write_file(device, b'', applet_id, file_index, True)
    device.dialogue_end()


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
    logger.debug('Reading extended data')
    remaining = size
    message = Message(MessageConst.REQUEST_BLOCK_READ, [])
    result = util.create_buffer(0)

    while remaining > 0:
        response = send_message(device, message)
        if response.command() == MessageConst.RESPONSE_BLOCK_READ_EMPTY:
            break
        if response.command() == MessageConst.RESPONSE_BLOCK_READ:
            block_size = response.argument(1, 4)
            checksum = response.argument(5, 2)
            buf = device.read(block_size, timeout=(block_size * 10 + 600))
            assert calculate_data_checksum(buf) == checksum
            result.extend(buf)
            remaining = remaining - len(buf)
        else:
            raise NeotoolsError('Unexpected response %s' % response)

    return result.tobytes()


def raw_read_file(device, applet_id, file_attrs, raw):
    """
    Transfer sequence:
      OUT:    0x12|0x1c   ASMESSAGE_REQUEST_READ_FILE | ASMESSAGE_REQUEST_READ_RAW_FILE
      IN:     0x53        ASMESSAGE_RESPONSE_READ_FILE
      [block read sequence]
    """
    size = file_attrs.alloc_size
    index = file_attrs.file_index
    logger.info('Requesting to read a file at applet_id=%s, file_index=%s', applet_id, index)
    command = MessageConst.REQUEST_READ_RAW_FILE if raw else MessageConst.REQUEST_READ_FILE
    message = Message(command, [(size, 1, 3), (index, 4, 1), (applet_id, 5, 2)])
    send_message(device, message)
    return read_extended_data(device, size)


def list_files(device, applet_id):
    file_index = 1
    files = []
    while True:
        attrs = get_file_attributes(device, applet_id, file_index)
        if attrs is None:
            break
        files.append(attrs)
        logger.debug('file listed file_index=%s attrs=%s', file_index, attrs)
        file_index = file_index + 1
    return sorted(files, key=lambda f: (f.space, f.name))


def write_extended_data(device, buf):
    remaining = len(buf)
    offset = 0
    while remaining > 0:
        block_size = min(0x400, remaining)
        block = buf[offset:offset + block_size]
        checksum = calculate_data_checksum(block)

        message = Message(MessageConst.REQUEST_BLOCK_WRITE, [(block_size, 1, 4), (checksum, 5, 2)])
        send_message(device, message, MessageConst.RESPONSE_BLOCK_WRITE)

        device.write(block)
        receive_message(device, MessageConst.RESPONSE_BLOCK_WRITE_DONE)

        offset = offset + block_size
        remaining = remaining - block_size


def raw_set_file_attributes(device, attrs, applet_id, file_index):
    """
    OUT:    0x1d    ASMESSAGE_REQUEST_SET_FILE_ATTRIBUTES
    IN:     0x5b    ASMESSAGE_RESPONSE_SET_FILE_ATTRIBUTES
    OUT:    0x02    ASMESSAGE_REQUEST_BLOCK_WRITE
    IN:     0x42    ASMESSAGE_RESPONSE_BLOCK_WRITE
    OUT:    data
    IN:     0x43    ASMESSAGE_RESPONSE_BLOCK_WRITE_DONE
    """
    assert file_index < 256
    logger.debug('Setting file attributes applet_id=%s file_index=%s attrs=%s', applet_id, file_index, attrs)
    message = Message(MessageConst.REQUEST_SET_FILE_ATTRIBUTES, [(file_index, 1, 4), (applet_id, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_SET_FILE_ATTRIBUTES)
    write_extended_data(device, attrs.to_raw())


def raw_write_file(device, buf, applet_id, file_index, raw):
    logger.debug('Preparing to write file')
    size = len(buf)
    command = MessageConst.REQUEST_WRITE_RAW_FILE if raw else MessageConst.REQUEST_WRITE_FILE
    message = Message(command, [(file_index, 1, 1), (size, 2, 3), (applet_id, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_WRITE_FILE)
    logger.debug('Writing block file data')
    write_extended_data(device, buf)
    message = Message(MessageConst.REQUEST_CONFIRM_WRITE_FILE)
    send_message(device, message, MessageConst.RESPONSE_CONFIRM_WRITE_FILE)
    logger.info('Writing file complete')


def create_file(device, filename, password, data, applet_id):
    """

    Create a new file.

    The sequence for creating a new file is a little counter intuitive, starting with the file attributes:

    --> REQUEST_SET_FILE_ATTRIBUTES     ; set up the attributes (see rawWriteAttributes())
    <-- RESPONSE_SET_FILE_ATTRIBUTES
    --> REQUEST_BLOCK_WRITE
    --> Attribute data
    <-- RESPONSE_BLOCK_WRITE_DONE
    --> REQUEST_COMMIT                  ; create the file
    <-- RESPONSE_COMMIT
    --> REQUEST_WRITE_RAW_FILE          ; the following sequence is as for writing an existing file (see rawWriteFile())
    <-- RESPONSE_WRITE_FILE
    --> REQUEST_BLOCK_WRITE
    --> File data
    <-- RESPONSE_BLOCK_WRITE_DONE
    --> REQUEST_CONFIRM_WRITE_FILE
    <-- RESPONSE_CONFIRM_WRITE_FILE

    :param device:
    :param filename:
    :param password:
    :param data: The buffer to write.
    :param applet_id:
    :return: The new FileAttributes.
    """
    usage = get_applet_resource_usage(device, applet_id)
    available_space = get_available_space(device)
    if isinstance(data, str):
        data = data.encode('utf-8')

    size = len(data)
    if size + 1024 > available_space['free_ram']:
        # REVIEW: arbitrarily choosing to keep at least 1k unused on the device
        raise NeotoolsError('The device does not have enough RAM')

    device.dialogue_start()

    file_index = usage['file_count'] + 1
    # The space is unbound, it is not index
    attrs = FileAttributes(file_index, filename, 0, password, size, size, 0)
    raw_set_file_attributes(device, attrs, applet_id, file_index)

    # Sending this message appears to bind the attributes to a new file -
    # not sending it will still result in a new file, but the attributes will not be correct.
    message = Message(MessageConst.REQUEST_COMMIT, [(file_index, 4, 1), (applet_id, 5, 2)])
    send_message(device, message, MessageConst.RESPONSE_COMMIT)
    raw_write_file(device, data, applet_id, file_index, True)
    device.dialogue_end()


def get_file_by_name_or_space(device, applet_id, file_name_or_space):
    """Return FileAttributes for a file.

If space (the string "1" to "8") is passed, will return that space.
Otherwise the file with a given name is returned, or None if it cannot
be found.

    """
    files = list_files(device, applet_id)
    if file_name_or_space.isdigit():
        space = int(file_name_or_space)
        if 1 <= space <= 8:
            for f in files:
                if f.space == space:
                    return f
    for f in files:
        if f.name == file_name_or_space:
            return f


