# NeoTools

Command-line tools for AlphaSmart NEO.

This project aims to provide common functionality like file management, as well as 
access to the low-level system details.
The device driver has been ported from [AlphaSync](https://github.com/tSoniq/alphasync/).

## Commands

Read file by index.

```bash
> neotools files read 1
Once upon a time...
````

Read file by name. Enter the name as it appears on your Neo, without extension.

```bash
> neotools files read intro
Introduction: ...
```

Read file in another language. This is an advanced option to apply a character map that matches the layout of a [language font file](https://github.com/lykahb/neo-ua-font).

```bash
> neotools files read --charmap ua-mac 2
Чув я, чи то снилось мені
Що існує країна мрій
В той країні росте чарівний гай
В гай той може кожний ввійти
```

Copy all files to the directory, preserving their names. It supports the option `charmap` too.
```bash
> neotools files read-all --path archives/
> ls archives
'File 1.txt'    'File 3.txt'    intro.txt
```

Write file to Neo. It can write both by index and file name. It supports the option `charmap` too.
```bash
> neotools files write notes.txt 1
> neotools files write intro.txt intro
```

Get system information.
```bash
> neotools info
{
  "revision_major": 3,
  "revision_minor": 17,
  "name": "System 3 Neo      ",
  "build_date": "Jul 11 2013, 09:44:53",
  "free_rom": 1022224,
  "free_ram": 351744
}
```

Get the installed applet files from the device.
```bash
# Pass applet id and the path where to write the applet
> neotools applets fetch 40967 ControlPanel.OS3KApp
> neotools applets fetch 0 romdump.os3kos
```

Analyze applet files.
```bash
> neotools applets inspect ~/projects/AlphaSmart\ Manager\ 2/SmartApplets/ControlPanel.OS3KApp
{
  "applet_type": "Applet program",
  "header": {
    "signature": 3237998253,
    "rom_size": 27412,
    "ram_size": 416,
    "settings_offset": 0,
    "flags": 4278190208,
    "applet_id": 40967,
    "header_version": 1,
    "file_count": 0,
    "name": "Control Panel",
    "version_major": 1,
    "version_minor": 0,
    "version_revision": 55,
    "language_id": 1,
    "info": "Copyright (c) 2005-2012 by Renaissance Learning, Inc.",
    "min_asm_version": 0,
    "file_space": 0
  }
}
```

Install applets.
```bash
> neotools applets install ~/projects/AlphaSmart\ Manager\ 2/SmartApplets/ControlPanel.OS3KApp
Are you sure you want to install an applet? This is an experimental feature. [y/N]: y
Installing applet Control Panel
Initialization for writing the applet
Initialized writing the applet
Started writing applet content
Completed writing applet content
Finalizing writing the applet
Finalized writing the applet
```

Remove all applets.
```bash
> neotools applets remove-all
Are you sure you want to remove all applets? [y/N]: y
```

Inspect applets and manage their settings.
```bash
> neotools applets list
[
  {
    "name": "System",
    "applet_id": 0,
    "rom_size": 401408,
    ...
  },
...
```

```bash
> neotools applets get-settings 0
[
  {
    "label": "Auto Repeat (16385)",
    "ident": 16385,
    "type": "OPTION",
    "value": {
      "selected": "On (4097)",
      "options": [
        "On (4097)",
        "Off (4098)"
      ]
    }
  },
...
```
Update system applet settings. Set idle time to five minutes.
```bash
> neotools --verbose applets set-settings 0 16388 5 4 59
```



## Installation

### Linux

1. Confirm that you have Python 3 on your machine.
2. Install neotools from the Python package repository with:

   `pip3 install neotools`

### Mac

1. Install a package manager [Brew](https://brew.sh).
2. Install libusb, a cross-platform library to access USB devices:

   `brew install libusb`
3. Install neotools from the Python package repository with:

   `pip3 install neotools`

## Troubleshooting

### Access denied
`usb.core.USBError: [Errno 13] Access denied (insufficient permissions)`  
A simple way to fix it is to run the command with `sudo`. However, it is
better to give granular udev permissions to neotools. Add the following rule to 
the udev rules, into, for example `/lib/udev/rules.d/50-alphasmart.rules`.

For systems based on Debian:
```
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd01", MODE="660", GROUP="plugdev"
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd04", MODE="660", GROUP="plugdev"
```
Make sure that your user is a member of the `plugdev` group.

For systems based on Arch:
```
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd01", TAG+="uaccess"
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd04", TAG+="uaccess"
```

### Attempting to enter the Updater Mode
The device displays this message and is not responsive.
This happens when there are no applets installed. It is normal after running the
Neotools command `applets clear`. To resolve the problem, install an applet,
for example, AlphaWord or ControlPanel.
