import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import os

FILENAME = "expenses.csv"
undo_stack = []  # To store deleted entries for redo

# Add Time if not in CSV
if not os.path.exists(FILENAME):
    pd.DataFrame(columns=["Date", "Time", "Category", "Amount", "Description"]).to_csv(FILENAME, index=False)

def add_expense(date, time, category, amount, description):
    df = pd.read_csv(FILENAME)
    
    # Capitalize the first letter of the category
    category = category.strip().capitalize()

    if not time:
        time = datetime.now().strftime('%H:%M:%S') + " (auto)"
    
    new = pd.DataFrame([[date, time, category, amount, description]],
                       columns=["Date", "Time", "Category", "Amount", "Description"])
    
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(FILENAME, index=False)
    messagebox.showinfo("Success", "Expense Added!")

def load_expenses(tree, category_filter=None, sort_by=None, order="Descending"):
    for row in tree.get_children():
        tree.delete(row)
    df = pd.read_csv(FILENAME)
    
    # Apply category filter if selected (case-insensitive matching)
    if category_filter and category_filter != "All":
        # Normalize the case for comparison and filter
        df = df[df["Category"].str.lower() == category_filter.lower()]
    
    # Apply sorting
    if sort_by:
        if sort_by == "Category":
            # Sorting category case-insensitively
            df = df.sort_values(by=sort_by, ascending=(order == "Ascending"), key=lambda x: x.str.lower())  # Case insensitive sort
        else:
            df = df.sort_values(by=sort_by, ascending=(order == "Ascending"))
    else:
        df = df[::-1]  # default: latest on top
    
    # Insert data into the treeview
    for _, row in df.iterrows():
        tree.insert('', 'end', values=list(row))

def plot_by_date():
    df = pd.read_csv(FILENAME, parse_dates=["Date"])
    daily = df.groupby("Date")["Amount"].sum()
    daily.plot(kind='bar', title="Expenses by Date", ylabel="Amount (₹)", xlabel="Date")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def plot_by_category():
    df = pd.read_csv(FILENAME)
    cats = df.groupby("Category")["Amount"].sum()
    cats.plot(kind='pie', autopct='%1.1f%%', startangle=90, title="By Category")
    plt.ylabel('')
    plt.tight_layout()
    plt.show()

def export_summary(group_by, title):
    df = pd.read_csv(FILENAME, parse_dates=["Date"])
    if group_by == "month":
        df["Month"] = df["Date"].dt.to_period("M").astype(str)
        summary = df.groupby("Month")["Amount"].sum().reset_index()
    else:
        df["Year"] = df["Date"].dt.year
        summary = df.groupby("Year")["Amount"].sum().reset_index()

    export_path = filedialog.asksaveasfilename(defaultextension=".pdf")
    if export_path.endswith(".pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, title, ln=True, align='C')
        for _, row in summary.iterrows():
            line = " | ".join(str(x) for x in row)
            pdf.cell(200, 10, txt=line, ln=True)
        pdf.output(export_path)
        messagebox.showinfo("Exported", f"PDF saved to {export_path}")
    else:
        summary.to_csv(export_path, index=False)
        messagebox.showinfo("Exported", f"CSV saved to {export_path}")

def delete_expense(tree):
    global undo_stack
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("No selection", "Please select at least one expense to delete.")
        return

    df = pd.read_csv(FILENAME)
    initial_len = len(df)
    to_delete = []

    for item in selected_items:
        values = tree.item(item, 'values')
        match = df[
            (df["Date"] == values[0]) &
            (df["Time"] == values[1]) &
            (df["Category"] == values[2]) &
            (pd.to_numeric(df["Amount"], errors="coerce") == float(values[3])) &
            (df["Description"] == values[4])
        ]
        to_delete.append(match)

        df = df.drop(match.index)

    if to_delete:
        undo_stack = pd.concat(to_delete)  # Save deleted rows
        df.to_csv(FILENAME, index=False)
        messagebox.showinfo("Deleted", f"{initial_len - len(df)} expense(s) deleted.")
        load_expenses(tree)

def redo_delete(tree):
    global undo_stack
    if undo_stack is None or undo_stack.empty:
        messagebox.showinfo("Redo", "Nothing to restore.")
        return

    df = pd.read_csv(FILENAME)
    df = pd.concat([df, undo_stack], ignore_index=True)
    df.to_csv(FILENAME, index=False)
    undo_stack = []  # Clear after restoring
    messagebox.showinfo("Redo", "Deleted expense(s) restored.")
    load_expenses(tree)

def main():
    app = tb.Window(themename="flatly")
    app.title("💸 Modern Expense Tracker")
    app.geometry("1000x650")

    # ====================== Form ========================
    form_frame = tb.Frame(app, padding=10)
    form_frame.pack(fill=X)

    tb.Label(form_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=E)
    date_entry = tb.Entry(form_frame)
    date_entry.insert(0, datetime.today().strftime('%Y-%m-%d'))
    date_entry.grid(row=0, column=1, padx=5)

    tb.Label(form_frame, text="Time (optional):").grid(row=0, column=2, sticky=E)
    time_entry = tb.Entry(form_frame)
    time_entry.grid(row=0, column=3, padx=5)

    tb.Label(form_frame, text="Category:").grid(row=1, column=0, sticky=E)
    category_entry = tb.Entry(form_frame)
    category_entry.grid(row=1, column=1, padx=5)

    tb.Label(form_frame, text="Amount:").grid(row=1, column=2, sticky=E)
    amount_entry = tb.Entry(form_frame)
    amount_entry.grid(row=1, column=3, padx=5)

    tb.Label(form_frame, text="Description:").grid(row=2, column=0, sticky=E)
    desc_entry = tb.Entry(form_frame, width=70)
    desc_entry.grid(row=2, column=1, columnspan=3, padx=5)

    tb.Button(form_frame, text="Add Expense", bootstyle="success", width=30,
              command=lambda: add_expense(
                  date_entry.get(), time_entry.get(),
                  category_entry.get(), float(amount_entry.get()), desc_entry.get())
              ).grid(row=3, column=0, columnspan=4, pady=10)

    # =================== Filter & Action Panel ===================
    filter_frame = tb.Frame(app, padding=10)
    filter_frame.pack(fill=X)

    tb.Label(filter_frame, text="Choose Category:").pack(side=LEFT, padx=(5, 2))
    category_box = tb.Combobox(filter_frame, values=["All"], width=20, bootstyle="info")
    category_box.current(0)
    category_box.pack(side=LEFT, padx=5)

    tb.Label(filter_frame, text="Sort by:").pack(side=LEFT, padx=(20, 2))
    sort_box = tb.Combobox(filter_frame, values=["Date", "Category", "Amount"], width=15, bootstyle="info")
    sort_box.pack(side=LEFT, padx=5)

    order_box = tb.Combobox(filter_frame, values=["Descending", "Ascending"], width=15, bootstyle="info")
    order_box.set("Descending")
    order_box.pack(side=LEFT, padx=5)

    tb.Button(filter_frame, text="Apply", bootstyle="primary", 
              command=lambda: load_expenses(
                  tree,
                  category_box.get(),
                  sort_box.get() if sort_box.get() else None,
                  order_box.get()
              )).pack(side=LEFT, padx=(10, 5))

    tb.Button(filter_frame, text="Reset", bootstyle="danger",
              command=lambda: [category_box.set("All"), sort_box.set(""), order_box.set("Descending"), load_expenses(tree)]
              ).pack(side=LEFT, padx=5)

    tb.Button(filter_frame, text="📊 Plot by Date", bootstyle="warning", command=plot_by_date).pack(side=RIGHT, padx=5)
    tb.Button(filter_frame, text="📈 Plot by Category", bootstyle="warning", command=plot_by_category).pack(side=RIGHT, padx=5)
    tb.Button(filter_frame, text="📅 Export Monthly", bootstyle="info", command=lambda: export_summary("month", "Monthly Summary")).pack(side=RIGHT, padx=5)
    tb.Button(filter_frame, text="📆 Export Yearly", bootstyle="info", command=lambda: export_summary("year", "Yearly Summary")).pack(side=RIGHT, padx=5)

    # =================== Table ===================
    table_frame = tb.Frame(app, padding=10)
    table_frame.pack(fill=BOTH, expand=YES)
    
    columns = ["Date", "Time", "Category", "Amount", "Description"]
    tree = tb.Treeview(table_frame, columns=columns, show="headings", height=15, bootstyle="info")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")
    tree.pack(fill=BOTH, expand=YES)
    # Horizontal button frame for Delete and Redo
    button_frame = tb.Frame(app)
    button_frame.pack(pady=5)

    tb.Button(button_frame, text="🗑️ Delete Selected", bootstyle="danger", 
            command=lambda: delete_expense(tree)).pack(side=LEFT, padx=10)

    tb.Button(button_frame, text="↩️ Redo Delete", bootstyle="secondary", 
            command=lambda: redo_delete(tree)).pack(side=LEFT, padx=10)


    # Load categories into dropdown
    def update_category_box():
        df = pd.read_csv(FILENAME)
        cats = sorted(df["Category"].unique())
        category_box["values"] = ["All"] + cats

    update_category_box()
    load_expenses(tree)

    app.mainloop()

if __name__ == "__main__":
    main()
