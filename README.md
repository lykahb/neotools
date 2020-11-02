# AlphaTools

Command-line tools for AlphaSmart NEO.

This project aims to provide common functionality like file management, as well as 
access to the low-level system details.
The device driver has been ported from [AlphaSync](https://github.com/tSoniq/alphasync/).

## Commands

Read file by index.

```bash
> alphatools files read 1
Once upon a time...
````

Copy all files to the directory, preserving their names.
```bash
> alphatools files read-all --path archives/
> ls archives
'File 1.txt'    'File 3.txt'    intro.txt
```

Write file to Neo
```bash
> alphatools files write notes.txt 1
```

Inspect applets and manage their settings
```bash
> alphatools applets list
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
> alphatools applets get-settings 0
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
> alphatools --verbose applets set-settings 0 16388 5 4 59
```



## Installation

Confirm that you have Python 3 on your machine. Install alphatools from the Python package repository with:
`pip3 install alphatools`.

## Troubleshooting

### Access denied
`usb.core.USBError: [Errno 13] Access denied (insufficient permissions)`  
A simple way to fix it is to run the command with `sudo`. However, it is
better to give granular udev permissions to alphatools. Add the following rule to 
the udev rules, into, for example `/lib/udev/rules.d/50-alphasmart.rules`.
```
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd01", MODE="660", GROUP="plugdev"
ACTION=="add", SUBSYSTEMS=="usb", ATTRS{idVendor}=="081e", ATTRS{idProduct}=="bd04", MODE="660", GROUP="plugdev"
```
Make sure that your user is a member of the `plugdev` group.
