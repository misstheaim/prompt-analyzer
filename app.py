"""Prompt Analyzer: pick Claude Code sessions and get a review of your prompts."""
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cleanup
import config
from analyzer import AnalysisError, run_analysis
from reports_tab import ReportsTab
from sessions import DEFAULT_RETENTION_DAYS, list_sessions, retention_days
from skill_installer import TARGET as SKILL_TARGET, install_skill, skill_installed
from ui_common import (
    ACCENT, APP_TITLE, ERROR_FG, MUTED_FG, apply_theme, center, dark_title_bar,
    enable_dpi_awareness, scaled,
)

EXPIRING_SOON_DAYS = 7
REPORTS_TAB, SETTINGS_TAB = 2, 3
FIELDS = [
    ("sessions_dir", "Claude sessions folder", "dir", ""),
    ("reports_base", "Reports location", "dir", "A 'reports' subfolder will be created here."),
    ("claude_path", "claude.exe", "file", ""),
]


class SettingsForm(ttk.Frame):
    """Path fields + skill status. Used by the first-run dialog and the Settings tab."""

    def __init__(self, parent: tk.Misc, cfg: dict, on_skill_change=None):
        super().__init__(parent)
        self.on_skill_change = on_skill_change
        self.columnconfigure(1, weight=1)
        self.vars: dict[str, tk.StringVar] = {}
        self.notes: dict[str, ttk.Label] = {}
        self.hints = {key: hint for key, _, _, hint in FIELDS}

        row = 0
        for key, label, kind, hint in FIELDS:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
            var = tk.StringVar(value=cfg.get(key, ""))
            self.vars[key] = var
            ttk.Entry(self, textvariable=var, width=45).grid(row=row, column=1, sticky="ew")
            ttk.Button(self, text="Browse…", command=lambda k=key, t=kind: self._browse(k, t)).grid(
                row=row, column=2, padx=(6, 0))
            # One line under each field: gray hint, replaced by a red error when invalid.
            note = ttk.Label(self, text=hint, foreground=MUTED_FG)
            note.grid(row=row + 1, column=1, columnspan=2, sticky="w", pady=(0, 4))
            self.notes[key] = note
            row += 2

        skill_row = ttk.Frame(self)
        skill_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self.skill_label = ttk.Label(skill_row)
        self.skill_label.pack(side="left")
        self.skill_btn = ttk.Button(skill_row, text="Install skill", command=self._install_skill)
        self.skill_btn.pack(side="right")
        self.refresh_skill_status()

    def set_values(self, values: dict) -> None:
        for key, var in self.vars.items():
            var.set(values.get(key, ""))
        self._show_errors({})

    def _browse(self, key: str, kind: str) -> None:
        current = self.vars[key].get()
        if kind == "dir":
            path = filedialog.askdirectory(parent=self, initialdir=current or None)
        else:
            path = filedialog.askopenfilename(
                parent=self, initialdir=os.path.dirname(current) or None,
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.vars[key].set(os.path.normpath(path))

    def refresh_skill_status(self) -> None:
        if skill_installed():
            self.skill_label.config(text="prompt-review skill: installed", foreground="")
            self.skill_btn.state(["disabled"])
        else:
            self.skill_label.config(text="prompt-review skill: not installed (required for Analyze)",
                                    foreground=ERROR_FG)
            self.skill_btn.state(["!disabled"])

    def _install_skill(self) -> None:
        try:
            install_skill()
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not install skill:\n{e}", parent=self)
        self.refresh_skill_status()
        if self.on_skill_change:
            self.on_skill_change()

    def _show_errors(self, errors: dict) -> None:
        for key, note in self.notes.items():
            if key in errors:
                note.config(text=errors[key], foreground=ERROR_FG)
            else:
                note.config(text=self.hints[key], foreground=MUTED_FG)

    def apply(self, cfg: dict) -> bool:
        """Validate, then save the field values into cfg. Returns False if invalid."""
        values = {k: v.get().strip() for k, v in self.vars.items()}
        errors = config.validate(values)
        self._show_errors(errors)
        if errors:
            return False
        updated = {**cfg, **values}
        try:
            config.ensure_reports_dir(updated)
            config.save(updated)
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not save settings:\n{e}", parent=self)
            return False
        cfg.update(values)
        return True


class SettingsDialog(tk.Toplevel):
    """First-run modal. self.result is the saved cfg, or None if the user exits."""

    def __init__(self, parent: tk.Misc, cfg: dict):
        super().__init__(parent)
        self.title("Welcome — confirm settings")
        self.resizable(True, False)
        self.cfg = cfg
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Check the default locations below and change them if needed.").pack(
            anchor="w", pady=(0, 8))
        self.form = SettingsForm(frame, cfg)
        self.form.pack(fill="x")
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", pady=(10, 0))
        ttk.Button(buttons, text="OK", style=ACCENT, command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Exit", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        # A transient of a withdrawn root stays hidden on Windows (first run).
        if parent.winfo_viewable():
            self.transient(parent)
        self.grab_set()
        center(self)
        dark_title_bar(self)

    def _ok(self) -> None:
        if self.form.apply(self.cfg):
            self.result = self.cfg
            self.destroy()


class DeleteDataDialog(tk.Toplevel):
    """Confirmation for wiping app data. self.confirmed is True if the user clicked Delete."""

    def __init__(self, parent: tk.Misc, cfg: dict):
        super().__init__(parent)
        self.title("Delete all app data")
        self.resizable(False, False)
        self.confirmed = False
        skill_dir, config_dir = cleanup.app_data_dirs()

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        lines = [
            "This will permanently delete:",
            f"  • prompt-review skill: {skill_dir if skill_dir.exists() else '(not installed)'}",
            f"  • app settings and favorites: {config_dir if config_dir.exists() else '(none saved)'}",
            "",
            f"Your reports in {config.reports_dir(cfg)} are kept.",
            "Claude Code's own settings (e.g. session retention) and your",
            "sessions are not touched. The app will close afterwards.",
        ]
        ttk.Label(frame, text="\n".join(lines), justify="left",
                  wraplength=scaled(self, 520)).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", pady=(12, 0))
        ttk.Button(buttons, text="Delete", command=self._confirm).pack(side="left", padx=4)
        cancel = ttk.Button(buttons, text="Cancel", command=self.destroy)
        cancel.pack(side="left")
        cancel.focus_set()  # safe default

        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent)
        self.grab_set()
        center(self)
        dark_title_bar(self)

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cfg = config.load()
        self.sessions = []
        self.retention = DEFAULT_RETENTION_DAYS
        self.results: queue.Queue = queue.Queue()
        self.busy = False
        self.status = tk.StringVar()

        root.title(APP_TITLE)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        min_w, min_h = scaled(root, 560), scaled(root, 420)
        w, h = max(min_w, int(sw * 0.3)), max(min_h, int(sh * 0.3))
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        root.minsize(min_w, min_h)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.all_tree = self._make_tree("All sessions")
        self.fav_tree = self._make_tree("Favorites")
        self.reports_tab = ReportsTab(
            self.notebook, lambda: config.reports_dir(self.cfg), self.status_set,
            lambda: self.notebook.index("current") == REPORTS_TAB)
        self.notebook.add(self.reports_tab, text="Reports")
        self._make_settings_tab()
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())

        self.bar = ttk.Frame(root)
        self.bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(self.bar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(self.bar, text="☆ Toggle favorite", command=self.toggle_favorite).pack(
            side="left", padx=4)
        self.analyze_btn = ttk.Button(self.bar, text="Analyze", style=ACCENT, command=self.analyze)
        self.analyze_btn.pack(side="right")

        ttk.Label(root, textvariable=self.status, anchor="w", foreground=MUTED_FG).pack(
            fill="x", padx=8, pady=(0, 6))

    def status_set(self, text: str) -> None:
        self.status.set(text)

    def _make_tree(self, title: str) -> ttk.Treeview:
        frame = ttk.Frame(self.notebook)
        tree = ttk.Treeview(frame, columns=("fav", "title", "project", "date", "expires"),
                            show="headings", selectmode="extended")
        for col, text, width, stretch in [
            ("fav", "★", 30, False), ("title", "Session", 200, True),
            ("project", "Project", 100, True), ("date", "Last activity", 115, False),
            ("expires", "Expires in", 75, False),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, stretch=stretch, anchor="center" if col == "fav" else "w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        tree.tag_configure("expiring", foreground=ERROR_FG)
        tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons())
        tree.bind("<Double-1>", lambda e, t=tree: self._on_double_click(e, t))
        self.notebook.add(frame, text=title)
        return tree

    def _make_settings_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=10)
        self.settings_form = SettingsForm(tab, self.cfg, on_skill_change=self._update_buttons)
        self.settings_form.pack(fill="x")

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Save", style=ACCENT, command=self.save_settings).pack(side="right")
        ttk.Button(buttons, text="Restore defaults", command=self._restore_defaults).pack(
            side="right", padx=6)

        ttk.Separator(tab).pack(fill="x", pady=10)
        danger = ttk.Frame(tab)
        danger.pack(fill="x")
        ttk.Label(danger, text="Remove the skill, settings and favorites from this computer.",
                  foreground=MUTED_FG).pack(side="left")
        ttk.Button(danger, text="Delete all app data…", command=self.delete_app_data).pack(
            side="right")
        self.notebook.add(tab, text="Settings")

    # --- startup -------------------------------------------------------------

    def first_run_checks(self) -> bool:
        """Settings + skill setup. Returns False if the user chose to exit."""
        if not config.exists():
            dlg = SettingsDialog(self.root, self.cfg)
            self.root.wait_window(dlg)
            if dlg.result is None:
                return False
            self.settings_form.set_values(self.cfg)
        if not skill_installed() and not self.cfg.get("skill_prompt_answered"):
            if messagebox.askyesno(
                APP_TITLE,
                "Prompt Analyzer needs the 'prompt-review' skill to run analyses.\n\n"
                f"Install it to:\n{SKILL_TARGET}\n\n"
                "It has no description, so it won't add anything to Claude's context "
                "in your normal sessions; it only runs when this app calls /prompt-review.",
            ):
                try:
                    install_skill()
                except OSError as e:
                    messagebox.showerror(APP_TITLE, f"Could not install skill:\n{e}")
            self.cfg["skill_prompt_answered"] = True
            config.save(self.cfg)
            self.settings_form.refresh_skill_status()
        return True

    # --- session list --------------------------------------------------------

    def refresh(self) -> None:
        errors = config.validate(self.cfg)
        if "sessions_dir" in errors:
            self.sessions = []
        else:
            self.sessions = list_sessions(self.cfg["sessions_dir"])
        self.retention = retention_days(Path(self.cfg["sessions_dir"]).parent)
        self._fill_trees()
        self.reports_tab.reload()
        self._update_buttons()

    def _fill_trees(self) -> None:
        favs = set(self.cfg["favorites"])
        for tree in (self.all_tree, self.fav_tree):
            selected = set(tree.selection())
            tree.delete(*tree.get_children())
            for s in self.sessions:
                if tree is self.fav_tree and s.id not in favs:
                    continue
                days = s.days_left(self.retention)
                tree.insert("", "end", iid=s.id, values=(
                    "★" if s.id in favs else "", s.title, s.project, s.date_display,
                    f"{days} day{'' if days == 1 else 's'}",
                ), tags=("expiring",) if days <= EXPIRING_SOON_DAYS else ())
            keep = [i for i in selected if tree.exists(i)]
            if keep:
                tree.selection_set(keep)

    def _active_tree(self) -> ttk.Treeview | None:
        return {0: self.all_tree, 1: self.fav_tree}.get(self.notebook.index("current"))

    def _on_tab_changed(self) -> None:
        # The session buttons only apply to the two session tabs.
        if self.notebook.index("current") in (REPORTS_TAB, SETTINGS_TAB):
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(fill="x", padx=8, pady=(0, 4), before=self.root.pack_slaves()[-1])
        self._update_buttons()

    def _on_double_click(self, event, tree: ttk.Treeview) -> None:
        if tree.identify_column(event.x) == "#1" and (item := tree.identify_row(event.y)):
            self._toggle([item])

    def toggle_favorite(self) -> None:
        if tree := self._active_tree():
            self._toggle(list(tree.selection()))

    def _toggle(self, ids: list[str]) -> None:
        if not ids:
            return
        favs = list(self.cfg["favorites"])
        for sid in ids:
            if sid in favs:
                favs.remove(sid)
            else:
                favs.append(sid)
        self.cfg["favorites"] = favs
        config.save(self.cfg)
        self._fill_trees()
        self._update_buttons()

    # --- settings ------------------------------------------------------------

    def save_settings(self) -> None:
        if self.settings_form.apply(self.cfg):
            self.refresh()
            self.status.set("Settings saved.")

    def _restore_defaults(self) -> None:
        self.settings_form.set_values(config.defaults())
        self.status.set("Defaults restored in the form. Click Save to apply.")

    def delete_app_data(self) -> None:
        if self.busy:
            messagebox.showinfo(APP_TITLE, "Wait for the running analysis to finish first.")
            return
        dlg = DeleteDataDialog(self.root, self.cfg)
        self.root.wait_window(dlg)
        if not dlg.confirmed:
            return
        errors = cleanup.delete_app_data()
        if errors:
            messagebox.showerror(APP_TITLE, "Some items could not be deleted:\n\n" + "\n".join(errors))
        else:
            messagebox.showinfo(APP_TITLE, "All Prompt Analyzer data was deleted. The app will now close.")
        self.root.destroy()

    # --- analysis ------------------------------------------------------------

    def _update_buttons(self) -> None:
        if self.busy:
            return
        tree = self._active_tree()
        if tree is None:
            if self.notebook.index("current") == REPORTS_TAB:
                self.reports_tab.update_buttons()  # shows the report count / selection
            else:
                self.status.set("")
            return
        problem = None
        errors = config.validate(self.cfg)
        if errors:
            problem = "Check the Settings tab: " + "; ".join(errors.values())
        elif not skill_installed():
            problem = "prompt-review skill is not installed. Install it on the Settings tab."
        selected = tree.selection()
        if problem:
            self.status.set(problem)
        elif selected:
            self.status.set(f"{len(selected)} session(s) selected.")
        else:
            self.status.set(f"{len(self.sessions)} sessions (kept {self.retention} days after last "
                            "activity). Select one or more and click Analyze.")
        self.analyze_btn.state(["!disabled"] if selected and not problem else ["disabled"])

    def analyze(self) -> None:
        tree = self._active_tree()
        ids = set(tree.selection()) if tree else set()
        chosen = [s for s in self.sessions if s.id in ids]
        if not chosen:
            return
        self.busy = True
        self.analyze_btn.state(["disabled"])
        self.status.set(f"Analyzing {len(chosen)} session(s)… this can take a few minutes.")
        cfg = dict(self.cfg)

        def work():
            try:
                self.results.put(("ok", run_analysis(chosen, cfg)))
            except AnalysisError as e:
                self.results.put(("error", str(e)))
            except Exception as e:  # keep the UI alive on unexpected failures
                self.results.put(("error", repr(e)))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(500, self._poll)

    def _poll(self) -> None:
        try:
            kind, value = self.results.get_nowait()
        except queue.Empty:
            self.root.after(500, self._poll)
            return
        self.busy = False
        self._update_buttons()
        if kind == "ok":
            self.reports_tab.reload()
            self.status.set(f"Report saved: {value}")
            os.startfile(value)
        else:
            self.status.set("Analysis failed.")
            messagebox.showerror(APP_TITLE, value)


def main() -> None:
    enable_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    apply_theme(root)
    dark_title_bar(root)
    app = App(root)
    if not app.first_run_checks():
        root.destroy()
        return
    root.deiconify()
    app.refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
