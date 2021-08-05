import logging

from neotools.util import NeotoolsError

logger = logging.getLogger(__name__)


#  Example exchanges:
# 
# -->  bfffa943 : 00000000 : 8  =   0b 00 00 00 00 00 00 0b   ........
# <--   bfffa943 : 00000000 : 8  =   87 00 05 8f 0c 00 24 4b   ......$K      Neo displays "Error: Not enough RAM for operation"
# 
# -->  bfffa943 : 00000000 : 8  =   16 00 00 00 00 00 00 16   ........
# <--   bfffa943 : 00000000 : 8  =   8f 00 00 00 00 00 00 8f   ........
# 
# -->  bfffa943 : 00000000 : 8  =   17 00 00 00 00 00 00 17   ........
# <--   bfffa943 : 00000000 : 8  =   8f 00 00 00 00 00 00 8f   ........
# 
# -->  bfffa943 : 00000000 : 8  =   19 00 00 00 00 00 00 19   ........
# <--   bfffa943 : 00000000 : 8  =   57 00 00 00 00 00 00 57   W......W
# 
# -->  bfffa943 : 00000000 : 8  =   1a 00 00 00 00 00 00 1a   ........      (with Neo running the Small ROM)
# <--   bfffa943 : 00000000 : 8  =   92 00 00 00 00 00 00 92   ........
# 
# -->  bfffa943 : 00000000 : 8  =   1a 00 00 00 00 00 00 1a   ........      (with Neo running the standard ROM)
# <--   bfffa943 : 00000000 : 8  =   58 00 0e ac 34 05 8f da   X...4...
# 
# -->  bfffa943 : 00000000 : 8  =   1b 00 00 00 00 00 00 1b   ........
# <--   bfffa943 : 00000000 : 8  =   90 00 00 00 00 00 00 90   ........
# 
# -->  bfffa943 : 00000000 : 8  =   1b 00 00 00 00 a0 00 bb   ........
# <--   bfffa943 : 00000000 : 8  =   59 00 00 80 00 00 08 e1   Y.......
# 
# -->  bfffa943 : 00000000 : 8  =   1b ff ff ff ff a0 00 b7   ........
# <--   bfffa943 : 00000000 : 8  =   59 00 00 10 00 00 08 71   Y......q


class MessageConst:
    REQUEST_VERSION = 0x00  # (len32, csum16): Obtain the OS version information. */
    REQUEST_01 = 0x01  # Unknown (generates response 8f). */
    REQUEST_BLOCK_WRITE = 0x02  # (len32, csum16): write a 1k or less block of data. */
    REQUEST_03 = 0x03  # Unknown (generates response 0x8f). */
    REQUEST_LIST_APPLETS = 0x04  # (first32, count16): read an array of applet headers. */
    REQUEST_REMOVE_APPLET = 0x05  # (5, applet16): constant 5. */
    REQUEST_WRITE_APPLET = 0x06  # (len32, z16): write a new applet. */
    REQUEST_FINALIZE_WRITING_APPLET = 0x07  # (z48): unknown - used when writing an applet. */
    REQUEST_RESTART = 0x08  # (z48): causes the device to reset and restart as a HID device. */
    REQUEST_SET_BAUDRATE = 0x09  # (baud32, z16). Try to set the specified baud rate. */
    REQUEST_0A = 0x0a  # Unknown - returns response 0x90 in tests & Neo displays nothing. */
    REQUEST_PROGRAMMING_APPLET_BLOCK = 0x0b  # (z48): unknown - used when writing an applet. */
    REQUEST_GET_SETTINGS = 0x0c  # (flags, applet16): read the specified file attributes. */
    REQUEST_SET_SETTINGS = 0x0d  # (flags, applet16): write the specified file attributes. */
    REQUEST_SET_APPLET = 0x0e  # (z32, applet16): used when setting applet properties. */
    REQUEST_READ_APPLET = 0x0f  # (z32, applet16): used when reading an applet. */
    REQUEST_BLOCK_READ = 0x10  # (z48): Request the next requested block of data from the device. */
    REQUEST_ERASE_APPLETS = 0x11  # (z48): causes Neo to erase all smart applets - may take a very long time to return a reply. */
    REQUEST_READ_FILE = 0x12  # (index32, applet16): used to read data from the specified file. */
    REQUEST_GET_FILE_ATTRIBUTES = 0x13  # (index32, applet16): used to read the file attributes. */
    REQUEST_WRITE_FILE = 0x14  # (index8, len24, applet16): request write of a file. */
    REQUEST_CONFIRM_WRITE_FILE = 0x15  # (z48): used to complete writing of a file. */
    REQUEST_CLEAR_SEGMENT_MAP = 0x16  # (z48): used when updating ROM for System 3 and System 3 Neo. */
    REQUEST_ERASE_SEGMENTS = 0x17  # (unknown): depends on contents of ROM file. used when updating ROM for System 3 and System 3 Neo. */
    REQUEST_SMALL_ROM_UPDATER = 0x18  # (z48?): used to enter the updater ROM when adding an applet. */
    REQUEST_19 = 0x19  # Unknown - may be specific to AlphaHub devices? Generates response 0x57. */
    REQUEST_GET_AVAIL_SPACE = 0x1a  # (z48): used to return the available space. */
    REQUEST_GET_USED_SPACE = 0x1b  # (select32, applet16): used to obtain the file space used by an applet select32 is zero for the largest file, non-zero for all files. */
    REQUEST_READ_RAW_FILE = 0x1c  # (index32, applet16): used to read a file in raw mode. */
    REQUEST_SET_FILE_ATTRIBUTES = 0x1d  # (index32, applet16): used when setting file attributes. */
    REQUEST_COMMIT = 0x1e  # (index32, applet16): used to commit changes following SET_FILE_ATTRIBUTES. */
    REQUEST_WRITE_RAW_FILE = 0x1f  # (index8, len24, applet16): request write of a file. */

    RESPONSE_VERSION = 0x40  # (len32, csum16): returns version information. */
    RESPONSE_41 = 0x41  # Unknown. */
    RESPONSE_BLOCK_WRITE = 0x42  # (z48): reply to block write request. */
    RESPONSE_BLOCK_WRITE_DONE = 0x43  # (z43): reply to block write request. */
    RESPONSE_LIST_APPLETS = 0x44  # (len32, csum16): returns array of applet headers. */
    RESPONSE_REMOVE_APPLET = 0x45  # (z48): reply to REQUEST_REMOVE_APPLET. */
    RESPONSE_45 = 0x41  # Unknown. */
    RESPONSE_WRITE_APPLET = 0x46  # (z48?): sent in response to ASMESSAGE_REQUEST_WRITE_APPLET */
    RESPONSE_PROGRAMMING_APPLET_BLOCK = 0x47  # (z48?): unknown: sent in response to ASMESSAGE_REQUEST_0B - possibly an ok to proceed check? */
    RESPONSE_FINALIZE_WRITING_APPLET = 0x48  # (z48?): unknown: sent in response to ASMESSAGE_REQUEST_07 */
    RESPONSE_49 = 0x49  # Unknown. */
    RESPONSE_SET_BAUDRATE = 0x4a  # (baud32, z16): response to ASMESSAGE_REQUEST_BAUDRATE. */
    RESPONSE_GET_SETTINGS = 0x4b  # (len32, csum16): returns file attribute data. */
    RESPONSE_SET_APPLET = 0x4c  # (z48?): reply to ASMESSAGE_REQUEST_SET_APPLET. */
    RESPONSE_BLOCK_READ = 0x4d  # (len32, csum16): reply to  ASMESSAGE_REQUEST_BLOCK_READ. */
    RESPONSE_BLOCK_READ_EMPTY = 0x4e  # ? */
    RESPONSE_RESPONSE_ERASE_APPLETS = 0x4f  # (z48?): reply to ASMESSAGE_REQUEST_ERASE_APPLETS. */
    RESPONSE_WRITE_FILE = 0x50  # (z48): */
    RESPONSE_CONFIRM_WRITE_FILE = 0x51  # (z48): */
    RESPONSE_RESTART = 0x52  # (z48): */
    RESPONSE_READ_FILE = 0x53  # (length32, ?16): */
    RESPONSE_CLEAR_SEGMENT_MAP = 0x54  # (z48?): send in response to ASMESSAGE_REQUEST_16. */
    RESPONSE_ERASE_SEGMENTS = 0x55  # (z48?): send in response to ASMESSAGE_REQUEST_17. */
    RESPONSE_SMALL_ROM_UPDATER = 0x56  # (z48): reply to ASMESSAGE_REQUEST_SMALL_ROM_UPDATER, indicating using small ROM. */
    RESPONSE_57 = 0x57  # Unknown. Sent in response to 0x19. */
    RESPONSE_GET_AVAIL_SPACE = 0x58  # (flash32, ram16): reply to ASMESSAGE_REQUEST_GET_AVAIL_SPACE. ram size should be multiplied by 256. */
    RESPONSE_GET_USED_SPACE = 0x59  # (ram32, files16): returns the number of bytes of RAM and the number of files used by an applet. */
    RESPONSE_GET_FILE_ATTRIBUTES = 0x5a
    RESPONSE_SET_FILE_ATTRIBUTES = 0x5b
    RESPONSE_COMMIT = 0x5c

    ERROR_INVALID_BAUDRATE = 0x86  # (z48): Sent if a bad BAUD rate is given. */
    ERROR_87 = 0x87  # (unknown): Unknown (seen in response to a bogus cmd 0x0b). */
    ERROR_INVALID_APPLET = 0x8a  # (z48): Specified Applet ID is not recognised. */
    ERROR_PROTOCOL = 0x8f  # (z48): Sent in response to command block checksum errors or invalid command codes. */
    ERROR_PARAMETER = 0x90  # (error32, z16): appears to return an error number (usually negative). */
    ERROR_OUTOFMEMORY = 0x91  # May be seen if trying to write too large a file. */
    ERROR_94 = 0x94  # Seen in response to sending command code 0x20 */


class Message:
    def __init__(self, command=0, args=None):
        # message is eight bytes
        self.m_data = [0] * 8
        self.m_data[0] = command

        if args is None:
            args = []

        for (value, offset, width) in args:
            self._set_argument(value, offset, width)

        self.m_data[7] = self.checksum()

    @staticmethod
    def from_raw(m_data):
        message = Message()
        message.m_data = m_data
        return message

    @staticmethod
    def _validate_offset_width(offset, width):
        if not (1 <= width <= 4):
            raise ValueError('Invalid width')
        if offset < 1 or offset + width > 7:
            raise ValueError('Invalid offset')

    def _set_argument(self, value, offset, width):
        self._validate_offset_width(offset, width)

        i = width - 1
        while i >= 0:
            self.m_data[offset + i] = value & 0xFF
            value = value >> 8
            i = i - 1

    def command(self):
        return self.m_data[0]

    def argument(self, offset, width):
        self._validate_offset_width(offset, width)
        value = 0
        for byte in self.m_data[offset:offset + width]:
            value = value * 0x100 + byte
        return value

    def checksum(self):
        # The first seven bytes out of eight
        return sum(self.m_data[:-1]) & 0xFF

    def __str__(self):
        return str(self.m_data)


def send_message(device, message, success_code=None, timeout=None):
    device.write(message.m_data, timeout=timeout)
    return receive_message(device, success_code, timeout=timeout)


def receive_message(device, success_code=None, timeout=None):
    response = Message.from_raw(device.read(8, timeout))
    if success_code is not None:
        assert_success(response, success_code)
    return response


def assert_success(response, success_code):
    code = response.command()
    if code == success_code:
        return

    error_map = {
        MessageConst.ERROR_INVALID_BAUDRATE: 'Bad baud rate',
        MessageConst.ERROR_87: 'Unknown error',
        MessageConst.ERROR_94: 'Unknown error',
        MessageConst.ERROR_INVALID_APPLET: 'Specified Applet ID is not recognised',
        MessageConst.ERROR_PROTOCOL: 'Protocol error',
        MessageConst.ERROR_PARAMETER: 'Error number',
        MessageConst.ERROR_OUTOFMEMORY: 'Out of memory'
    }
    error_text = error_map.get(code, 'Unknown error')

    raise NeotoolsError(f'Mismatching response code {hex(code)}. {error_text}.\n{response.m_data}')
