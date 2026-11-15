# os_kernel.py
from __future__ import annotations
import sys
import shlex
from math import ceil
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
BLOCK_SIZE = 64       # bytes per block
NUM_BLOCKS = 128      # total blocks in simulated disk
ROOT_NAME = "/"

# --------------------------
# FAT (File Allocation Table) & Disk Simulation
# --------------------------
class FAT:
    """
    FAT simulation:
    - table[i] is None -> free block
    - table[i] == -1 -> end-of-chain
    - table[i] == j (int) -> next block index in chain
    - data[i] stores bytes for that block
    """
    def __init__(self, num_blocks: int):
        self.num_blocks = num_blocks
        self.table: List[Optional[int]] = [None] * num_blocks
        self.data: List[bytes] = [b""] * num_blocks

    def free_blocks_count(self) -> int:
        return sum(1 for v in self.table if v is None)

    def allocate_blocks(self, k: int) -> List[int]:
        """First-fit allocation (non-contiguous allowed)."""
        free = [i for i, v in enumerate(self.table) if v is None]
        if len(free) < k:
            raise MemoryError(f"Not enough free blocks (need {k}, have {len(free)})")
        alloc = free[:k]
        for idx in range(len(alloc) - 1):
            self.table[alloc[idx]] = alloc[idx + 1]
        self.table[alloc[-1]] = -1
        for b in alloc:
            self.data[b] = b""
        return alloc

    def allocate_contiguous(self, start_idx: int, k: int) -> List[int]:
        """Allocate k contiguous blocks starting at start_idx. Caller must ensure bounds and freeness."""
        if start_idx + k > self.num_blocks:
            raise MemoryError("Not enough contiguous space at requested location.")
        for i in range(start_idx, start_idx + k):
            if self.table[i] is not None:
                raise MemoryError("Requested contiguous region is not free.")
        for i in range(start_idx, start_idx + k - 1):
            self.table[i] = i + 1
        self.table[start_idx + k - 1] = -1
        for i in range(start_idx, start_idx + k):
            self.data[i] = b""
        return list(range(start_idx, start_idx + k))

    def free_chain(self, start_block: int) -> None:
        idx = start_block
        visited = set()
        while idx is not None and idx != -1 and idx not in visited:
            visited.add(idx)
            nxt = self.table[idx]
            self.table[idx] = None
            self.data[idx] = b""
            idx = nxt

    def write_to_chain(self, chain: List[int], content: bytes) -> None:
        # write content in BLOCK_SIZE chunks into chain slots
        for i, block_idx in enumerate(chain):
            start = i * BLOCK_SIZE
            chunk = content[start:start + BLOCK_SIZE]
            self.data[block_idx] = chunk

    def read_chain(self, start_block: int) -> bytes:
        parts = []
        idx = start_block
        visited = set()
        while idx is not None and idx != -1 and idx not in visited:
            visited.add(idx)
            parts.append(self.data[idx])
            idx = self.table[idx]
        return b"".join(parts)

    def status_map(self) -> str:
        # returns short map: '.' free, '#' used
        return "".join("." if v is None else "#" for v in self.table)

    def reset(self):
        self.table = [None] * self.num_blocks
        self.data = [b""] * self.num_blocks

# --------------------------
# File & Directory Structures (with metadata)
# --------------------------
class FileEntry:
    def __init__(self, name: str, start_block: Optional[int], size: int = 0):
        self.name = name
        self.start_block = start_block
        self.size = size  # bytes
        now = datetime.now()
        self.created_at: datetime = now
        self.modified_at: datetime = now

    def touch_modified(self):
        self.modified_at = datetime.now()

    def __repr__(self):
        return (f"FileEntry(name={self.name!r}, start={self.start_block}, size={self.size}, "
                f"created={self.created_at.isoformat()}, modified={self.modified_at.isoformat()})")

class Directory:
    def __init__(self, name: str, parent: Optional[Directory] = None):
        self.name = name
        self.parent = parent
        self.children_dirs: Dict[str, Directory] = {}
        self.children_files: Dict[str, FileEntry] = {}

    def path(self) -> str:
        if self.parent is None:
            return ROOT_NAME
        parts = []
        cur = self
        while cur.parent is not None:
            parts.append(cur.name)
            cur = cur.parent
        return "/" + "/".join(reversed(parts))

    def add_dir(self, name: str) -> Directory:
        if name in self.children_dirs or name in self.children_files:
            raise FileExistsError(f"Name '{name}' already exists")
        nd = Directory(name, parent=self)
        self.children_dirs[name] = nd
        return nd

    def add_file(self, file_entry: FileEntry) -> None:
        if file_entry.name in self.children_dirs or file_entry.name in self.children_files:
            raise FileExistsError(f"Name '{file_entry.name}' already exists")
        self.children_files[file_entry.name] = file_entry

    def remove_file(self, name: str) -> FileEntry:
        if name not in self.children_files:
            raise FileNotFoundError(name)
        return self.children_files.pop(name)

    def remove_dir(self, name: str) -> Directory:
        if name not in self.children_dirs:
            raise FileNotFoundError(name)
        return self.children_dirs.pop(name)

# --------------------------
# Simple Kernel / Filesystem Controller (includes defragmentation)
# --------------------------
class SimpleOSKernel:
    def __init__(self):
        self.fat = FAT(NUM_BLOCKS)
        self.root = Directory(ROOT_NAME, parent=None)
        self.cwd = self.root

    # ---- Path helpers ----
    def _resolve(self, path: str) -> Tuple[Directory, str]:
        if path == "/":
            return (self.root, "")
        parts = [p for p in path.split("/") if p != ""]
        cur = self.root if path.startswith("/") else self.cwd
        for part in parts[:-1]:
            if part == ".":
                continue
            if part == "..":
                cur = cur.parent if cur.parent is not None else cur
                continue
            if part not in cur.children_dirs:
                raise FileNotFoundError(f"Directory '{part}' not found in path '{path}'")
            cur = cur.children_dirs[part]
        basename = parts[-1] if parts else ""
        return cur, basename

    def _dir_from_path(self, path: str) -> Directory:
        if path == "/":
            return self.root
        parts = [p for p in path.split("/") if p != ""]
        cur = self.root if path.startswith("/") else self.cwd
        for part in parts:
            if part == ".":
                continue
            if part == "..":
                cur = cur.parent if cur.parent is not None else cur
                continue
            if part not in cur.children_dirs:
                raise FileNotFoundError(f"Directory '{part}' not found in path '{path}'")
            cur = cur.children_dirs[part]
        return cur

    # ---- File operations ----
    def create(self, path: str, content: str = "") -> None:
        parent, name = self._resolve(path)
        if not name:
            raise ValueError("Invalid file name")
        if name in parent.children_dirs:
            raise FileExistsError("A directory with that name exists")
        b = content.encode()
        blocks_needed = ceil(len(b) / BLOCK_SIZE) if len(b) > 0 else 0
        start = None
        if blocks_needed > 0:
            chain = self.fat.allocate_blocks(blocks_needed)
            start = chain[0]
            self.fat.write_to_chain(chain, b)
        entry = FileEntry(name, start, size=len(b))
        parent.add_file(entry)

    def read(self, path: str) -> str:
        parent, name = self._resolve(path)
        if name not in parent.children_files:
            raise FileNotFoundError(name)
        entry = parent.children_files[name]
        if entry.start_block is None:
            return ""
        raw = self.fat.read_chain(entry.start_block)
        return raw[:entry.size].decode()

    def write(self, path: str, content: str) -> None:
        parent, name = self._resolve(path)
        if name not in parent.children_files:
            # create new if doesn't exist
            self.create(path, content)
            return
        entry = parent.children_files[name]
        if entry.start_block is not None:
            self.fat.free_chain(entry.start_block)
        b = content.encode()
        blocks_needed = ceil(len(b) / BLOCK_SIZE) if len(b) > 0 else 0
        start = None
        if blocks_needed > 0:
            chain = self.fat.allocate_blocks(blocks_needed)
            start = chain[0]
            self.fat.write_to_chain(chain, b)
        entry.start_block = start
        entry.size = len(b)
        entry.touch_modified()

    def append(self, path: str, content: str) -> None:
        parent, name = self._resolve(path)
        if name not in parent.children_files:
            self.create(path, content)
            return
        entry = parent.children_files[name]
        existing = b""
        if entry.start_block is not None:
            existing = self.fat.read_chain(entry.start_block)[:entry.size]
            self.fat.free_chain(entry.start_block)
        new = existing + content.encode()
        blocks_needed = ceil(len(new) / BLOCK_SIZE) if len(new) > 0 else 0
        start = None
        if blocks_needed > 0:
            chain = self.fat.allocate_blocks(blocks_needed)
            start = chain[0]
            self.fat.write_to_chain(chain, new)
        entry.start_block = start
        entry.size = len(new)
        entry.touch_modified()

    def delete(self, path: str) -> None:
        parent, name = self._resolve(path)
        if name not in parent.children_files:
            raise FileNotFoundError(name)
        entry = parent.children_files[name]
        if entry.start_block is not None:
            self.fat.free_chain(entry.start_block)
        parent.remove_file(name)

    # ---- Directory operations ----
    def mkdir(self, path: str) -> None:
        parent, name = self._resolve(path)
        if not name:
            raise ValueError("Invalid directory name")
        parent.add_dir(name)

    def rmdir(self, path: str) -> None:
        parent, name = self._resolve(path)
        if name not in parent.children_dirs:
            raise FileNotFoundError(name)
        target = parent.children_dirs[name]
        if target.children_dirs or target.children_files:
            raise OSError("Directory not empty")
        parent.remove_dir(name)

    def ls(self, path: Optional[str] = None) -> List[str]:
        target = self.cwd if path is None else self._dir_from_path(path)
        items = []
        for d in sorted(target.children_dirs):
            items.append(d + "/")
        for f in sorted(target.children_files):
            items.append(f)
        return items

    def cd(self, path: str) -> None:
        self.cwd = self._dir_from_path(path)

    def pwd(self) -> str:
        return self.cwd.path()

    def tree(self, dir_obj: Optional[Directory] = None, prefix: str = "") -> None:
        if dir_obj is None:
            dir_obj = self.root
            print("/")
        for dname, d in sorted(dir_obj.children_dirs.items()):
            print(prefix + "|-- " + dname + "/")
            self.tree(d, prefix + "    ")
        for fname, f in sorted(dir_obj.children_files.items()):
            print(prefix + "|-- " + fname + f"  (size={f.size}B)  created={f.created_at.strftime('%Y-%m-%d %H:%M:%S')} modified={f.modified_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def fat_status(self) -> None:
        free = self.fat.free_blocks_count()
        used = NUM_BLOCKS - free
        print(f"Blocks: {NUM_BLOCKS} | Used: {used} | Free: {free}")
        m = self.fat.status_map()
        for i in range(0, len(m), 32):
            print(m[i:i+32])
# --------------------------
# Minimal Shell (CLI) exposing kernel commands (REPL)
# --------------------------
HELP_TEXT = """Available commands:
  help                       Show this help
  list [path]                List directory
  make <path>                Create directory
  remove <path>              Remove empty directory
  create <file> [content]    Create file (optionally with content)
  write <file> <text>        Overwrite file with text
  append <file> <text>       Append text to file
  print <file>               Print file contents
  delete <file>              Delete file
  change <path>              Change directory
  current                    Show current path
  tree                       Show full filesystem tree (with timestamps)
  fat                        Show FAT/disk status
  exit                       Exit shell
"""

def run_shell():
    kernel = SimpleOSKernel()
    print("Simple RaghuOS Kernel Simulation (type 'help' for commands)")
    while True:
        try:
            raw = input(f"RaghuOS:{kernel.pwd()}$ ")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        try:
            tokens = shlex.split(raw)
        except ValueError as e:
            print("Parsing error:", e)
            continue
        if not tokens:
            continue
        cmd, *args = tokens
        try:
            if cmd == "help":
                print(HELP_TEXT)
            elif cmd == "list":
                path = args[0] if args else None
                items = kernel.ls(path)
                for it in items:
                    print(it)
            elif cmd == "make":
                if not args:
                    print("Usage: mkdir <path>")
                else:
                    kernel.mkdir(args[0])
            elif cmd == "remove":
                if not args:
                    print("Usage: rmdir <path>")
                else:
                    kernel.rmdir(args[0])
            elif cmd == "create":
                if not args:
                    print("Usage: create <file> [content]")
                else:
                    content = args[1] if len(args) > 1 else ""
                    kernel.create(args[0], content)
            elif cmd == "write":
                if len(args) < 2:
                    print("Usage: write <file> <text>")
                else:
                    path = args[0]
                    text = " ".join(args[1:])
                    kernel.write(path, text)
            elif cmd == "append":
                if len(args) < 2:
                    print("Usage: append <file> <text>")
                else:
                    path = args[0]
                    text = " ".join(args[1:])
                    kernel.append(path, text)
            elif cmd == "print":
                if not args:
                    print("Usage: cat <file>")
                else:
                    print(kernel.read(args[0]))
            elif cmd == "delete":
                if not args:
                    print("Usage: rm <file>")
                else:
                    kernel.delete(args[0])
            elif cmd == "change":
                if not args:
                    print("Usage: cd <path>")
                else:
                    kernel.cd(args[0])
            elif cmd == "current":
                print(kernel.pwd())
            elif cmd == "tree":
                kernel.tree()
            elif cmd == "fat":
                kernel.fat_status()
            elif cmd == "exit":
                sys.exit(0)
            else:
                print("Unknown command. Type 'help' for commands.")
        except Exception as e:
            print("Error:", e)

# If run as a script, start the shell
if __name__ == "__main__":
    run_shell()
