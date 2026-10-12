"""Reports tab: list, filter, sort, preview, open, rename and delete generated reports."""
import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import reports
from md_preview import PreviewWindow
from ui_common import ACCENT, APP_TITLE, ERROR_FG, MUTED_FG, center, dark_title_bar

COLUMNS = [  # id, heading, width, stretch, sort key
    ("date", "Date", 120, False, lambda r: r.created),
    ("name", "Name", 230, True, lambda r: r.name.lower()),
    ("score", "Score", 60, False, lambda r: -1 if r.score is None else r.score),
    ("size", "Size", 70, False, lambda r: r.size),
]


class RenameDialog(tk.Toplevel):
    """Modal rename prompt with inline validation. self.result is the new name or None."""

    def __init__(self, parent: tk.Misc, path: Path):
        super().__init__(parent)
        self.title("Rename report")
        self.resizable(False, False)
        self.path = path
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="New name (.md is added automatically):").pack(anchor="w")
        self.var = tk.StringVar(value=path.stem)
        entry = ttk.Entry(frame, textvariable=self.var, width=50)
        entry.pack(fill="x", pady=(4, 2))
        entry.select_range(0, "end")
        entry.focus_set()
        self.error = ttk.Label(frame, text="", foreground=ERROR_FG)
        self.error.pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", pady=(8, 0))
        ttk.Button(buttons, text="Rename", style=ACCENT, command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent)
        self.grab_set()
        center(self)
        dark_title_bar(self)

    def _ok(self) -> None:
        name = self.var.get().strip()
        if name == self.path.stem:
            self.destroy()
            return
        if error := reports.validate_name(name, self.path):
            self.error.config(text=error)
            return
        self.result = name
        self.destroy()


class ReportsTab(ttk.Frame):
    def __init__(self, parent: tk.Misc, get_reports_dir, set_status, is_active):
        super().__init__(parent, padding=(0, 6, 0, 0))
        self.get_reports_dir = get_reports_dir
        self.set_status = set_status
        self.is_active = is_active  # status bar is shared; only write to it while shown
        self.reports: list[reports.Report] = []
        self.sort_col, self.sort_reverse = "date", True

        top = ttk.Frame(self)
        top.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Label(top, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._fill())
        ttk.Entry(top, textvariable=self.filter_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Refresh", command=self.reload).pack(side="right")

        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", padx=4, pady=(6, 4))
        self.single_buttons = []
        for text, cmd, style in [
            ("Preview", self.preview, ACCENT), ("Open", self.open_external, None),
            ("Show in folder", self.show_in_folder, None), ("Rename…", self.rename, None),
        ]:
            b = ttk.Button(bottom, text=text, command=cmd, **({"style": style} if style else {}))
            b.pack(side="left", padx=(0, 4))
            self.single_buttons.append(b)
        self.delete_btn = ttk.Button(bottom, text="Delete…", command=self.delete)
        self.delete_btn.pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=[c[0] for c in COLUMNS],
                                 show="headings", selectmode="extended")
        for col, text, width, stretch, _ in COLUMNS:
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, stretch=stretch)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.empty = ttk.Label(self.tree, foreground=MUTED_FG)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_buttons())
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Delete>", lambda e: self.delete())
        self.tree.bind("<Return>", lambda e: self.preview())
        self.tree.bind("<F2>", lambda e: self.rename())

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Preview", command=self.preview)
        self.menu.add_command(label="Open", command=self.open_external)
        self.menu.add_command(label="Show in folder", command=self.show_in_folder)
        self.menu.add_command(label="Rename…", command=self.rename)
        self.menu.add_separator()
        self.menu.add_command(label="Delete…", command=self.delete)
        self.update_buttons()

    # --- data ----------------------------------------------------------------

    def reload(self) -> None:
        self.reports = reports.list_reports(self.get_reports_dir())
        self._fill()

    def _visible(self) -> list[reports.Report]:
        needle = self.filter_var.get().strip().lower()
        items = [r for r in self.reports if needle in r.name.lower()]
        key = next(c[4] for c in COLUMNS if c[0] == self.sort_col)
        return sorted(items, key=key, reverse=self.sort_reverse)

    def _fill(self) -> None:
        selected = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        visible = self._visible()
        for r in visible:
            self.tree.insert("", "end", iid=str(r.path), values=(
                r.date_display, r.name, r.score_display, r.size_display))
        keep = [i for i in selected if self.tree.exists(i)]
        if keep:
            self.tree.selection_set(keep)
        for col, text, *_ in COLUMNS:
            arrow = (" ▼" if self.sort_reverse else " ▲") if col == self.sort_col else ""
            self.tree.heading(col, text=text + arrow)

        if not self.reports:
            self.empty.config(text="No reports yet. Analyze a session to create one.")
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        elif not visible:
            self.empty.config(text="No reports match the filter.")
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty.place_forget()
        self.update_buttons()

    def _sort_by(self, col: str) -> None:
        if col == self.sort_col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col, self.sort_reverse = col, col in ("date", "score", "size")
        self._fill()

    def summary(self) -> str:
        return f"{len(self.reports)} report(s) in {self.get_reports_dir()}"

    # --- selection -----------------------------------------------------------

    def _selected(self) -> list[Path]:
        return [Path(i) for i in self.tree.selection()]

    def _single(self) -> Path | None:
        sel = self._selected()
        return sel[0] if len(sel) == 1 else None

    def update_buttons(self) -> None:
        n = len(self.tree.selection())
        for b in self.single_buttons:
            b.state(["!disabled"] if n == 1 else ["disabled"])
        self.delete_btn.state(["!disabled"] if n else ["disabled"])
        for label in ("Preview", "Open", "Show in folder", "Rename…"):
            self.menu.entryconfigure(label, state="normal" if n == 1 else "disabled")
        self.menu.entryconfigure("Delete…", state="normal" if n else "disabled")
        if self.is_active():
            self.set_status(f"{n} report(s) selected." if n else self.summary())

    def _on_double_click(self, event) -> None:
        if self.tree.identify_row(event.y):
            self.preview()

    def _on_right_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        if row not in self.tree.selection():
            self.tree.selection_set(row)
        self.update_buttons()
        self.menu.tk_popup(event.x_root, event.y_root)

    # --- actions -------------------------------------------------------------

    def preview(self) -> None:
        if path := self._single():
            try:
                PreviewWindow(self.winfo_toplevel(), path)
            except OSError as e:
                messagebox.showerror(APP_TITLE, f"Could not read report:\n{e}")

    def open_external(self) -> None:
        if path := self._single():
            try:
                os.startfile(path)
            except OSError as e:
                messagebox.showerror(APP_TITLE, f"Could not open report:\n{e}")

    def show_in_folder(self) -> None:
        if path := self._single():
            subprocess.Popen(f'explorer /select,"{path}"')

    def rename(self) -> None:
        path = self._single()
        if not path:
            return
        dlg = RenameDialog(self.winfo_toplevel(), path)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        try:
            new_path = reports.rename_report(path, dlg.result)
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not rename report:\n{e}")
            return
        self.reload()
        self.tree.selection_set(str(new_path))
        self.tree.see(str(new_path))

    def delete(self) -> None:
        paths = self._selected()
        if not paths:
            return
        names = "\n".join(f"  • {p.name}" for p in paths[:10])
        if len(paths) > 10:
            names += f"\n  … and {len(paths) - 10} more"
        if not messagebox.askyesno(
            APP_TITLE,
            f"Permanently delete {len(paths)} report(s)?\n\n{names}",
            icon="warning", default="no", parent=self.winfo_toplevel(),
        ):
            return
        errors = reports.delete_reports(paths)
        self.reload()
        if errors:
            messagebox.showerror(APP_TITLE, "Some reports could not be deleted:\n\n" + "\n".join(errors))
        else:
            self.set_status(f"Deleted {len(paths)} report(s).")
