"""Version 3 screens: date reports, validated CSV import and archive recovery."""
import sqlite3
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from import_utils import write_template
from widgets import BG, WHITE, INK, BLUE, MUTED, Card


def money(paise):
    return f'INR {paise/100:,.2f}'


class EnhancementViews:
    def analytics_page(self):
        self.heading('Reports & insights','Choose a date range, inspect your best sellers and export the underlying records.')
        notebook=ttk.Notebook(self.content)
        notebook.pack(fill='both',expand=True)
        sales=tk.Frame(notebook,bg=BG,padx=14,pady=16)
        inventory=tk.Frame(notebook,bg=BG,padx=14,pady=16)
        notebook.add(sales,text='  Sales analytics  ')
        notebook.add(inventory,text='  Inventory & backups  ')
        self.report_notebook=notebook
        filters=tk.Frame(sales,bg=BG); filters.pack(fill='x',pady=(0,10))
        start=tk.StringVar(value=date.today().replace(day=1).isoformat())
        end=tk.StringVar(value=date.today().isoformat())
        for label,variable in [('From',start),('To',end)]:
            self.label(filters,label,10,MUTED).pack(side='left',padx=(0,7))
            ttk.Entry(filters,textvariable=variable,width=13).pack(side='left',padx=(0,15))
        result={}
        self.button(filters,'Apply dates',lambda:refresh(),True).pack(side='left')
        self.button(filters,'Export report',lambda:export()).pack(side='right')
        shortcuts=tk.Frame(sales,bg=BG); shortcuts.pack(fill='x',pady=(0,12))
        def preset(days=None):
            today=date.today()
            start.set((today.replace(day=1) if days is None else today-timedelta(days=days-1)).isoformat())
            end.set(today.isoformat()); refresh()
        for text,days in [('Today',1),('Last 7 days',7),('This month',None)]:
            self.button(shortcuts,text,lambda d=days:preset(d)).pack(side='left',padx=(0,8))
        report_status=self.label(shortcuts,'',9,MUTED)
        report_status.pack(side='right')
        cards=tk.Frame(sales,bg=BG); cards.pack(fill='x',pady=(0,16))
        totals=[]
        for i,title in enumerate(['Completed sales value','Completed orders','Units sold']):
            cards.columnconfigure(i,weight=1,uniform='stat')
            card=Card(cards,height=91,padding=14)
            card.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==2 else 6))
            self.label(card.body,title,9,MUTED).pack(anchor='w')
            value=self.label(card.body,'0',20,INK,True); value.pack(anchor='w',pady=(5,0)); totals.append(value)
        panel=self.panel(sales); panel.pack(fill='both',expand=True)
        heading=tk.Frame(panel,bg=WHITE); heading.pack(fill='x',padx=15,pady=12)
        self.label(heading,'Best-selling products',13,INK,True).pack(side='left')
        self.label(heading,'Ranked by units sold',9,MUTED).pack(side='right')
        tree=self.table(panel,[('sku','SKU',110),('name','Product',230),('units','Units sold',110),('value','Sales (INR)',150),('orders','Orders',95)],6)
        hint=self.label(sales,'',9,MUTED,wraplength=770,justify='left')
        hint.pack(side='bottom',anchor='w',pady=(10,0),before=panel)
        def mark_dirty(*args):
            report_status.configure(text='Dates changed - click Apply',fg='#AE781C')
        def refresh():
            try:
                current=self.db.sales_report(start.get().strip(),end.get().strip())
            except ValueError as error:
                self.notify_error(error); return False
            result.clear(); result.update(current)
            totals[0].configure(text=money(current['sales']))
            totals[1].configure(text=str(current['order_count']))
            totals[2].configure(text=str(current['units']))
            tree.delete(*tree.get_children())
            for i,row in enumerate(current['products']):
                tree.insert('','end',values=(row['sku'],row['name'],row['units'],f'{row["revenue"]/100:,.2f}',row['order_count']),tags=('alt' if i%2 else '',))
            report_status.configure(text='Both dates included',fg=MUTED)
            hint.configure(text=f"Showing {current['start']} to {current['end']}. " +
                           ('No completed sales in this period.' if not current['orders'] else 'Cancelled sales are excluded. Historical line prices are used; product labels show current names.'))
            return True
        def export():
            if not refresh(): return
            path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',
                    initialfile=f"sales_{result['start']}_to_{result['end']}.csv",filetypes=[('CSV','*.csv')])
            if path:
                try:
                    self.db.export_sales_report(path,result['start'],result['end'])
                    self.status.set('Date-filtered sales report exported')
                except (OSError,sqlite3.Error,ValueError) as error: self.notify_error(error)
        start.trace_add('write',mark_dirty); end.trace_add('write',mark_dirty)
        self.report_start,self.report_end,self.refresh_report=start,end,refresh
        self.report_tree,self.report_result,self.export_period_report=tree,result,export
        refresh()
        actions=tk.Frame(inventory,bg=BG); actions.pack(fill='x',pady=(0,18))
        self.button(actions,'Products CSV',lambda:self.export('all'),True).pack(side='left')
        self.button(actions,'Low stock CSV',lambda:self.export('low')).pack(side='left',padx=8)
        self.button(actions,'History CSV',lambda:self.export('all_history')).pack(side='left')
        if self.db.user['role']=='Admin': self.button(actions,'Backup database',self.backup).pack(side='right')
        panel=self.panel(inventory); panel.pack(fill='both',expand=True)
        self.label(panel,'Inventory by category',14,INK,True).pack(anchor='w',padx=18,pady=(17,8))
        self.label(panel,'Current stock value uses the current product price. It is not profit.',10,MUTED).pack(anchor='w',padx=18,pady=(0,12))
        category_tree=self.table(panel,[('category','Category',230),('products','Products',120),('units','Stock units',130),('value','Stock value',200)])
        for row in self.db.category_summary():
            category_tree.insert('','end',values=(row['category'],row['products'],row['units'],money(row['value'])))

    def archives_dialog(self):
        self.db.require(admin=True)
        dialog=tk.Toplevel(self); dialog.title('Archived products'); dialog.configure(bg=BG)
        dialog.geometry('850x570'); dialog.minsize(760,480); dialog.transient(self); dialog.grab_set()
        body=tk.Frame(dialog,bg=BG,padx=22,pady=20); body.pack(fill='both',expand=True)
        self.label(body,'Archived products',23,INK,True).pack(anchor='w')
        self.label(body,'Restore a product with its original SKU, ID and transaction history.',10,MUTED).pack(anchor='w',pady=(6,16))
        search=tk.StringVar()
        row=tk.Frame(body,bg=BG); row.pack(fill='x',pady=(0,12))
        ttk.Entry(row,textvariable=search,width=30).pack(side='left')
        self.label(row,'Search name or SKU',10,MUTED).pack(side='left',padx=10)
        panel=self.panel(body); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('sku','SKU',120),('name','Product',220),('category','Category',140),('qty','Stock',80),('price','Price (INR)',130)])
        footer=tk.Frame(body,bg=BG); footer.pack(side='bottom',fill='x',pady=(12,0),before=panel)
        count=self.label(footer,'',10,MUTED); count.pack(side='left')
        def refresh(*args):
            tree.delete(*tree.get_children()); rows=self.db.archived_products(search.get())
            for r in rows: tree.insert('','end',iid=str(r['id']),values=(r['sku'],r['name'],r['category'],r['quantity'],f'{r["price_paise"]/100:.2f}'))
            count.configure(text=f'{len(rows)} archived products')
        def restore():
            selected=tree.selection()
            if not selected: return messagebox.showinfo('Select a product','Select an archived product to restore.',parent=dialog)
            if not messagebox.askyesno('Restore product','Restore this product to the active catalogue? Its quantity stays unchanged.',parent=dialog): return
            try:
                self.db.restore_product(int(selected[0])); refresh()
                self.status.set('Product restored with its original history')
                self.show_page('Products')
            except (ValueError,sqlite3.Error) as error: self.notify_error(error,dialog)
        self.button(footer,'Restore selected',restore,True).pack(side='right')
        self.button(footer,'Close',dialog.destroy).pack(side='right',padx=8)
        search.trace_add('write',refresh); refresh()
        dialog.archive_tree,dialog.restore_selected,dialog.archive_search=tree,restore,search
        return dialog

    def csv_import_dialog(self):
        self.db.require(admin=True)
        dialog=tk.Toplevel(self); dialog.title('Import products from CSV'); dialog.configure(bg=BG)
        dialog.geometry('1040x700'); dialog.minsize(980,650); dialog.transient(self); dialog.grab_set()
        body=tk.Frame(dialog,bg=BG,padx=22,pady=20); body.pack(fill='both',expand=True)
        self.label(body,'Import products',23,INK,True).pack(anchor='w')
        self.label(body,'Preview first. Every row must be valid before anything is saved.',10,MUTED).pack(anchor='w',pady=(6,16))
        toolbar=tk.Frame(body,bg=BG); toolbar.pack(fill='x',pady=(0,10))
        self.button(toolbar,'Choose CSV',lambda:load(),True).pack(side='left')
        self.button(toolbar,'Download template',lambda:template()).pack(side='left',padx=9)
        filename=self.label(toolbar,'No file selected',10,MUTED); filename.pack(side='right')
        summary=self.label(body,'Use the template or examples/products_valid.csv to get started.',10,BLUE)
        summary.pack(anchor='w',pady=(0,12))
        panel=self.panel(body); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('row','Row',65),('sku','SKU',110),('name','Product',180),('category','Category',120),
                               ('price','Price',90),('qty','Qty',65),('level','Reorder',85),('status','Validation',220)],8)
        bottom=tk.Frame(body,bg=BG); bottom.pack(side='bottom',fill='x',pady=(12,0),before=panel)
        self.label(bottom,'Validation details - select a row',10,MUTED).pack(anchor='w')
        detail=tk.Text(bottom,height=3,wrap='word',font=(self.font,10),bg=WHITE,fg=INK,relief='flat',padx=9,pady=8)
        detail.pack(fill='x',pady=(5,10)); detail.configure(state='disabled')
        actions=tk.Frame(bottom,bg=BG); actions.pack(fill='x')
        self.label(actions,'Import adds new products; existing records are never overwritten.',9,MUTED).pack(side='left')
        import_button=self.button(actions,'Import all products',lambda:commit(),True); import_button.pack(side='right'); import_button.state(['disabled'])
        rows=[]
        def details(event=None):
            selected=tree.selection()
            text=''
            if selected:
                r=rows[int(selected[0])]
                text=f"Row {r['row']}: "+ ('\n'.join(r['errors']) if r['errors'] else 'Ready to import. A stock-history entry will be added if opening quantity is greater than zero.')
            detail.configure(state='normal'); detail.delete('1.0','end'); detail.insert('1.0',text); detail.configure(state='disabled')
        tree.bind('<<TreeviewSelect>>',details)
        def render():
            tree.delete(*tree.get_children())
            invalid=sum(bool(r['errors']) for r in rows)
            for i,r in enumerate(rows):
                v=r['values']; status=r['errors'][0] if r['errors'] else 'Ready'
                tree.insert('','end',iid=str(i),values=(r['row'],v['sku'],v['name'],v['category'],v['price'],v['quantity'],v['reorder_level'],status),tags=('empty' if r['errors'] else 'completed',))
            summary.configure(text=f'{len(rows)} rows  /  {len(rows)-invalid} ready  /  {invalid} need fixing',fg='#C3434E' if invalid else '#228363')
            import_button.state(['disabled'] if invalid or not rows else ['!disabled'])
            if invalid:
                tree.selection_set(str(next(i for i,r in enumerate(rows) if r['errors'])))
            details()
        def load(path=None):
            if path is None: path=filedialog.askopenfilename(parent=dialog,title='Choose product CSV',filetypes=[('CSV files','*.csv')])
            if not path: return
            rows.clear(); tree.delete(*tree.get_children()); details(); import_button.state(['disabled'])
            filename.configure(text=Path(path).name[:50])
            try:
                rows.extend(self.db.preview_product_import(path)); render()
            except (ValueError,OSError,sqlite3.Error) as error:
                summary.configure(text='File could not be validated. Nothing has been imported.',fg='#C3434E'); self.notify_error(error,dialog)
        def template():
            path=filedialog.asksaveasfilename(parent=dialog,initialfile='product_import_template.csv',defaultextension='.csv',filetypes=[('CSV files','*.csv')])
            if path:
                try: write_template(path); self.status.set('CSV template saved')
                except OSError as error: self.notify_error(error,dialog)
        def commit():
            if not rows or any(r['errors'] for r in rows): return
            if not messagebox.askyesno('Import products',f'Add all {len(rows)} products and their opening stock?',parent=dialog): return
            try:
                count=self.db.import_products(rows)
                dialog.destroy(); self.show_page('Products'); self.status.set(f'Imported {count} products. Opening stock and activity saved.')
            except (ValueError,sqlite3.Error) as error:
                self.notify_error(error,dialog)
                rows[:]=self.db.validate_import_rows(rows); render()
        dialog.load_csv,dialog.commit_import,dialog.preview_rows,dialog.import_button=load,commit,rows,import_button
        dialog.preview_tree=tree
        return dialog
