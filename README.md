# Raghu OS Simulator

A simple operating system kernel simulation built in Python to demonstrate core OS concepts such as file-system navigation, directory management, block allocation, FAT-based disk storage, and defragmentation.

This project includes both a CLI shell and a Tkinter-based graphical interface, making it easy to understand how a minimal kernel manages files and storage in a simulated environment.

## Overview

The goal of this project is to model how an operating system manages files and disk blocks in a simplified way. It focuses on:

- directory and file operations
- current working directory tracking
- FAT (File Allocation Table) block allocation
- file metadata such as creation and modification time
- disk usage statistics
- defragmentation of allocated blocks

This is an educational simulation intended to help students understand how filesystem logic and kernel-level resource management work together.

## Project Structure

- `OS_Kernel_Tkinter_GUI.py` — Tkinter GUI version of the OS simulator
- `os_kern.py` — main kernel implementation and CLI shell
- `os_kernel.py` — additional kernel implementation/version
- `os.py` — related filesystem simulation file
- `README.md` — project documentation

## Features

### File System Simulation
- root directory with nested subdirectories
- file creation, deletion, reading, and writing
- current path tracking with `cd` / `pwd` style behavior
- directory listing and tree visualization

### FAT-Based Disk Management
- simulated disk with 128 blocks
- 64-byte block size
- first-fit block allocation
- free and used block tracking
- chain-based storage for file data

### File Metadata
- file name
- file size
- created timestamp
- modified timestamp
- per-file data location in the storage table

### Defragmentation
- compact file blocks to reduce fragmentation
- demonstrate how disk optimization works in a simple OS model

### GUI Interface
- output console
- file tree panel
- command input area
- current directory display
- FAT block map view
- quick action buttons for common commands
- file tree refresh after operations

## Usage

### Run the GUI version

```bash
python3 OS_Kernel_Tkinter_GUI.py
```

### Run the command-line shell

```bash
python3 os_kern.py
```

## Supported Commands

```text
help
list [path]
make <path>
remove <path>
create <file> [content]
write <file> <text>
append <file> <text>
print <file>
delete <file>
change <path>
current
tree
fat
defrag
exit
```

### Command descriptions

- `help` — show available commands
- `list [path]` — list directory contents
- `make <path>` — create a directory
- `remove <path>` — remove an empty directory
- `create <file> [content]` — create a file with optional text
- `write <file> <text>` — overwrite a file
- `append <file> <text>` — append to a file
- `print <file>` — display file contents
- `delete <file>` — delete a file
- `change <path>` — change the current working directory
- `current` — show current path
- `tree` — show filesystem structure with timestamps
- `fat` — show disk status and FAT map
- `defrag` — compact fragmented blocks
- `exit` — exit the shell or close the GUI

## Demo

Example workflow:

```text
kernel:/$ help
kernel:/$ make docs
kernel:/$ change docs
kernel:/docs$ create ragss.txt "Hello World"
kernel:/docs$ print ragss.txt
Hello World
kernel:/docs$ append ragss.txt " This is my project"
kernel:/docs$ fat
kernel:/docs$ tree
kernel:/docs$ exit
```

The `fat` command displays the number of used and free blocks along with a visual disk map. The `tree` command shows the directory structure and file metadata.

## Technical Notes

This is a simplified educational simulation and not a full operating system kernel. It models core filesystem behavior and disk allocation logic rather than full process scheduling, memory management, or hardware-level OS services.

## Future Work

Planned enhancements for this project include:

- adding process scheduling simulation
- implementing memory allocation models
- adding file permissions and ownership
- supporting nested directory operations more robustly
- improving GUI usability and visual design
- adding export/import of filesystem state
- enhancing simulation realism for OS lab demonstrations

## Conclusion

The Raghu OS Simulator demonstrates the basic ideas behind a kernel-level filesystem in a simple, interactive, and visual way. It helps users understand how files, directories, storage blocks, metadata, and disk optimization work together in a minimal operating system model.
