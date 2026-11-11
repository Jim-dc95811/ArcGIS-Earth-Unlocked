"""P25 alias editor - names the P25 unit IDs for the PRAVE / ME Tracker 3.0 map.

Edits p25_aliases.json in this folder (unit ID -> friendly name, e.g.
9076801 -> "Jax 24"). The running tracker watches this file and relabels the
map within a moment of a save - you do not need to stop the tracker to rename.

Standard Python 3 with Tk only; nothing else required.
"""
import json
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

ALIAS_FILE = Path(__file__).resolve().parent / "p25_aliases.json"


def load_aliases():
    try:
        if ALIAS_FILE.is_file():
            data = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_aliases(d):
    ALIAS_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")


class AliasDialog(tk.Toplevel):
    def __init__(self, parent, title, unit="", alias="", lock_unit=False):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        frm = ttk.Frame(self, padding=14)
        frm.grid()
        ttk.Label(frm, text="Unit ID (P25):").grid(row=0, column=0, sticky="w", pady=4)
        self.u = ttk.Entry(frm, width=24)
        self.u.grid(row=0, column=1, pady=4)
        self.u.insert(0, unit)
        if lock_unit:
            self.u.configure(state="disabled")
        ttk.Label(frm, text="Alias (shown on map):").grid(row=1, column=0, sticky="w", pady=4)
        self.a = ttk.Entry(frm, width=24)
        self.a.grid(row=1, column=1, pady=4)
        self.a.insert(0, alias)
        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Save", command=self._ok).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=5)
        (self.a if lock_unit else self.u).focus_set()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        unit = self.u.get().strip()
        if not unit:
            messagebox.showwarning("Missing", "Enter a Unit ID.", parent=self)
            return
        self.result = (unit, self.a.get().strip())
        self.destroy()


class Editor:
    def __init__(self, root):
        self.root = root
        root.title("P25 Aliases - PRAVE / ME Tracker")
        root.geometry("460x420")
        root.minsize(380, 300)
        self.aliases = load_aliases()

        top = ttk.Frame(root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Name your P25 field radios. Saved changes relabel the map live.",
                  wraplength=430).pack(anchor="w")

        mid = ttk.Frame(root, padding=(12, 4))
        mid.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(mid, columns=("unit", "alias"), show="headings", height=12)
        self.tree.heading("unit", text="Unit ID")
        self.tree.heading("alias", text="Alias")
        self.tree.column("unit", width=150, anchor="w")
        self.tree.column("alias", width=250, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self.edit())

        btns = ttk.Frame(root, padding=(12, 8))
        btns.pack(fill="x")
        ttk.Button(btns, text="Add", command=self.add).pack(side="left")
        ttk.Button(btns, text="Edit", command=self.edit).pack(side="left", padx=6)
        ttk.Button(btns, text="Remove", command=self.remove).pack(side="left")
        ttk.Button(btns, text="Reload file", command=self.reload).pack(side="right")

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for unit, alias in sorted(self.aliases.items()):
            self.tree.insert("", "end", values=(unit, alias))

    def selected(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0], "values")[0] if sel else None

    def _commit(self, unit, alias):
        if alias:
            self.aliases[unit] = alias
        else:
            self.aliases.pop(unit, None)
        try:
            save_aliases(self.aliases)
        except Exception as exc:
            messagebox.showerror("Could not save", str(exc), parent=self.root)
        self.refresh()

    def add(self):
        dlg = AliasDialog(self.root, "Add / name a unit")
        self.root.wait_window(dlg)
        if dlg.result:
            self._commit(*dlg.result)

    def edit(self):
        unit = self.selected()
        if not unit:
            messagebox.showinfo("Pick a unit", "Select a row first.", parent=self.root)
            return
        dlg = AliasDialog(self.root, "Edit alias", unit=unit,
                          alias=self.aliases.get(unit, ""), lock_unit=True)
        self.root.wait_window(dlg)
        if dlg.result:
            self._commit(unit, dlg.result[1])

    def remove(self):
        unit = self.selected()
        if unit:
            self._commit(unit, "")

    def reload(self):
        self.aliases = load_aliases()
        self.refresh()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    Editor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
