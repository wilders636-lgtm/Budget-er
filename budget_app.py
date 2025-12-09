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


def apply_theme(root):
    root.configure(bg=current_theme["bg"])
    for widget in root.winfo_children():
        cls = widget.winfo_class()

        if cls in ("Frame", "LabelFrame"):
            widget.configure(bg=current_theme["bg"])
        elif cls == "Label":
            widget.configure(bg=current_theme["bg"], fg=current_theme["fg"])
        elif cls == "Entry":
            widget.configure(bg=current_theme["entry_bg"], fg=current_theme["fg"])
        elif cls == "Button":
            widget.configure(bg=current_theme["button_bg"], fg=current_theme["fg"])


def apply_theme_to_window(win):
    """Theme entire toplevel window."""
    for widget in win.winfo_children():
        cls = widget.winfo_class()

        if cls in ("Frame", "LabelFrame"):
            widget.configure(bg=current_theme["bg"])
        elif cls == "Label":
            widget.configure(bg=current_theme["bg"], fg=current_theme["fg"])
        elif cls == "Entry":
            widget.configure(bg=current_theme["entry_bg"], fg=current_theme["fg"])
        elif cls == "Button":
            widget.configure(bg=current_theme["button_bg"], fg=current_theme["fg"])

        if isinstance(widget, (tk.Frame, tk.LabelFrame)):
            for child in widget.winfo_children():
                try:
                    ccls = child.winfo_class()
                    if ccls in ("Frame", "LabelFrame"):
                        child.configure(bg=current_theme["bg"])
                    elif ccls == "Label":
                        child.configure(bg=current_theme["bg"], fg=current_theme["fg"])
                    elif ccls == "Entry":
                        child.configure(bg=current_theme["entry_bg"], fg=current_theme["fg"])
                    elif ccls == "Button":
                        child.configure(bg=current_theme["button_bg"], fg=current_theme["fg"])
                except:
                    pass


def toggle_theme(root):
    global current_theme
    current_theme = DARK_THEME if current_theme == LIGHT_THEME else LIGHT_THEME
    apply_theme(root)

    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel):
            apply_theme_to_window(w)


# -----------------------------
# SUMMARY
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

    container = tk.Frame(win)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)

    content = tk.Frame(canvas)
    canvas.create_window((0, 0), window=content, anchor="nw")

    def _resize(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", _resize)

    # Add Expense
    add_frame = tk.LabelFrame(content, text="Add Expense")
    add_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(add_frame, text="Category:").grid(row=0, column=0, padx=5)
    tk.Label(add_frame, text="Amount:").grid(row=0, column=2, padx=5)

    cats = [c[1] for c in get_categories()]
    if not cats:
        cats = ["Rent", "Food", "Gas", "Utilities", "Personal"]

    selected_category = tk.StringVar(value=cats[0])
    category_dropdown = ttk.Combobox(add_frame, values=cats, state="readonly")
    category_dropdown.grid(row=0, column=1, padx=5)

    amount_entry = tk.Entry(add_frame, width=10)
    amount_entry.grid(row=0, column=3, padx=5)

    def save_expense():
        try:
            amt = float(amount_entry.get())
        except:
            messagebox.showerror("Invalid Input", "Enter a valid number.")
            return

        cname = selected_category.get()

        cid = None
        for c in get_categories():
            if c[1] == cname:
                cid = c[0]

        if cid is None:
            messagebox.showerror("Error", "Category not found.")
            return

        add_expense(amt, cid)
        amount_entry.delete(0, tk.END)
        load_expenses()
        update_summary(summary_labels)

    tk.Button(add_frame, text="Add Expense", command=save_expense).grid(
        row=1, column=0, columnspan=4, pady=10
    )

    # Expense Table
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
        total = 0
        for r in expense_table.get_children():
            expense_table.delete(r)

        rows = get_expenses()
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
        exp_id = expense_table.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Delete expense {exp_id}?"):
            delete_expense(exp_id)
            load_expenses()
            update_summary(summary_labels)

    tk.Button(table_frame, text="Delete Selected", fg="red",
              command=delete_expense_ui).pack(pady=5)

    apply_theme_to_window(win)


# -----------------------------
# CHARTS
# -----------------------------
def open_charts_window(root):
    rows = get_expenses()
    if not rows:
        messagebox.showinfo("No Data", "No expenses to chart.")
        return

    totals = {}
    for r in rows:
        cat = r[2]
        amt = float(r[1])
        totals[cat] = totals.get(cat, 0) + amt

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
    root.geometry("520x620")

    # Load icon safely
    try:
        png = tk.PhotoImage(file="app_icon.png")
        icon_img = png.subsample(max(1, png.width() // 48), max(1, png.height() // 48))
    except:
        icon_img = None

    # Header
    header = tk.Frame(root, height=50)
    header.pack(fill="x")

    if icon_img:
        tk.Label(header, image=icon_img, bg=current_theme["bg"]).pack(side="left", padx=10)

    tk.Label(
        header,
        text="💰 Budget-er",
        font=("Arial", 18, "bold"),
        bg=current_theme["bg"],
        fg=current_theme["fg"]
    ).pack(side="left")

    # Inputs
    input_frame = tk.Frame(root)
    input_frame.pack(pady=15)

    labels = ["Income", "Expenses", "Savings", "Cash"]
    entries = {}

    for text in labels:
        row = tk.Frame(input_frame)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=text + ":", width=12, anchor="w").pack(side="left")
        entry = tk.Entry(row, width=20)
        entry.pack(side="right")
        entries[text.lower()] = entry

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

    tk.Button(root, text="Manage Expenses",
              command=lambda: open_expense_manager(root, summary_labels)).pack(pady=5)

    # CSV
    csv_frame = tk.Frame(root)
    csv_frame.pack(pady=5)

    def do_export():
        p = filedialog.asksaveasfilename(defaultextension=".csv")
        if p:
            export_expenses_csv(p)
            messagebox.showinfo("Exported", "CSV saved!")

    def do_import():
        p = filedialog.askopenfilename()
        if p:
            import_expenses_csv(p)
            update_summary(summary_labels)
            messagebox.showinfo("Imported", "CSV imported!")

    tk.Button(csv_frame, text="Export CSV", command=do_export).pack(side="left", padx=5)
    tk.Button(csv_frame, text="Import CSV", command=do_import).pack(side="left", padx=5)

    # Summary
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

    # Charts button
    tk.Button(root, text="Charts", width=15,
              command=lambda: open_charts_window(root)).pack(pady=5)

    # Theme toggle
    tk.Button(root, text="Toggle Theme",
              command=lambda: toggle_theme(root)).pack(pady=10)

    apply_theme(root)
    update_summary(summary_labels)

    root.mainloop()


if __name__ == "__main__":
    main_ui()
