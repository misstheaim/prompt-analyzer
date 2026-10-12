"""Read-only Markdown preview window: a tk.Text widget plus a tiny Markdown-to-tags renderer.

Supports the subset our /prompt-review reports use: headings, **bold**, *italic*,
`code`, [links](url), bullet/numbered lists, > quotes, ``` code blocks and --- rules.
"""
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from ui_common import (
    APP_TITLE, BG, CODE_BG, FG, LINK_FG, MUTED_FG, dark_title_bar, scaled,
)

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
QUOTE = re.compile(r"^\s*>\s?(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")
# Order matters: code first (its content is literal), then bold before italic.
INLINE = re.compile(
    r"(`[^`]+`)"                       # `code`
    r"|(\*\*[^*]+\*\*|(?<!\w)__[^_]+__(?!\w))"  # **bold**
    # *italic*; underscores only at word boundaries so snake_case names stay intact
    r"|(\*[^*\s][^*]*\*|(?<!\w)_[^_\s][^_]*_(?!\w))"
    r"|(\[[^\]]+\]\([^)]+\))"          # [text](url)
)


def _configure_tags(text: tk.Text) -> None:
    base = tkfont.nametofont("TkDefaultFont").actual()
    family, size = base["family"], abs(base["size"]) or 10
    mono = "Consolas"
    text.configure(font=(family, size))
    text.tag_configure("h1", font=(family, size + 8, "bold"), spacing1=12, spacing3=6)
    text.tag_configure("h2", font=(family, size + 5, "bold"), spacing1=12, spacing3=4)
    text.tag_configure("h3", font=(family, size + 2, "bold"), spacing1=8, spacing3=2)
    text.tag_configure("bold", font=(family, size, "bold"))
    text.tag_configure("italic", font=(family, size, "italic"))
    text.tag_configure("code", font=(mono, size), background=CODE_BG)
    text.tag_configure("codeblock", font=(mono, size), background=CODE_BG,
                       lmargin1=12, lmargin2=12, rmargin=12)
    text.tag_configure("link", foreground=LINK_FG, underline=True)
    text.tag_configure("quote", foreground=MUTED_FG, lmargin1=18, lmargin2=18)
    text.tag_configure("rule", foreground=MUTED_FG, justify="center")
    for level in range(6):
        indent = 14 + level * 20
        text.tag_configure(f"li{level}", lmargin1=indent, lmargin2=indent + 14, spacing1=1)


def _insert_inline(text: tk.Text, line: str, base_tags: tuple) -> None:
    pos = 0
    for m in INLINE.finditer(line):
        if m.start() > pos:
            text.insert("end", line[pos:m.start()], base_tags)
        token = m.group(0)
        if m.group(1):
            text.insert("end", token[1:-1], base_tags + ("code",))
        elif m.group(2):
            text.insert("end", token[2:-2], base_tags + ("bold",))
        elif m.group(3):
            text.insert("end", token[1:-1], base_tags + ("italic",))
        else:
            label = token[1:token.index("]")]
            text.insert("end", label, base_tags + ("link",))
        pos = m.end()
    text.insert("end", line[pos:] + "\n", base_tags)


def render_markdown(text: tk.Text, md: str) -> None:
    """Replace the widget's contents with md rendered via text tags."""
    _configure_tags(text)
    text.configure(state="normal")
    text.delete("1.0", "end")
    in_code = False
    for line in md.splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            text.insert("end", line + "\n", ("codeblock",))
        elif m := HEADING.match(line):
            level = min(len(m[1]), 3)
            # Inline markers are stripped in headings so the heading font isn't overridden.
            title = re.sub(r"(\*\*|__|`)", "", m[2])
            text.insert("end", title + "\n", (f"h{level}",))
        elif RULE.match(line):
            text.insert("end", "─" * 40 + "\n", ("rule",))
        elif m := QUOTE.match(line):
            _insert_inline(text, m[1], ("quote",))
        elif m := LIST_ITEM.match(line):
            level = min(len(m[1].expandtabs(4)) // 2, 5)
            marker = "•" if m[2] in "-*+" else m[2]
            text.insert("end", f"{marker} ", (f"li{level}",))
            _insert_inline(text, m[3], (f"li{level}",))
        else:
            _insert_inline(text, line, ())
    text.configure(state="disabled")


class PreviewWindow(tk.Toplevel):
    """Non-modal window showing one report. Several can be open at once."""

    def __init__(self, parent: tk.Misc, path: Path):
        super().__init__(parent)
        self.path = path
        self.title(f"{path.stem} — {APP_TITLE}")
        self.configure(background=BG)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = max(scaled(self, 600), sw // 2), max(scaled(self, 450), sh // 2)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(scaled(self, 400), scaled(self, 300))

        bar = ttk.Frame(self, padding=(8, 8, 8, 0))
        bar.pack(fill="x")
        ttk.Label(bar, text=str(path), foreground=MUTED_FG).pack(side="left")
        ttk.Button(bar, text="Open externally", command=self._open_external).pack(side="right")
        ttk.Button(bar, text="Copy", command=self._copy).pack(side="right", padx=6)

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        self.text = tk.Text(
            body, wrap="word", background=BG, foreground=FG, insertbackground=FG,
            selectbackground="#2f60d8", borderwidth=0, highlightthickness=0,
            padx=scaled(self, 12), pady=scaled(self, 8),
        )
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        self.raw = path.read_text(encoding="utf-8", errors="replace")
        render_markdown(self.text, self.raw)
        self.bind("<Escape>", lambda e: self.destroy())
        dark_title_bar(self)

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.raw)

    def _open_external(self) -> None:
        try:
            os.startfile(self.path)
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not open report:\n{e}", parent=self)
