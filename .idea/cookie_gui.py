import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pathlib import Path
import json
import sv_ttk
import darkdetect

class CookieCostApp(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            if hasattr(sv_ttk, "set_theme"):
                sv_ttk.set_theme(darkdetect.theme())

        except Exception:
            pass
        self.title("Cookie Cost Calculator")
        self.geometry("900x560")
        self.minsize(900, 560)

        # ----- State -----
        self.df = pd.DataFrame(columns=["name", "unit_cost", "quantity_used", "total_cost"])
        # defaults (you can change in the GUI)
        self.cookie_yield = tk.DoubleVar(master=self, value=50.0)
        self.cookie_price = tk.DoubleVar(master=self, value=0.50)
        self._edit_entry = None
        self._editing_info = None  # tuple: (item_id, column_id)
        # ---- Config file path ----
        self._config_path = Path.home() / ".cookie_cost_gui.json"


        # ---- Load config & vars ----
        cfg = self._load_config()
        self.ask_before_delete = tk.BooleanVar(master=self, value=cfg.get("ask_before_delete", True))

        # (keep your other vars here, e.g., cookie_yield, cookie_price, etc.)

        # Save config on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Also auto-save when the checkbox is toggled
        self.ask_before_delete.trace_add("write", lambda *_: self._save_config())

        # ----- Layout -----
        self._build_header()
        self._build_table()
        self._build_editor()
        self._build_summary()
        self._build_actions()

        # Seed data (optional; comment out if you want a blank start)
        self._seed_rows()

        self._recalculate_and_refresh()

    # ------------------------- UI Builders -------------------------
    def _build_header(self):
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")

        # Yield & Price controls
        ttk.Label(bar, text="Cookies per batch:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.yield_entry = ttk.Entry(bar, textvariable=self.cookie_yield, width=10)
        self.yield_entry.grid(row=0, column=1, sticky="w", padx=(0, 16))

        ttk.Label(bar, text="Price per cookie ($):").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.price_entry = ttk.Entry(bar, textvariable=self.cookie_price, width=10)
        self.price_entry.grid(row=0, column=3, sticky="w", padx=(0, 16))

        apply_button = (ttk.Button(bar, text="Apply", command=self._recalculate_and_refresh))
        apply_button.grid(row=0, column=4, sticky="w")

        # Quick usability: Enter key applies
        self.yield_entry.bind("<Return>", lambda e: self._recalculate_and_refresh())
        self.price_entry.bind("<Return>", lambda e: self._recalculate_and_refresh())

        # Make spacing responsive
        bar.columnconfigure(5, weight=1)

    def _build_table(self):
        wrapper = ttk.Frame(self, padding=(10, 0))
        wrapper.pack(fill="both", expand=True)

        cols = ("name", "unit_cost", "quantity_used", "total_cost")
        self.tree = ttk.Treeview(wrapper, columns=cols, show="headings", height=10)
        self.tree.heading("name", text="Ingredient")
        self.tree.heading("unit_cost", text="Unit Cost ($)")
        self.tree.heading("quantity_used", text="Qty Used")
        self.tree.heading("total_cost", text="Total Cost ($)")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("unit_cost", width=120, anchor="e")
        self.tree.column("quantity_used", width=100, anchor="e")
        self.tree.column("total_cost", width=120, anchor="e")

        vsb = ttk.Scrollbar(wrapper, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_row)
        self.tree.bind("<Button-1>", self._clear_if_empty_click, add="+")
        self.tree.bind("<ButtonRelease-1>", self._clear_if_empty_click, add="+")
        self.tree.bind("<Escape>", lambda e: (self.tree.selection_remove(self.tree.selection()),
                                              self.tree.focus(""),
                                              self._clear_editor()))
        self.tree.bind("<Delete>", lambda e: self._delete_selected())
        self.tree.bind("<Double-1>", self._begin_cell_edit, add="+")

        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)

    def _build_editor(self):
        editor = ttk.Labelframe(self, text="Ingredient Editor", padding=(10, 10))
        editor.pack(fill="x", padx=10, pady=(6, 0))

        self.name_var = tk.StringVar(master=self)
        self.unit_cost_var = tk.StringVar(master=self)
        self.qty_var = tk.StringVar(master=self)

        ttk.Label(editor, text="Ingredient name").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.name_var, width=24).grid(row=1, column=0, sticky="we", padx=(0, 12))

        ttk.Label(editor, text="Unit cost ($ / unit)").grid(row=0, column=1, sticky="w")
        ttk.Entry(editor, textvariable=self.unit_cost_var, width=16).grid(row=1, column=1, sticky="we", padx=(0, 12))

        ttk.Label(editor, text="Quantity used").grid(row=0, column=2, sticky="w")
        ttk.Entry(editor, textvariable=self.qty_var, width=16).grid(row=1, column=2, sticky="we", padx=(0, 12))

        ttk.Button(editor, text="Add / Update", command=self._add_or_update_row).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(editor, text="Delete Selected", command=self._delete_selected).grid(row=1, column=4)


        for c in range(5):
            editor.columnconfigure(c, weight=1)

    def _build_summary(self):
        self.summary = ttk.Frame(self, padding=(10, 8))
        self.summary.pack(fill="x")

        self.total_cost_lbl = ttk.Label(self.summary, text="Total cost: $0.00", font=("Segoe UI", 10, "bold"))
        self.revenue_lbl = ttk.Label(self.summary, text="Revenue: $0.00", font=("Segoe UI", 10, "bold"))
        self.profit_lbl = ttk.Label(self.summary, text="Profit: $0.00", font=("Segoe UI", 10, "bold"))
        self.ppc_lbl = ttk.Label(self.summary, text="Profit per cookie: $0.00", font=("Segoe UI", 10, "bold"))

        self.total_cost_lbl.grid(row=0, column=0, sticky="w", padx=(0, 18))
        self.revenue_lbl.grid(row=0, column=1, sticky="w", padx=(0, 18))
        self.profit_lbl.grid(row=0, column=2, sticky="w", padx=(0, 18))
        self.ppc_lbl.grid(row=0, column=3, sticky="w", padx=(0, 18))

        self.summary.columnconfigure(4, weight=1)

    def _build_actions(self):
        actions = ttk.Frame(self, padding=(10, 8))
        actions.pack(fill="x")

        ttk.Button(actions, text="Show Profit vs Cost Chart", command=self._show_chart).pack(side="right")
        ttk.Button(actions, text="Clear All", command=self._clear_all).pack(side="left")
        ttk.Checkbutton(actions, text="Ask before deleting",
                        variable=self.ask_before_delete,
                        onvalue=True, offvalue=False).pack(side="left", padx=(8, 0))

    # ------------------------- Helpers -------------------------
    def _seed_rows(self):
        # You can edit these later in the GUI
        seed = [
            {"name": "egg", "unit_cost": 22.24/90, "quantity_used": 4},
            {"name": "butter", "unit_cost": 12.18/16, "quantity_used": 8},
            {"name": "flour", "unit_cost": 6/5, "quantity_used": 3},
            {"name": "sugar", "unit_cost": 4.5/4, "quantity_used": 1.763698},
            {"name": "vanilla", "unit_cost": 13/11, "quantity_used": 2},
            {"name": "powdered_sugar", "unit_cost": 2.6/2, "quantity_used": 4},
        ]
        for row in seed:
            self._upsert_df_row(row["name"], float(row["unit_cost"]), float(row["quantity_used"]))

    def _on_select_row(self, _evt):
        item = self._get_selected_item()
        if not item:
            return
        values = self.tree.item(item, "values")
        # values order: name, unit_cost, quantity_used, total_cost
        self.name_var.set(values[0])
        self.unit_cost_var.set(values[1])
        self.qty_var.set(values[2])

    def _clear_if_empty_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        # Ignore header clicks; only care about the body (cells/tree area)
        if region in ("heading", "separator"):
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            # Clicked on empty area -> clear
            self.tree.selection_remove(self.tree.selection())
            self.tree.focus("")  # remove keyboard focus from any row
            self._clear_editor()
            return "break"

    def _parse_float(self, text, field_name):
        try:
            return float(text)
        except ValueError:
            messagebox.showerror("Invalid input", f"'{field_name}' must be a number.")
            raise

    def _add_or_update_row(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing value", "Ingredient name is required.")
            return
        try:
            unit_cost = self._parse_float(self.unit_cost_var.get(), "Unit cost")
            qty = self._parse_float(self.qty_var.get(), "Quantity used")
        except Exception:
            return
        self._upsert_df_row(name, unit_cost, qty)
        self._recalculate_and_refresh()
        self._clear_editor()

    def _delete_selected(self):
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("Nothing selected", "Please select a row to delete.")
            return

        # Only prompt if the option is enabled
        if self.ask_before_delete.get():
            if not messagebox.askyesno("Delete", "Are you sure you want to delete the selected ingredient?"):
                return
        name = self.tree.item(item, "values")[0]
        self.df = self.df[self.df["name"] != name].reset_index(drop=True)
        self._recalculate_and_refresh()
        self._clear_editor()

    def _clear_editor(self):
        self.name_var.set("")
        self.unit_cost_var.set("")
        self.qty_var.set("")

    def _get_selected_item(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _upsert_df_row(self, name, unit_cost, quantity_used):
        # Insert or update by name
        if (self.df["name"] == name).any():
            idx = self.df.index[self.df["name"] == name][0]
            self.df.at[idx, "unit_cost"] = unit_cost
            self.df.at[idx, "quantity_used"] = quantity_used
        else:
            self.df.loc[len(self.df)] = {
                "name": name,
                "unit_cost": unit_cost,
                "quantity_used": quantity_used,
                "total_cost": 0.0,
            }
        # recompute total for row
        idx = self.df.index[self.df["name"] == name][0]
        self.df.at[idx, "total_cost"] = self.df.at[idx, "unit_cost"] * self.df.at[idx, "quantity_used"]

    def _begin_cell_edit(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)

        if not item_id or not col_id:
            return

        # Make total_cost read-only
        if col_id == "#4":
            return

        # Cell geometry
        x, y, w, h = self.tree.bbox(item_id, col_id)
        if not w or not h:
            return

        # Current value (string as shown)
        current = self.tree.set(item_id, col_id)

        # Cancel any prior editor
        self._cancel_cell_edit()

        # Create editor
        self._editing_info = (item_id, col_id)
        self._edit_var = tk.StringVar(master=self, value=current)
        self._edit_entry = ttk.Entry(self.tree, textvariable=self._edit_var)
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.focus()
        self._edit_entry.select_range(0, tk.END)

        # Save/cancel handlers
        self._edit_entry.bind("<Return>", self._commit_cell_edit)
        self._edit_entry.bind("<Escape>", self._cancel_cell_edit)
        self._edit_entry.bind("<FocusOut>", self._commit_cell_edit)

    def _begin_cell_edit_on_focus(self):
        item_id = self.tree.focus()
        if not item_id:
            return
        # Choose the column the user last clicked into, or default to name (#1)
        # For simplicity, start at name:
        col_id = "#1"
        # Simulate bbox/placement
        bbox = self.tree.bbox(item_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        current = self.tree.set(item_id, col_id)
        self._cancel_cell_edit()
        self._editing_info = (item_id, col_id)
        self._edit_var = tk.StringVar(master=self, value=current)
        self._edit_entry = ttk.Entry(self.tree, textvariable=self._edit_var)
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.focus()
        self._edit_entry.select_range(0, tk.END)
        self._edit_entry.bind("<Return>", self._commit_cell_edit)
        self._edit_entry.bind("<Escape>", self._cancel_cell_edit)
        self._edit_entry.bind("<FocusOut>", self._commit_cell_edit)

    def _commit_cell_edit(self, _evt=None):
        if not self._editing_info or not self._edit_entry:
            return

        item_id, col_id = self._editing_info
        new_text = self._edit_var.get().strip()
        old_name = self.tree.set(item_id, "name")  # row key before changes

        # Map column ids to df fields
        if col_id == "#1":  # name
            if not new_text:
                messagebox.showerror("Invalid input", "Ingredient name cannot be empty.")
                return self._cancel_cell_edit()
            # Prevent duplicate names (unless it's the same row)
            if (self.df["name"] == new_text).any() and new_text != old_name:
                messagebox.showerror("Duplicate name", "An ingredient with that name already exists.")
                return self._cancel_cell_edit()
            # Update df
            if (self.df["name"] == old_name).any():
                idx = self.df.index[self.df["name"] == old_name][0]
                self.df.at[idx, "name"] = new_text

        elif col_id == "#2":  # unit_cost
            try:
                val = float(new_text)
            except ValueError:
                messagebox.showerror("Invalid input", "Unit cost must be a number.")
                return self._cancel_cell_edit()
            if (self.df["name"] == old_name).any():
                idx = self.df.index[self.df["name"] == old_name][0]
                self.df.at[idx, "unit_cost"] = val

        elif col_id == "#3":  # quantity_used
            try:
                val = float(new_text)
            except ValueError:
                messagebox.showerror("Invalid input", "Quantity used must be a number.")
                return self._cancel_cell_edit()
            if (self.df["name"] == old_name).any():
                idx = self.df.index[self.df["name"] == old_name][0]
                self.df.at[idx, "quantity_used"] = val

        # Recompute total for row (and all rows to be safe)
        if not self.df.empty:
            self.df["total_cost"] = self.df["unit_cost"] * self.df["quantity_used"]

        self._cancel_cell_edit()
        self._recalculate_and_refresh()

    def _cancel_cell_edit(self, _evt=None):
        if getattr(self, "_edit_entry", None):
            try:
                self._edit_entry.destroy()
            except Exception:
                pass
        self._edit_entry = None
        self._editing_info = None

    def _recalculate_and_refresh(self):
        # Close any active cell editor before redrawing rows
        self._cancel_cell_edit()
        # Recompute totals column just in case
        if not self.df.empty:
            self.df["total_cost"] = self.df["unit_cost"] * self.df["quantity_used"]
        total_cost = float(self.df["total_cost"].sum()) if not self.df.empty else 0.0

        # Parse yield/price (with validation)
        try:
            yld = self._parse_float(self.yield_entry.get(), "Cookies per batch")
            price = self._parse_float(self.price_entry.get(), "Price per cookie")
        except Exception:
            return

        revenue = price * yld
        profit = revenue - total_cost
        profit_per_cookie = (profit / yld) if yld else 0.0

        # Update labels
        self.total_cost_lbl.config(text=f"Total cost: ${total_cost:,.2f}")
        self.revenue_lbl.config(text=f"Revenue: ${revenue:,.2f}")
        self.profit_lbl.config(text=f"Profit: ${profit:,.2f}")
        self.ppc_lbl.config(text=f"Profit per cookie: ${profit_per_cookie:,.2f}")

        # Refresh table rows
        for r in self.tree.get_children():
            self.tree.delete(r)
        for _, row in self.df.iterrows():
            self.tree.insert(
                "",
                "end",
                values=(
                    row["name"],
                    f"{row['unit_cost']:.6f}",
                    f"{row['quantity_used']:.6f}",
                    f"{row['total_cost']:.2f}",
                ),
            )

    def _clear_all(self):
        if messagebox.askyesno("Clear all", "Remove all ingredients and reset totals?"):
            self.df = pd.DataFrame(columns=["name", "unit_cost", "quantity_used", "total_cost"])
            self._recalculate_and_refresh()
            self._clear_editor()

    def _show_chart(self):
        # Compute values
        total_cost = float(self.df["total_cost"].sum()) if not self.df.empty else 0.0
        try:
            yld = float(self.cookie_yield.get())
            price = float(self.cookie_price.get())
        except Exception:
            messagebox.showerror("Invalid input", "Fix price/yield values first.")
            return
        revenue = price * yld
        profit = revenue - total_cost

        labels = ["Total Cost", "Total Revenue", "Profit"]
        values = [total_cost, revenue, profit]

        # Pop up a window with the matplotlib figure embedded
        win = tk.Toplevel(self)
        win.title("Profit vs Cost")
        win.geometry("700x450")

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=100)
        bars = ax.bar(labels, values)
        ax.set_title("Profit vs Cost for Cookie Batch")
        ax.set_ylabel("USD ($)")
        ax.grid(axis="y", linestyle="--", alpha=0.5)

        for i, v in enumerate(values):
            ax.text(i, v + max(values) * 0.02 if max(values) else 0.02, f"${v:,.2f}", ha="center")

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # keep references to avoid garbage collection in some environments
        win._fig = fig
        win._canvas = canvas

    # ------------------------- Config helpers -------------------------
    def _load_config(self):
        try:
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        data = {
            "ask_before_delete": bool(self.ask_before_delete.get()),
            # If you later want to persist other bits, add them here:
            # "cookie_yield": float(self.cookie_yield.get()),
            # "cookie_price": float(self.cookie_price.get()),
        }
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Don’t crash if writing fails; you could log to console if desired.
            pass

    def _on_close(self):
        self._save_config()
        try:
            plt.close("all")
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = CookieCostApp()
    app.mainloop()
