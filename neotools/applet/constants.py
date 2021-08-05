from collections import OrderedDict
from enum import Enum


# Applet fields with offset and width in to the applet header data
# (usually located at the start of the applet).
APPLET_HEADER_FORMAT = {
    'size': 0x84,  # The total size of the header
    'fields': OrderedDict([
        ('signature', (0x00, 4, int)),  # The signature word field.
        ('rom_size', (0x04, 4, int)),  # The ROM size field.
        ('ram_size', (0x08, 4, int)),  # The size of working RAM field.
        ('settings_offset', (0x0c, 4, int)),  # Settings parameters field.
        ('flags', (0x10, 4, int)),
        ('applet_id', (0x14, 2, int)),
        ('header_version', (0x16, 1, int)),  # ByteHeader version code field.
        ('file_count', (0x17, 1, int)),
        ('name', (0x18, 36, str)),  # Display name.
        ('version_major', (0x3c, 1, int)),  # Major version number field.
        ('version_minor', (0x3d, 1, int)),  # Minor version number field.
        ('version_revision', (0x3e, 1, int)),  # Revision code (ASCII) field.
        ('language_id', (0x3f, 1, int)),  # Localised language field.
        ('info', (0x40, 60, str)),  # The info (copyright) string field.
        ('min_asm_version', (0x7c, 4, int)),  # Minimum AlphaSmart Manager version required field.
        ('file_space', (0x80, 4, int)),  # The required file space field.
    ])}

APPLET_SETTINGS_FORMAT = {
    'size': None,
    'fields': OrderedDict([
        ('type', (0x00, 2, int)),
        ('ident', (0x02, 2, int)),
        ('length', (0x04, 2, int))
    ])
}
APPLET_SETTINGS_RANGE32_FORMAT = {
    'size': 12,
    'fields': {
        'default': (0x00, 4, int),
        'min': (0x04, 4, int),
        'max': (0x08, 4, int)
    }
}

SIGNATURE_START = 0xc0ffeead  # The expected value of the signature word.#
SIGNATURE_END = 0xcafefeed

# Known applet flags:
# *
# *  AlphaWord:      0xff0000ce      1100.1110
# *  KAZ:            0xff000000      0000.0000
# *  Calculator:     0xff000000      0000.0000
# *  Beamer:         0xff000000      0000.0000
# *  Control Panel:  0xff000080      1000.0000
# *  Spell Check:    0xff000001      0000.0001
# *  Thesaurus:      0xff000001      0000.0001
# *  Font files:     0xff000031      0011.0001
# *  System:         0xff000011      0001.0001

FLAGS_HIDDEN = 0x01  # If set, the applet is hidden.

# Reading more than 7 headers will cause a crash on some Neos (1k buffer overflow?)
LIST_APPLETS_REQUEST_COUNT = 7


class AppletSettingsType(Enum):
    NONE = 0x0000  # No item is present (used to mark end of data).
    LABEL = 0x0001  # Item is a null terminated string (fixed label).
    RANGE_32 = 0x0102  # Item is an integer numeric range: {default, min, max}.
    OPTION = 0x0103  # Item is a list of item IDs: {default, a, b, c...}.
    # Item is a password (c-string). Used for AW "File Passwords" and system "Master Password". Max 6 characters.
    PASSWORD_6 = 0x0105
    DESCRIPTION = 0x0106  # Item is a null terminated string constant for descriptive purposes only.
    FILE_PASSWORD = 0xc001  # Item is a file password (c-string). File is identified by the ident field.
    APPLET_ID = 0x8002  # Item is a U16 applet ID.


class AppletSettingsIdent:
    # Well known settings ident values.
    # Bit 31 is set if the ident is local to an applet, or clear if it is global (system applet).
    # Bit 30 is set for file passwords (possible security flag?)
    NONE = 0x0000  # No item is present (used to mark end of data).
    SYSTEM_ON = 0x1001  # Setting is 'on'
    SYSTEM_OFF = 0x1002  # Setting is 'off'
    SYSTEM_YES = 0x100c  # Setting is 'yes'
    SYSTEM_NO = 0x100d  # Setting is 'no'
    SYSTEM_PASSWORD = 0x400b  # Master password, as type 0x0105.
    ALPHAWORD_CLEARFILES = 0x8003  # Clear all files, as type 0x0103. Use a value of SYSTEM_ON to trigger.
    ALPHAWORD_MAXFILESIZE = 0x1010  # Get maximum file size information. Type is Range32.
    ALPHAWORD_MINFILESIZE = 0x1011  # Get minimum file size information. Type is Range32.


class AppletIds:
    INVALID = 0xffff
    SYSTEM = 0X000  # OS applet id
    ALPHAWORD = 0xa000
    DICTIONARY = 0xa005


# The values match the classification of NEOManager, together with signatures
class AppletType:
    REGULAR = 0x11
    SYSTEM_3 = 0
    OS3000_SMALL_ROM = 1
    ALPHASMART_UPDATER = 2
    SYSTEM_3_NEO = 3
    OS3KNEO_SMALL_ROM = 4
