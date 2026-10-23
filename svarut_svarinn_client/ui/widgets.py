"""Small reusable widgets. No global mouse-wheel grabs or fixed-height forms."""
from __future__ import annotations

import tkinter as tk
from tkinter import font, ttk


class ScrollableForm(ttk.Frame):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0,
                                background=ttk.Style().lookup("TFrame", "background"))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.body = ttk.Frame(self.canvas, padding=16)
        self.body.columnconfigure(0, weight=1)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._body_changed)
        self.canvas.bind("<Configure>", self._canvas_changed)
        self._wrap_labels: list[ttk.Label] = []
        self._top = self.winfo_toplevel()
        self._bindings = []
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            binding = self._top.bind(sequence, self._wheel, add="+")
            self._bindings.append((sequence, binding))
        self.bind("<Destroy>", self._destroyed, add="+")

    def text(self, parent: tk.Misc, text: str, **options: object) -> ttk.Label:
        label = ttk.Label(parent, text=text, justify="left", wraplength=650, **options)
        self._wrap_labels.append(label)
        return label

    def _body_changed(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _canvas_changed(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        for label in self._wrap_labels:
            if label.winfo_exists():
                label.configure(wraplength=max(180, event.width - 60))

    def _contains(self, widget: tk.Misc | None) -> bool:
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(self, event: tk.Event) -> str | None:
        if not self.winfo_ismapped():
            return None
        widget = self.winfo_containing(event.x_root, event.y_root)
        if not self._contains(widget):
            return None
        if self.canvas.yview() == (0.0, 1.0):
            return None
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            delta = getattr(event, "delta", 0)
            step = -1 if delta > 0 else 1 if delta < 0 else 0
        self.canvas.yview_scroll(step * 3, "units")
        return "break"

    def show_widget(self, widget: tk.Misc) -> None:
        """Keep keyboard-focused input visible in a long setup form."""
        self.update_idletasks()
        top = widget.winfo_rooty() - self.body.winfo_rooty()
        height = max(1, self.body.winfo_height())
        first, last = self.canvas.yview()
        if top < first * height:
            self.canvas.yview_moveto(max(0, top - 12) / height)
        elif top + widget.winfo_height() > last * height:
            self.canvas.yview_moveto(max(0, top + widget.winfo_height() - self.canvas.winfo_height() + 12) / height)

    def _destroyed(self, event: tk.Event) -> None:
        if event.widget is self:
            for sequence, binding in self._bindings:
                try:
                    self._top.unbind(sequence, binding)
                except tk.TclError:
                    pass


def table(parent: tk.Misc, columns: tuple[tuple[str, str, int], ...], height: int = 8) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=tuple(c[0] for c in columns), show="headings", height=height)
    for key, label, width in columns:
        tree.heading(key, text=label, anchor="w")
        tree.column(key, width=width, minwidth=width, stretch=(key == columns[-1][0]), anchor="w")
    yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")
    return tree


def fit_columns(tree: ttk.Treeview) -> None:
    """All text must be reachable by horizontal scrolling, not clipped in cells."""
    metrics = font.nametofont("TkDefaultFont")
    for index, key in enumerate(tree["columns"]):
        labels = [str(tree.heading(key, "text"))]
        for item in tree.get_children():
            values = tree.item(item, "values")
            if index < len(values):
                labels.append(str(values[index]))
        width = max(metrics.measure(value) for value in labels) + 20
        width = max(85, width)
        tree.column(key, minwidth=width, width=width)
