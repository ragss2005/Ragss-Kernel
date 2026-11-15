"""
Tkinter GUI wrapper for the Simple OS Kernel Simulator (os_kernel.py)

Usage:
  1. Place this file in the same folder as your provided `os_kernel.py`.
  2. Run: python3 OS_Kernel_Tkinter_GUI.py

This GUI provides:
  - An output console (scrolled text) that shows kernel output
  - A command input entry to type the same commands as your CLI
  - Quick buttons for common actions (help, tree, fat, defrag, clear)
  - A "Run" button that executes the typed command
  - A label that shows current working directory

The GUI calls the same kernel methods used by your CLI; for kernel methods that print
internally (like tree() or fat_status()), the GUI temporarily redirects stdout and
captures printed text into the output console.
"""
import sys
import shlex
import io
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# Try importing the kernel file provided by the user
try:
    import os_kern
    KernelClass = os_kern.SimpleOSKernel
    HELP_TEXT = os_kern.HELP_TEXT
except Exception as e:
    KernelClass = None
    HELP_TEXT = """(help not available - failed to import os_kernel.py)"""


class SimpleOSKernel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raghu OS Simulator GUI")
        self.geometry("900x600")

        if KernelClass is None:
            lbl = tk.Label(self, text="Failed to import os_kernel.py.\nMake sure OS_Kernel_Tkinter_GUI.py is in the same folder as os_kernel.py and restart.", fg="red")
            lbl.pack(padx=10, pady=10)
            return

        self.kernel = KernelClass()

        # Top frame: path and buttons
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=6, pady=6)

        self.path_var = tk.StringVar(value=self.kernel.pwd())
        tk.Label(top, text="Current Path:").pack(side=tk.LEFT)
        self.path_label = tk.Label(top, textvariable=self.path_var, relief=tk.SUNKEN, anchor=tk.W)
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10))

        ttk.Button(top, text="Help", command=self.show_help).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Tree", command=lambda: self.run_and_capture("tree")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="FAT", command=lambda: self.run_and_capture("fat")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Defrag", command=lambda: self.run_and_capture("defrag")).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=2)

        # Middle frame: output console
        mid = ttk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.output = ScrolledText(mid, wrap=tk.WORD, height=25)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.insert(tk.END, "Raghu OS Simulation (GUI)\nType 'help' or use the buttons.\n\n")
        self.output.configure(state=tk.DISABLED)

        # Bottom frame: input and run
        bot = ttk.Frame(self)
        bot.pack(fill=tk.X, padx=6, pady=6)

        self.cmd_var = tk.StringVar()
        self.cmd_entry = ttk.Entry(bot, textvariable=self.cmd_var)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6))
        self.cmd_entry.bind('<Return>', lambda e: self.on_run())

        ttk.Button(bot, text="Run", command=self.on_run).pack(side=tk.LEFT)

        # Quick command dropdown
        self.quick = ttk.Combobox(bot, values=["help", "list", "tree", "fat", "defrag", "current"], state="readonly")
        self.quick.set("quick")
        self.quick.pack(side=tk.LEFT, padx=(6,0))
        self.quick.bind('<<ComboboxSelected>>', self.on_quick)

    def show_help(self):
        messagebox.showinfo("Help", HELP_TEXT)

    def clear_output(self):
        self.output.configure(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.configure(state=tk.DISABLED)

    def append_output(self, text: str):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def on_quick(self, event=None):
        val = self.quick.get()
        if val and val != "quick":
            self.cmd_var.set(val)

    def on_run(self):
        cmdline = self.cmd_var.get().strip()
        if not cmdline:
            return
        self.append_output(f"> {cmdline}\n")
        try:
            self.run_and_capture(cmdline)
        except Exception as e:
            tb = traceback.format_exc()
            self.append_output(f"Exception while running command:\n{tb}\n")
        self.path_var.set(self.kernel.pwd())
        self.cmd_var.set("")

    def run_and_capture(self, raw: str):
        # mimic the CLI's parsing & behaviour but route output to GUI
        try:
            tokens = shlex.split(raw)
        except ValueError as e:
            self.append_output(f"Parsing error: {e}\n")
            return
        if not tokens:
            return
        cmd, *args = tokens

        # Some kernel methods print directly; capture stdout for the call
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            # Map commands similarly to CLI
            if cmd == "help":
                print(HELP_TEXT)
            elif cmd == "list":
                path = args[0] if args else None
                items = self.kernel.ls(path)
                for it in items:
                    print(it)
            elif cmd == "make":
                if not args:
                    print("Usage: mkdir <path>")
                else:
                    self.kernel.mkdir(args[0])
            elif cmd == "remove":
                if not args:
                    print("Usage: rmdir <path>")
                else:
                    self.kernel.rmdir(args[0])
            elif cmd == "create":
                if not args:
                    print("Usage: create <file> [content]")
                else:
                    content = args[1] if len(args) > 1 else ""
                    self.kernel.create(args[0], content)
            elif cmd == "write":
                if len(args) < 2:
                    print("Usage: write <file> <text>")
                else:
                    path = args[0]
                    text = " ".join(args[1:])
                    self.kernel.write(path, text)
            elif cmd == "append":
                if len(args) < 2:
                    print("Usage: append <file> <text>")
                else:
                    path = args[0]
                    text = " ".join(args[1:])
                    self.kernel.append(path, text)
            elif cmd == "print":
                if not args:
                    print("Usage: print <file>")
                else:
                    print(self.kernel.read(args[0]))
            elif cmd == "delete":
                if not args:
                    print("Usage: delete <file>")
                else:
                    self.kernel.delete(args[0])
            elif cmd == "change":
                if not args:
                    print("Usage: change <path>")
                else:
                    self.kernel.cd(args[0])
            elif cmd == "current":
                print(self.kernel.pwd())
            elif cmd == "tree":
                self.kernel.tree()
            elif cmd == "fat":
                self.kernel.fat_status()
            elif cmd == "defrag":
                self.kernel.defragment()
                print("Defragmentation completed.")
            elif cmd == "exit":
                self.destroy()
            else:
                print("Unknown command. Type 'help' for commands.")
        except Exception as e:
            print("Error:", e)
        finally:
            sys.stdout = old_stdout
        out = buf.getvalue()
        if out:
            self.append_output(out + "\n")


if __name__ == "__main__":
    app = SimpleOSKernel()
    app.mainloop()
