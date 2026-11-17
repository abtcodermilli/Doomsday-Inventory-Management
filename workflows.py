"""Tkinter screens for suppliers, orders, accounts and backend activity."""
import csv
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from database import csv_safe, whole_number, price_to_paise
from cart import OrderCart
from widgets import BG, WHITE, BLUE, INK, MUTED, Card


def money(paise):
    return f'INR {paise/100:,.2f}'


class WorkflowViews:
    def notify_error(self, error, parent=None):
        messagebox.showerror('Please check these details',str(error),parent=parent or self)

    def form_dialog(self,title,specs,on_save):
        dialog=tk.Toplevel(self); dialog.title(title); dialog.configure(bg=WHITE)
        dialog.geometry(f'500x{175+len(specs)*73}'); dialog.resizable(False,False)
        dialog.transient(self); dialog.grab_set()
        form=tk.Frame(dialog,bg=WHITE,padx=28,pady=22); form.pack(fill='both',expand=True)
        self.label(form,title,20,INK,True).pack(anchor='w',pady=(0,15))
        variables={}
        for key,label,value,options in specs:
            self.label(form,label,10,MUTED).pack(anchor='w',pady=(7,5))
            variables[key]=tk.StringVar(value=value)
            if isinstance(options,list):
                entry=ttk.Combobox(form,textvariable=variables[key],values=options,state='readonly')
            else:
                entry=ttk.Entry(form,textvariable=variables[key],show='*' if options=='password' else '')
            entry.pack(fill='x')
        def save():
            try:
                on_save(**{k:v.get() for k,v in variables.items()})
                dialog.destroy(); self.status.set('Changes saved successfully'); self.show_page(self.current_page)
            except (ValueError,sqlite3.Error,OSError) as error: self.notify_error(error,dialog)
        self.button(form,'Save changes',save,True).pack(side='bottom',anchor='e',pady=(20,0))
        dialog.bind('<Escape>',lambda e:dialog.destroy())
        dialog.form_variables=variables; dialog.save_form=save
        return dialog

    def suppliers_page(self):
        self.heading('Suppliers','Keep supplier contacts together and link them to your purchase orders.')
        toolbar=tk.Frame(self.content,bg=BG); toolbar.pack(fill='x',pady=(0,16))
        search=tk.StringVar()
        ttk.Entry(toolbar,textvariable=search,width=32).pack(side='left')
        self.label(toolbar,'Search supplier / contact',9,MUTED).pack(side='left',padx=12)
        self.button(toolbar,'+ Add supplier',self.supplier_dialog,True).pack(side='right')
        panel=self.panel(self.content); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('name','Supplier',220),('contact','Contact person',180),('phone','Phone',150),('email','Email',240)])
        footer=tk.Frame(self.content,bg=BG); footer.pack(side='bottom',fill='x',pady=(15,0),before=panel)
        def edit():
            selection=tree.selection()
            if not selection: return messagebox.showinfo('Select a supplier','Click a supplier row first.',parent=self)
            self.supplier_dialog(int(selection[0]))
        self.button(footer,'Edit selected',edit).pack(side='left')
        count=self.label(footer,'',10,MUTED); count.pack(side='right')
        def refresh(*args):
            tree.delete(*tree.get_children()); rows=self.db.suppliers(search.get())
            for i,s in enumerate(rows): tree.insert('','end',iid=str(s['id']),values=(s['name'],s['contact'],s['phone'],s['email']),tags=('alt' if i%2 else '',))
            count.configure(text=f'{len(rows)} suppliers')
        search.trace_add('write',refresh); tree.bind('<Double-1>',lambda e:edit()); refresh()

    def supplier_dialog(self,supplier_id=None):
        row=next((s for s in self.db.suppliers() if s['id']==supplier_id),None)
        specs=[(key,title,row[key] if row else '',None) for key,title in
               [('name','Supplier name *'),('contact','Contact person'),('phone','Phone'),('email','Email')]]
        return self.form_dialog('Edit supplier' if row else 'Add supplier',specs,
                                lambda **values:self.db.save_supplier(**values,supplier_id=supplier_id))

    def orders_page(self,kind):
        purchase=kind=='PURCHASE'
        self.heading('Purchase orders' if purchase else 'Sales & receipts',
                     'Create a purchase, then receive it to update inventory.' if purchase else 'Record a sale, update stock automatically and save a receipt.')
        orders=self.db.orders(kind)
        stats=tk.Frame(self.content,bg=BG); stats.pack(fill='x',pady=(0,17))
        specs=[('Open orders' if purchase else 'Completed sales',str(sum(r['status']==('PENDING' if purchase else 'COMPLETED') for r in orders))),
               ('Received value' if purchase else 'Sales value',money(sum(r['total_paise'] for r in orders if r['status']=='COMPLETED'))),
               ('Total records',str(len(orders)))]
        for i,(label,value) in enumerate(specs):
            stats.columnconfigure(i,weight=1,uniform='orderstat')
            card=Card(stats,height=85,padding=13); card.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 7,0 if i==2 else 7))
            self.label(card.body,label,9,MUTED).pack(anchor='w')
            self.label(card.body,value,19,INK,True).pack(anchor='w',pady=(4,0))
        bar=tk.Frame(self.content,bg=BG); bar.pack(fill='x',pady=(0,13))
        search,status=tk.StringVar(),tk.StringVar(value='All statuses')
        ttk.Entry(bar,textvariable=search,width=24).pack(side='left')
        combo=ttk.Combobox(bar,textvariable=status,values=['All statuses','PENDING','COMPLETED','CANCELLED'],state='readonly',width=17)
        combo.pack(side='left',padx=10)
        self.button(bar,'+ New purchase' if purchase else '+ New sale',lambda:self.order_dialog(kind),True).pack(side='right')
        panel=self.panel(self.content); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('number','Order no.',110),('date','Created',165),('partner','Supplier' if purchase else 'Customer',210),
                               ('total','Total (INR)',140),('status','Status',140)])
        def selected():
            items=tree.selection()
            if not items:
                messagebox.showinfo('Select an order','Click an order row first.',parent=self); return None
            return int(items[0])
        def details():
            order_id=selected()
            if order_id is not None: self.order_detail_dialog(order_id)
        def receive():
            order_id=selected()
            if order_id is None: return
            if not messagebox.askyesno('Receive purchase','Receive all items on this order and add them to inventory?',parent=self): return
            try:
                self.db.receive_purchase(order_id); self.status.set('Purchase received; inventory and history updated'); self.show_page('Purchasing')
            except (ValueError,sqlite3.Error) as error: self.notify_error(error)
        def cancel():
            order_id=selected()
            if order_id is None: return
            text='Cancel this pending purchase? Stock will not change.' if purchase else 'Void this sale? Its stock will be restored and its value excluded from sales totals.'
            if not messagebox.askyesno('Confirm cancellation',text,parent=self): return
            try:
                self.db.cancel_order(order_id); self.status.set('Order cancelled successfully'); self.show_page(self.current_page)
            except (ValueError,sqlite3.Error) as error: self.notify_error(error)
        footer=tk.Frame(self.content,bg=BG); footer.pack(side='bottom',fill='x',pady=(14,0),before=panel)
        self.button(footer,'View details / receipt',details).pack(side='left')
        if purchase: self.button(footer,'Receive selected',receive,True).pack(side='left',padx=8)
        if self.db.user['role']=='Admin': self.button(footer,'Cancel purchase' if purchase else 'Void sale',cancel).pack(side='left',padx=8 if not purchase else 0)
        visible=[]
        self.button(footer,'Export CSV',lambda:self.export_orders(visible)).pack(side='right')
        def refresh(*args):
            tree.delete(*tree.get_children()); visible.clear()
            for r in orders:
                number=self.db.order_number(r)
                if status.get()!='All statuses' and r['status']!=status.get(): continue
                if search.get().lower() not in (number+' '+r['partner']).lower(): continue
                visible.append(r)
                tree.insert('','end',iid=str(r['id']),values=(number,r['created_at'],r['partner'],f'{r["total_paise"]/100:,.2f}',r['status']),tags=(r['status'].lower(),))
        search.trace_add('write',refresh); combo.bind('<<ComboboxSelected>>',refresh)
        tree.bind('<Double-1>',lambda e:details()); refresh()
        self.order_tree=tree

    def order_dialog(self,kind):
        purchase=kind=='PURCHASE'
        if purchase and self.db.user['role']!='Admin': return self.notify_error(ValueError('Only an Admin can create purchases.'))
        products=self.db.products()
        if not products: return messagebox.showinfo('Add products first','Create at least one product before recording an order.',parent=self)
        suppliers=self.db.suppliers() if purchase else []
        if purchase and not suppliers: return messagebox.showinfo('Add a supplier first','Open Suppliers and add a supplier before creating a purchase.',parent=self)
        dialog=tk.Toplevel(self); dialog.title('New purchase order' if purchase else 'New sale')
        dialog.configure(bg=BG); dialog.geometry('900x700'); dialog.minsize(860,660); dialog.transient(self); dialog.grab_set()
        frame=tk.Frame(dialog,bg=BG,padx=24,pady=20); frame.pack(fill='both',expand=True)
        self.label(frame,'New purchase order' if purchase else 'Record a sale',23,INK,True).pack(anchor='w')
        self.label(frame,'Stock increases only when you receive this order.' if purchase else 'Completing this sale reduces inventory immediately.',10,MUTED).pack(anchor='w',pady=(6,18))
        customer=tk.StringVar(value='' if purchase else 'Walk-in customer')
        names={s['name']:s['id'] for s in suppliers}
        row=tk.Frame(frame,bg=BG); row.pack(fill='x',pady=(0,17))
        self.label(row,'Supplier *' if purchase else 'Customer *',10,INK,True).pack(side='left',padx=(0,12))
        if purchase:
            chooser=ttk.Combobox(row,textvariable=customer,values=list(names),state='readonly',width=32); chooser.pack(side='left')
        else: ttk.Entry(row,textvariable=customer,width=32).pack(side='left')
        picker=self.panel(frame); picker.pack(fill='x',pady=(0,16))
        product_map={f'{p["sku"]} | {p["name"]}':p for p in products}
        product_var,quantity,price=tk.StringVar(),tk.StringVar(value='1'),tk.StringVar(value='0.00')
        picker.columnconfigure(0,weight=1)
        for col,title in enumerate(['Product','Quantity','Unit cost (INR)' if purchase else 'Unit price (INR)']):
            self.label(picker,title,9,MUTED).grid(row=0,column=col,sticky='w',padx=12,pady=(12,5))
        product_box=ttk.Combobox(picker,textvariable=product_var,values=list(product_map),state='readonly',width=32)
        product_box.grid(row=1,column=0,sticky='ew',padx=12,pady=(0,6))
        ttk.Entry(picker,textvariable=quantity,width=8).grid(row=1,column=1,padx=6)
        ttk.Entry(picker,textvariable=price,width=12).grid(row=1,column=2,padx=6)
        available=self.label(picker,'Select a product to see available stock.',9,MUTED)
        available.grid(row=2,column=0,columnspan=3,sticky='w',padx=12,pady=(0,12))
        def choose(e=None):
            p=product_map.get(product_var.get())
            if p:
                price.set(f'{p["price_paise"]/100:.2f}'); available.configure(text=f'Available: {p["quantity"]} units | SKU: {p["sku"]}')
        product_box.bind('<<ComboboxSelected>>',choose)
        cart_model=OrderCart(self.db,kind)
        cart=cart_model.items
        self.label(frame,'Double-click Qty or Price to edit. Press Enter to save or Esc to cancel.',9,BLUE).pack(anchor='w',pady=(0,8))
        panel=self.panel(frame); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('sku','SKU',100),('name','Product',230),('qty','Qty',70),('price','Price (INR)',130),('total','Total (INR)',150)],4)
        footer=tk.Frame(frame,bg=BG); footer.pack(side='bottom',fill='x',pady=(15,0),before=panel)
        note=tk.StringVar()
        self.label(footer,'Note / reference (optional)',9,MUTED).pack(anchor='w')
        ttk.Entry(footer,textvariable=note).pack(fill='x',pady=(4,12))
        actions=tk.Frame(footer,bg=BG); actions.pack(fill='x')
        total_label=self.label(actions,'Total  INR 0.00',15,INK,True); total_label.pack(side='left')
        def refresh():
            tree.delete(*tree.get_children())
            for line in cart:
                p=next(p for p in products if p['id']==line['product_id']); cents=price_to_paise(line['price'])
                tree.insert('','end',iid=str(p['id']),values=(p['sku'],p['name'],line['quantity'],f'{cents/100:.2f}',f'{cents*line["quantity"]/100:.2f}'))
            total_label.configure(text='Total  '+money(cart_model.total_paise))
        def add():
            try:
                p=product_map.get(product_var.get())
                if p is None: raise ValueError('Select a product.')
                if not commit_editor(): return
                cart_model.add(p['id'],quantity.get(),price.get())
                refresh()
            except ValueError as error: self.notify_error(error,dialog)
        self.button(picker,'Add item',add,True).grid(row=1,column=3,padx=(6,12))
        def remove():
            if tree.selection():
                selected=int(tree.selection()[0]); cancel_editor(); cart_model.remove(selected); refresh()
        self.button(actions,'Remove item',remove).pack(side='right',padx=(8,0))
        editor=[None]
        def cancel_editor(event=None):
            current=editor[0]; editor[0]=None
            if current is not None: current['entry'].destroy()
        def commit_editor(event=None):
            current=editor[0]
            if current is None: return True
            try:
                item=next(line for line in cart if line['product_id']==current['id'])
                qty=current['entry'].get() if current['column']=='qty' else item['quantity']
                unit_price=current['entry'].get() if current['column']=='price' else item['price']
                cart_model.update(current['id'],qty,unit_price)
                selected=str(current['id']); cancel_editor(); refresh(); tree.selection_set(selected)
                return True
            except (ValueError,sqlite3.Error) as error:
                self.notify_error(error,dialog)
                if editor[0]: editor[0]['entry'].focus_set()
                return False
        def begin_edit(product_id,column='qty'):
            if column not in ('qty','price') or not commit_editor(): return
            item=next((line for line in cart if line['product_id']==int(product_id)),None)
            if item is None: return
            tree.see(str(product_id)); dialog.update_idletasks()
            box=tree.bbox(str(product_id),column)
            if not box: return
            entry=ttk.Entry(tree,style='Compact.TEntry')
            entry.insert(0,str(item['quantity'] if column=='qty' else item['price']))
            entry.place(x=box[0],y=box[1],width=box[2],height=box[3])
            entry.focus_set(); entry.selection_range(0,'end')
            editor[0]={'entry':entry,'id':int(product_id),'column':column}
            entry.bind('<Return>',lambda e:commit_editor())
            entry.bind('<Escape>',cancel_editor)
        def double_click(event):
            row_id=tree.identify_row(event.y)
            column={'#3':'qty','#4':'price'}.get(tree.identify_column(event.x))
            if row_id and column: begin_edit(int(row_id),column)
        tree.bind('<Double-1>',double_click)
        tree.bind('<MouseWheel>',cancel_editor,add='+')
        def save():
            try:
                if not commit_editor(): return
                order_id=self.db.create_order(kind,customer.get(),cart,supplier_id=names.get(customer.get()) if purchase else None,note=note.get())
                dialog.destroy(); self.status.set('Purchase created; awaiting delivery' if purchase else 'Sale completed; stock and history updated')
                self.show_page('Purchasing' if purchase else 'Sales'); self.order_detail_dialog(order_id)
            except (ValueError,sqlite3.Error) as error: self.notify_error(error,dialog)
        self.button(actions,'Create purchase' if purchase else 'Complete sale',save,True).pack(side='right')
        dialog.order_fields={'partner':customer,'product':product_var,'quantity':quantity,'price':price,'note':note}
        dialog.add_item=add; dialog.save_order=save; dialog.choose_product=choose
        dialog.cart_model=cart_model; dialog.cart_tree=tree; dialog.begin_cart_edit=begin_edit
        dialog.commit_cart_edit=commit_editor; dialog.cart_editor=editor; dialog.cart_total_label=total_label
        return dialog

    def order_detail_dialog(self,order_id):
        order,items=self.db.order_details(order_id)
        dialog=tk.Toplevel(self); dialog.title(self.db.order_number(order)); dialog.configure(bg=WHITE)
        dialog.geometry('680x590'); dialog.transient(self)
        frame=tk.Frame(dialog,bg=WHITE,padx=25,pady=20); frame.pack(fill='both',expand=True)
        self.label(frame,self.db.order_number(order),24,INK,True).pack(anchor='w')
        self.label(frame,order['status']+'  |  '+order['partner'],11,BLUE).pack(anchor='w',pady=(5,15))
        actions=tk.Frame(frame,bg=WHITE); actions.pack(side='bottom',fill='x',pady=(15,0))
        text=tk.Text(frame,wrap='word',bg='#F8FAFD',fg=INK,font=(self.font,11),relief='flat',padx=16,pady=16)
        scroll=ttk.Scrollbar(frame,command=text.yview); scroll.pack(side='right',fill='y')
        text.configure(yscrollcommand=scroll.set); text.pack(fill='both',expand=True)
        receipt=self.db.receipt_text(order_id); text.insert('1.0',receipt); text.configure(state='disabled')
        def save():
            path=filedialog.asksaveasfilename(parent=dialog,defaultextension='.txt',initialfile=self.db.order_number(order)+'.txt',filetypes=[('Text receipt','*.txt')])
            if path:
                try: Path(path).write_text(receipt,encoding='utf-8'); self.status.set('Receipt saved successfully')
                except OSError as error: self.notify_error(error,dialog)
        self.button(actions,'Save receipt',save,True).pack(side='right')
        self.button(actions,'Close',dialog.destroy).pack(side='right',padx=8)
        return dialog

    def export_orders(self,rows):
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',initialfile='doomsday_orders.csv',filetypes=[('CSV','*.csv')])
        if not path: return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as file:
                writer=csv.writer(file); writer.writerow(['Order','Type','Partner','Date','Status','Total INR'])
                for r in rows: writer.writerow([self.db.order_number(r),r['kind'],csv_safe(r['partner']),r['created_at'],r['status'],f'{r["total_paise"]/100:.2f}'])
            self.status.set('Order report exported successfully')
        except OSError as error: self.notify_error(error)

    def activity_page(self):
        self.heading('Activity log','See who changed what, and when. The latest 500 events are shown.')
        panel=self.panel(self.content); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('time','Date & time',175),('user','Team member',175),('action','Action',190),('detail','Details',320)])
        for i,row in enumerate(self.db.activities(500)):
            tree.insert('','end',values=(row['created_at'],row['full_name'],row['action'],row['detail']),tags=('alt' if i%2 else '',))

    def accounts_page(self):
        admin=self.db.user['role']=='Admin'
        self.heading('Accounts & database' if admin else 'My account',
                     'Manage workspace access and inspect the database behind the application.' if admin else 'Manage your sign-in password.')
        bar=tk.Frame(self.content,bg=BG); bar.pack(fill='x',pady=(0,18))
        if admin: self.button(bar,'+ Add account',self.account_dialog,True).pack(side='left')
        self.button(bar,'Change my password',self.password_dialog).pack(side='left',padx=(10 if admin else 0,0))
        if not admin:
            self.label(self.content,self.db.user['full_name']+' / Staff',14,INK,True).pack(anchor='w'); return
        info=Card(self.content,height=125,padding=18); info.pack(fill='x',pady=(0,18))
        self.label(info.body,'SQLite backend  /  Connected',13,BLUE,True).pack(anchor='w')
        self.label(info.body,'7 related tables | Persistent local database | Password hashes | Transactional orders',10,MUTED).pack(anchor='w',pady=(6,4))
        counts=self.db.database_info()
        self.label(info.body,'   '.join(f'{name}: {count}' for name,count in counts),9,INK,wraplength=820,justify='left').pack(anchor='w')
        self.label(self.content,'Workspace accounts',13,INK,True).pack(anchor='w',pady=(0,10))
        panel=self.panel(self.content); panel.pack(fill='both',expand=True)
        tree=self.table(panel,[('name','Full name',270),('username','Username',220),('role','Role',160)],4)
        for user in self.db.users(): tree.insert('','end',values=(user['full_name'],user['username'],user['role']))
        self.label(self.content,'Admin: manage inventory, purchases and users. Staff: record sales and view inventory/reports.',9,MUTED,wraplength=820,justify='left').pack(side='bottom',anchor='w',pady=(12,0),before=panel)

    def account_dialog(self):
        return self.form_dialog('Create account',[
            ('full_name','Full name *','',None),('username','Username *','',None),
            ('password','Password (8+ characters) *','','password'),('role','Access level','Staff',['Staff','Admin'])],self.db.add_user)

    def password_dialog(self):
        return self.form_dialog('Change password',[
            ('old_password','Current password','','password'),('new_password','New password (8+ characters)','','password')],self.db.change_password)
