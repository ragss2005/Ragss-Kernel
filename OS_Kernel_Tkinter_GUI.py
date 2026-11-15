import sys, shlex, io, traceback, json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

# Try importing kernel
try:
    import os_kern
    KernelClass = os_kern.SimpleOSKernel
    HELP_TEXT = os_kern.HELP_TEXT
except Exception:
    KernelClass = None
    HELP_TEXT = "(help not available - failed to import os_kernel.py)"

class KernelGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raghu OS Simulator GUI")
        self.geometry("1200x650")
        self.configure(bg="#2b2b2b")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TButton", background="#444", foreground="white")
        self.style.configure("TLabel", background="#2b2b2b", foreground="white")
        self.style.configure("TEntry", fieldbackground="#3b3b3b", foreground="white")
        self.style.configure("TCombobox", fieldbackground="#3b3b3b", foreground="white")
        self.style.configure("Treeview", background="#1e1e1e", fieldbackground="#1e1e1e", foreground="white")
        self.style.map("Treeview", background=[('selected', '#555')], foreground=[('selected', 'white')])

        if KernelClass is None:
            lbl = tk.Label(self, text="Failed to import os_kernel.py.\nPlace this file with os_kernel.py.", fg="red", bg="#2b2b2b")
            lbl.pack(padx=10, pady=10)
            return

        self.kernel = KernelClass()
        self.history = []
        self.history_index = None
        self.dragging_item = None

        # Top frame: path and buttons
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=6, pady=6)
        self.path_var = tk.StringVar(value=self.kernel.pwd())
        ttk.Label(top, text="Current Path:").pack(side=tk.LEFT)
        self.path_label = ttk.Label(top, textvariable=self.path_var, relief=tk.SUNKEN, anchor=tk.W)
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4,10))
        ttk.Button(top, text="Help", command=self.show_help).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Tree", command=lambda:self.run_and_capture("tree")).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="FAT Map", command=self.show_fat_map).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="FAT", command=lambda:self.run_and_capture("fat")).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="Defrag", command=lambda:self.run_and_capture("defrag")).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="Export FS", command=self.export_fs).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="Import FS", command=self.import_fs).pack(side=tk.LEFT,padx=2)
        ttk.Button(top, text="Clear", command=self.clear_output).pack(side=tk.LEFT,padx=2)

        # Main frame with tree + output
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Left: Tree view
        self.tree_frame = ttk.Frame(main_frame)
        self.tree_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.pack(fill=tk.Y, expand=True)
        self.tree.heading("#0", text="File System", anchor=tk.W)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<ButtonPress-1>", self.on_tree_press)
        self.tree.bind("<B1-Motion>", self.on_tree_drag)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_release)
        self.populate_tree()

        # Right: Output console
        self.output = ScrolledText(main_frame, wrap=tk.WORD, height=25, bg="#1e1e1e", fg="white", font=("Consolas",10))
        self.output.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.output.insert(tk.END, "Raghu OS Simulation (GUI)\nType 'help' or use buttons.\n\n")
        self.output.configure(state=tk.DISABLED)

        # Bottom frame: input
        bot = ttk.Frame(self)
        bot.pack(fill=tk.X, padx=6, pady=6)
        self.cmd_var = tk.StringVar()
        self.cmd_entry = ttk.Entry(bot, textvariable=self.cmd_var)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6))
        self.cmd_entry.bind('<Return>', lambda e:self.on_run())
        self.cmd_entry.bind("<Up>", self.prev_history)
        self.cmd_entry.bind("<Down>", self.next_history)
        ttk.Button(bot, text="Run", command=self.on_run).pack(side=tk.LEFT)
        self.quick = ttk.Combobox(bot, values=["help","list","tree","fat","defrag","current"], state="readonly")
        self.quick.set("quick")
        self.quick.pack(side=tk.LEFT, padx=(6,0))
        self.quick.bind('<<ComboboxSelected>>', self.on_quick)

    # ---------- Core GUI Methods ----------
    def show_help(self):
        messagebox.showinfo("Help", HELP_TEXT)

    def clear_output(self):
        self.output.configure(state=tk.NORMAL)
        self.output.delete('1.0',tk.END)
        self.output.configure(state=tk.DISABLED)

    def append_output(self, text):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def on_quick(self,event=None):
        val = self.quick.get()
        if val != "quick":
            self.cmd_var.set(val)

    def on_run(self):
        cmdline = self.cmd_var.get().strip()
        if not cmdline: return
        self.append_output(f"> {cmdline}\n")
        self.history.append(cmdline)
        self.history_index = None
        try:
            self.run_and_capture(cmdline)
        except Exception as e:
            tb = traceback.format_exc()
            self.append_output(f"Exception:\n{tb}\n")
        self.path_var.set(self.kernel.pwd())
        self.cmd_var.set("")
        self.populate_tree()  # refresh tree after command

    def prev_history(self,event=None):
        if not self.history: return
        if self.history_index is None:
            self.history_index = len(self.history)-1
        else:
            self.history_index = max(0,self.history_index-1)
        self.cmd_var.set(self.history[self.history_index])

    def next_history(self,event=None):
        if not self.history: return
        if self.history_index is None: return
        self.history_index = min(len(self.history)-1,self.history_index+1)
        self.cmd_var.set(self.history[self.history_index])

    def run_and_capture(self, raw):
        try:
            tokens = shlex.split(raw)
        except ValueError as e:
            self.append_output(f"Parsing error: {e}\n"); return
        if not tokens: return
        cmd,*args = tokens
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            # replicate CLI behaviour
            if cmd == "help": print(HELP_TEXT)
            elif cmd == "list":
                path = args[0] if args else None
                items = self.kernel.ls(path)
                for it in items: print(it)
            elif cmd == "make":
                if not args: print("Usage: mkdir <path>")
                else: self.kernel.mkdir(args[0])
            elif cmd == "remove":
                if not args: print("Usage: rmdir <path>")
                else: self.kernel.rmdir(args[0])
            elif cmd == "create":
                if not args: print("Usage: create <file> [content]")
                else:
                    content = args[1] if len(args)>1 else ""
                    self.kernel.create(args[0],content)
            elif cmd == "write":
                if len(args)<2: print("Usage: write <file> <text>")
                else: self.kernel.write(args[0]," ".join(args[1:]))
            elif cmd == "append":
                if len(args)<2: print("Usage: append <file> <text>")
                else: self.kernel.append(args[0]," ".join(args[1:]))
            elif cmd == "print":
                if not args: print("Usage: print <file>")
                else: print(self.kernel.read(args[0]))
            elif cmd == "delete":
                if not args: print("Usage: delete <file>")
                else: self.kernel.delete(args[0])
            elif cmd == "change":
                if not args: print("Usage: change <path>")
                else: self.kernel.cd(args[0])
            elif cmd == "current": print(self.kernel.pwd())
            elif cmd == "tree": self.kernel.tree()
            elif cmd == "fat": self.kernel.fat_status()
            elif cmd == "defrag": self.kernel.defragment(); print("Defragmentation completed.")
            elif cmd == "exit": self.destroy()
            else: print("Unknown command. Type 'help' for commands.")
        finally:
            sys.stdout = old_stdout
        out = buf.getvalue()
        if out: self.append_output(out+"\n")

    # ---------- Tree Panel Methods ----------
    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        def add_node(parent, dir_obj):
            node_id = self.tree.insert(parent, "end", text=dir_obj.name, open=True)
            for d in dir_obj.children_dirs.values():
                add_node(node_id, d)
            for f in dir_obj.children_files:
                self.tree.insert(node_id,"end",text=f,open=True)
        add_node("", self.kernel.root)

    def on_tree_double_click(self,event):
        item_id = self.tree.focus()
        name = self.tree.item(item_id,"text")
        self.cmd_var.set(name)

    # ---------- Drag-and-Drop ----------
    def on_tree_press(self,event):
        item = self.tree.identify_row(event.y)
        if item:
            self.dragging_item = item

    def on_tree_drag(self,event):
        pass  # optional: visual feedback can be added

    def on_tree_release(self,event):
        if not self.dragging_item: return
        target_item = self.tree.identify_row(event.y)
        if not target_item or target_item==self.dragging_item: return
        source_name = self.tree.item(self.dragging_item,"text")
        target_name = self.tree.item(target_item,"text")
        try:
            self.kernel.move(source_name,target_name)  # assuming kernel has move(src,dst)
            self.append_output(f"Moved {source_name} to {target_name}\n")
            self.populate_tree()
        except Exception as e:
            self.append_output(f"Error moving {source_name} to {target_name}: {e}\n")
        finally:
            self.dragging_item = None

    # ---------- FAT Map ----------
    def show_fat_map(self):
        win = tk.Toplevel(self)
        win.title("FAT Block Map")
        canvas = tk.Canvas(win, width=650, height=300,bg="#1e1e1e")
        canvas.pack(fill=tk.BOTH, expand=True)
        fat_map = self.kernel.fat.status_map()
        block_w, block_h = 15, 15
        cols = 32
        for i,ch in enumerate(fat_map):
            x = (i%cols)*block_w + 5
            y = (i//cols)*block_h +5
            color = "#4CAF50" if ch=="." else "#FF9800"
            canvas.create_rectangle(x,y,x+block_w,y+block_h,fill=color,outline="#555")

    # ---------- Export / Import ----------
    def export_fs(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if not path: return
        try:
            def dir_to_dict(dir_obj):
                return {
                    "name": dir_obj.name,
                    "files": {f: self.kernel.read(f"{dir_obj.path()}/{f}") for f in dir_obj.children_files},
                    "dirs": {d: dir_to_dict(dir_obj.children_dirs[d]) for d in dir_obj.children_dirs}
                }
            data = dir_to_dict(self.kernel.root)
            with open(path,"w") as f: json.dump(data,f,indent=2)
            messagebox.showinfo("Export",f"Filesystem exported to {path}")
        except Exception as e:
            messagebox.showerror("Error",str(e))

    def import_fs(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path) as f: data = json.load(f)
            self.kernel = KernelClass()
            def load_dir(dir_obj,data_obj):
                for fname,content in data_obj.get("files",{}).items():
                    self.kernel.create(f"{dir_obj.path()}/{fname}",content)
                for dname,sub in data_obj.get("dirs",{}).items():
                    dir_new = dir_obj.add_dir(dname)
                    load_dir(dir_new,sub)
            load_dir(self.kernel.root,data)
            self.path_var.set(self.kernel.pwd())
            self.populate_tree()
            messagebox.showinfo("Import","Filesystem imported successfully.")
        except Exception as e:
            messagebox.showerror("Error",str(e))

if __name__=="__main__":
    app = KernelGUI()
    app.mainloop()
