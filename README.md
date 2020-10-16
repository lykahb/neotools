# Alphasmart-tools

This project aims to create cross-platform command-line tools that replace Neo Manager.

## Running Neo Manager in VirtualBox
Install VirtualBox
Create a virtual machine. I used a free Windows XP Mode virtual disk from the Microsoft website. Its archive has a VHD disk.

Install VirtualBox Extension Pack for better USB support. Its version must exactly match the version of VirtualBox.
Install guest additions into the VM.

In the virtual machine settings:
* Enable USB 2.0 EHCI 
* Set two USB filters, for the keyboard and comms parts of the device:
vendorId=081e productId=bd01
vendorId=081e productId=bd04

Install Neo Manager. If it fails with digital certificate error, update the OS or install the certificate manually.
Plug in AlphaSmart and wait a few minutes till the operating system recognizes it and offers to install a driver.

## Python development

## USB captured data
There is no open-source implementation of installing applets. So this is the focus of the USB set under usb_pcap.

Captured with WireShark on Linux host, with NEO Manager 3.9.3 running on Windows XP virtual machine.

* connection - exchange until Neo appears in the manager.
* get_info - "Get NEO Info" from the manager menu.
* install_applets_remove_unlisted - installing AlphaWord Plus 3.4 and Control Panel 1.07 with the checkmark for "Delete SmartApplets that are not in the Install List from all NEO devices"
* install_calculator302 - install a single applet Calculator 3.02
* install_thesaurus - Thesaurus Large USA 1.1. The manager backed up the applets, removed them and reinstalled again with thesaurus. It happened only for this applet. The delete checkmark was off.
* install_spellcheck_large_usa_103 - SpellCheck Large USA 1.03
* send_file3_to_device - File starts with the line "this is file 3 text", ends with "456"
* send_file4_to_device - File starts with the line "this is file 4 text", ends with "456"
* view_file - download a text file
* install_multiple_fonts - the default fonts micro, medium, large, very large, extra large.
* install_neofont_atto11
* install_neofont_bold6
* install_neofont_femto9
* install_neofont_small6
* install_neofont_tech6


