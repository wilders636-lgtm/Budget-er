import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from budget_db import (
    create_tables,
    get_budget, update_budget,
    get_categories, add_category, delete_category,
    add_expense, get_expenses, delete_expense,
    export_expenses_csv, import_expenses_csv
)

from budget_logic import calculate_summary

# Ensure tables exist
create_tables()

# -----------------------------
# THEME SETTINGS
# -----------------------------
LIGHT_THEME = {
    "bg": "#ffffff",
    "fg": "#000000",
    "entry_bg": "#f0f0f0",
    "button_bg": "#e0e0e0",
}

DARK_THEME = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "entry_bg": "#2e2e2e",
    "button_bg": "#3e3e3e",
}

current_theme = LIGHT_THEME


# ---------------------------------------------------
# GLOBAL THEME APPLY FUNCTIONS
# ---------------------------------------------------
def apply_theme(root):
    """Apply theme to root window and all children."""
    root.configure(bg=current_theme["bg"])
    for widget in root.winfo_children():
        _apply_widget_theme(widget)


def apply_theme_to_window(win):
    """Apply theme to a Toplevel window and all nested children."""
    win.configure(bg=current_theme["bg"])
    for widget in win.winfo_children():
        _apply_widget_theme(widget)
        if isinstance(widget, (tk.Frame, tk.LabelFrame)):
            for child in widget.winfo_children():
                _apply_widget_theme(child)


def _apply_widget_theme(widget):
    cls = widget.winfo_class()
    if cls in ("Frame", "LabelFrame"):
        widget.configure(bg=current_theme["bg"])
    elif cls == "Label":
        widget.configure(bg=current_theme["bg"], fg=current_theme["fg"])
    elif cls == "Entry":
        widget.configure(
            bg=current_theme["entry_bg"],
            fg=current_theme["fg"]
        )
    elif cls == "Button":
        widget.configure(
            bg=current_theme["button_bg"],
            fg=current_theme["fg"]
        )


def toggle_theme(root):
    global current_theme
    current_theme = DARK_THEME if current_theme == LIGHT_THEME else LIGHT_THEME
    apply_theme(root)

    # Update theme for open windows
    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            apply_theme_to_window(window)


# -----------------------------
# SUMMARY + SAVE LOGIC
# -----------------------------
def save_data(income_entry, expenses_entry, savings_entry, cash_entry, summary_labels):
    try:
        income = float(income_entry.get())
        savings = float(savings_entry.get())
        cash = float(cash_entry.get())

        update_budget(income, savings, cash)
        update_summary(summary_labels)

    except ValueError:
        summary_labels["remaining"].config(text="Enter valid numbers!")


def update_summary(summary_labels):
    data = calculate_summary()

    summary_labels["remaining"].config(text=f"${data['remaining']:.2f}")
    summary_labels["savings_percent"].config(text=f"{data['savings_percent']:.1f}%")
    summary_labels["weekly_allowance"].config(text=f"${data['weekly_allowance']:.2f}")

    summary_labels["overspending"].config(
        text="Overspending!" if data["overspending"] else ""
    )
    summary_labels["negative_cash"].config(
        text="Negative Cash Balance!" if data["negative_cash"] else ""
    )


# -----------------------------
# EXPENSE MANAGER
# -----------------------------
def open_expense_manager(root, summary_labels):
    win = tk.Toplevel(root)
    win.title("Expense Manager")
    win.geometry("835x650")
    apply_theme_to_window(win)

    # Scroll container
    container = tk.Frame(win)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)

    content = tk.Frame(canvas)
    canvas.create_window((0, 0), window=content, anchor="nw")

    def resize(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", resize)

    # -----------------------------
    # ADD EXPENSE SECTION
    # -----------------------------
    add_frame = tk.LabelFrame(content, text="Add Expense")
    add_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(add_frame, text="Category:").grid(row=0, column=0, padx=5)
    tk.Label(add_frame, text="Amount:").grid(row=0, column=2, padx=5)

    # Load categories properly
    def get_category_names():
        return [c[1] for c in get_categories()]

    category_list = get_category_names()
    if not category_list:
        category_list = ["General"]

    selected_category = tk.StringVar(value=category_list[0])

    category_dropdown = ttk.Combobox(
        add_frame, values=category_list, textvariable=selected_category, state="readonly"
    )
    category_dropdown.grid(row=0, column=1, padx=5)

    amount_entry = tk.Entry(add_frame, width=10)
    amount_entry.grid(row=0, column=3, padx=5)

    def refresh_dropdown():
        names = get_category_names()
        category_dropdown["values"] = names
        if selected_category.get() not in names:
            selected_category.set(names[0] if names else "")

    def save_expense():
        try:
            amt = float(amount_entry.get())
        except:
            messagebox.showerror("Error", "Enter a valid number.")
            return

        cat_name = selected_category.get()

        # CORRECT CATEGORY LOOKUP (fixed your bug)
        categories = get_categories()
        cat_id = next((c[0] for c in categories if c[1] == cat_name), None)

        if cat_id is None:
            messagebox.showerror("Error", f"Category '{cat_name}' not found.")
            return

        add_expense(amt, cat_id)
        amount_entry.delete(0, tk.END)
        load_expenses()
        update_summary(summary_labels)

    tk.Button(add_frame, text="Add Expense", command=save_expense).grid(
        row=1, column=0, columnspan=4, pady=10
    )

    # -----------------------------
    # EXPENSE TABLE
    # -----------------------------
    table_frame = tk.LabelFrame(content, text="Expenses")
    table_frame.pack(fill="x", padx=10, pady=10)

    cols = ("id", "amount", "category", "date")
    expense_table = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
    expense_table.pack(fill="x")

    for col in cols:
        expense_table.heading(col, text=col.title())

    total_label = tk.Label(table_frame, text="Total: $0.00")
    total_label.pack(pady=5)

    def load_expenses():
        for r in expense_table.get_children():
            expense_table.delete(r)

        rows = get_expenses()
        total = 0

        for rec in rows:
            expense_table.insert("", "end", values=rec)
            total += float(rec[1])

        total_label.config(text=f"Total: ${total:.2f}")

    load_expenses()

    tk.Button(table_frame, text="Refresh", command=load_expenses).pack(pady=5)

    def delete_expense_ui():
        sel = expense_table.selection()
        if not sel:
            return

        row = expense_table.item(sel[0])["values"]
        exp_id = row[0]

        if messagebox.askyesno("Confirm", f"Delete expense {exp_id}?"):
            delete_expense(exp_id)
            load_expenses()
            update_summary(summary_labels)

    tk.Button(table_frame, text="Delete Selected", fg="red",
              command=delete_expense_ui).pack(pady=5)

    # -----------------------------
    # CATEGORY MANAGER
    # -----------------------------
    cat_header = tk.Button(content, text="▶ Categories", relief="flat", anchor="w")
    cat_header.pack(fill="x", padx=10, pady=(10, 0))

    cat_frame = tk.Frame(content)
    cat_open = False

    def build_cat_frame():
        for widget in cat_frame.winfo_children():
            widget.destroy()

        add_cat_frame = tk.LabelFrame(cat_frame, text="Add Category")
        add_cat_frame.pack(fill="x", pady=5)

        tk.Label(add_cat_frame, text="Name:").grid(row=0, column=0, padx=5)
        name_entry = tk.Entry(add_cat_frame, width=20)
        name_entry.grid(row=0, column=1)

        def add_new_cat():
            name = name_entry.get().strip()
            if not name:
                return
            add_category(name)
            name_entry.delete(0, tk.END)
            load_cat()
            refresh_dropdown()

        tk.Button(add_cat_frame, text="Add", command=add_new_cat).grid(row=0, column=2, padx=5)

        # Category table
        cat_table_frame = tk.LabelFrame(cat_frame, text="Categories")
        cat_table_frame.pack(fill="x", pady=5)

        cat_table = ttk.Treeview(cat_table_frame, columns=("id", "name"),
                                 show="headings", height=6)
        cat_table.pack(fill="x")

        cat_table.heading("id", text="ID")
        cat_table.heading("name", text="Name")

        def load_cat():
            for r in cat_table.get_children():
                cat_table.delete(r)
            for row in get_categories():
                cat_table.insert("", "end", values=row)

        def delete_cat():
            sel = cat_table.selection()
            if not sel:
                return

            row = cat_table.item(sel[0])["values"]
            cid, cname = row[0], row[1]

            if messagebox.askyesno("Confirm", f"Delete '{cname}'?"):
                delete_category(cid)
                load_cat()
                refresh_dropdown()

        load_cat()

        tk.Button(cat_frame, text="Delete Selected", fg="red", command=delete_cat).pack(pady=5)

    def toggle_cat():
        nonlocal cat_open
        if not cat_open:
            cat_open = True
            cat_header.config(text="▼ Categories")
            cat_frame.pack(fill="x", padx=10, pady=10)
            build_cat_frame()
            apply_theme_to_window(win)
        else:
            cat_open = False
            cat_header.config(text="▶ Categories")
            cat_frame.pack_forget()

    cat_header.config(command=toggle_cat)


# -----------------------------
# CHART WINDOW
# -----------------------------
def open_charts_window(root):
    rows = get_expenses()
    if not rows:
        messagebox.showinfo("No Data", "No expenses available.")
        return

    totals = {}
    for row in rows:
        amount = float(row[1])
        category = row[2]
        totals[category] = totals.get(category, 0) + amount

    cats = list(totals.keys())
    vals = list(totals.values())

    win = tk.Toplevel(root)
    win.title("Charts")
    win.geometry("750x600")
    apply_theme_to_window(win)

    fig = Figure(figsize=(8, 5), dpi=100)

    ax1 = fig.add_subplot(1, 2, 1)
    ax1.pie(vals, labels=cats, autopct="%1.1f%%")
    ax1.set_title("Expense Distribution")

    ax2 = fig.add_subplot(1, 2, 2)
    ax2.bar(cats, vals)
    ax2.set_title("Totals by Category")
    ax2.tick_params(axis="x", rotation=45)

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    tk.Button(win, text="Close", command=win.destroy).pack(pady=10)


# -----------------------------
# MAIN UI
# -----------------------------
def main_ui():
    root = tk.Tk()
    root.title("Budget-er")
    root.geometry("520x600")

    # Header
    header = tk.Frame(root, height=50)
    header.pack(fill="x")
    tk.Label(
        header,
        text="💰  Budget-er",
        font=("Arial", 18, "bold"),
        anchor="w",
        padx=15
    ).pack(fill="both")

    # Input Panel
    input_frame = tk.Frame(root)
    input_frame.pack(pady=15)

    labels = ["Income", "Expenses", "Savings", "Cash"]
    entries = {}

    for text in labels:
        row = tk.Frame(input_frame)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=f"{text}:", width=12, anchor="w").pack(side="left")
        entry = tk.Entry(row, width=20)
        entry.pack(side="right")
        entries[text.lower()] = entry

    # Load saved budget
    b = get_budget()
    if b:
        entries["income"].insert(0, str(b[0]))
        entries["savings"].insert(0, str(b[1]))
        entries["cash"].insert(0, str(b[2]))

    summary_labels = {
        "remaining": None,
        "savings_percent": None,
        "weekly_allowance": None,
        "overspending": None,
        "negative_cash": None,
    }

    # Save button
    tk.Button(
        root,
        text="Save",
        command=lambda: save_data(
            entries["income"],
            entries["expenses"],
            entries["savings"],
            entries["cash"],
            summary_labels
        )
    ).pack(pady=5)

    # Manage Expenses
    tk.Button(
        root,
        text="Manage Expenses",
        command=lambda: open_expense_manager(root, summary_labels)
    ).pack(pady=5)

    # CSV
    csv_frame = tk.Frame(root)
    csv_frame.pack(pady=5)

    tk.Button(csv_frame, text="Export CSV",
              command=lambda: _export_csv(root)).pack(side="left", padx=5)

    tk.Button(csv_frame, text="Import CSV",
              command=lambda: _import_csv(root, summary_labels)).pack(side="left", padx=5)

    # Summary Panel
    summary_frame = tk.LabelFrame(root, text="Summary")
    summary_frame.pack(fill="x", padx=20, pady=10)

    rows = [
        ("Remaining:", "remaining"),
        ("Savings %:", "savings_percent"),
        ("Weekly Allowance:", "weekly_allowance"),
    ]

    for label, key in rows:
        line = tk.Frame(summary_frame)
        line.pack(fill="x", pady=3)
        tk.Label(line, text=label).pack(side="left")
        val = tk.Label(line, text="")
        val.pack(side="right")
        summary_labels[key] = val

    summary_labels["overspending"] = tk.Label(root, fg="red")
    summary_labels["overspending"].pack()
    summary_labels["negative_cash"] = tk.Label(root, fg="red")
    summary_labels["negative_cash"].pack()

    # Charts
    tk.Button(root, text="Charts", width=15,
              command=lambda: open_charts_window(root)).pack(pady=5)

    # Theme Toggle
    tk.Button(root, text="Toggle Theme",
              command=lambda: toggle_theme(root)).pack(pady=10)

    apply_theme(root)
    update_summary(summary_labels)

    root.mainloop()


# CSV helper functions
def _export_csv(root):
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")]
    )
    if not path:
        return
    export_expenses_csv(path)
    messagebox.showinfo("Export", "Expenses exported successfully.")


def _import_csv(root, summary_labels):
    path = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    if not path:
        return
    import_expenses_csv(path)
    update_summary(summary_labels)
    messagebox.showinfo("Import", "Expenses imported successfully.")


if __name__ == "__main__":
    main_ui()
