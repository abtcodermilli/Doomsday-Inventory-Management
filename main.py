"""Doomsday Inventory. Run: python3 main.py"""
import sqlite3
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk, font

from services import InventoryService
from workflows import WorkflowViews
from enhancements import EnhancementViews
import widgets
from widgets import BLUE, NAVY, BG, WHITE, INK, MUTED, LINE, Card, NavItem, icon, rounded, warehouse

TEAM = [('Aditya Malik','RA2511003012354'), ('Shashank Singh Solanki','RA2511003012371'),
        ('Ankur Bikram Thapa','RA2511003012373')]


def money(paise):
    return f'INR {paise / 100:,.2f}'


class InventoryApp(EnhancementViews, WorkflowViews, tk.Tk):
    def __init__(self, database=None):
        super().__init__()
        self.db = database if database is not None else InventoryService()
        self.title('Doomsday | Inventory & Operations')
        self.geometry(f'{max(1120,min(1280,self.winfo_screenwidth()-80))}x{max(780,min(850,self.winfo_screenheight()-70))}')
        self.minsize(1120,780)
        self.configure(bg=BG)
        self.protocol('WM_DELETE_WINDOW',self.close)
        families=font.families()
        self.font = 'Helvetica Neue' if sys.platform=='darwin' else 'DejaVu Sans' if 'DejaVu Sans' in families else 'Arial'
        widgets.FONT=self.font
        self.current_page='Dashboard'
        self.status=tk.StringVar(value='All changes saved locally')
        self.setup_styles()
        if self.db.user:
            self.open_workspace()
        else:
            self.login_screen()

    def setup_styles(self):
        self.option_add('*Font',(self.font,10))
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('TButton',font=(self.font,10,'bold'),padding=(15,10),background=WHITE,
                        foreground=INK,bordercolor=LINE,lightcolor=WHITE,darkcolor=WHITE,relief='flat')
        style.map('TButton',background=[('active','#EAF1FF')])
        style.configure('Primary.TButton',background=BLUE,foreground=WHITE,bordercolor=BLUE,lightcolor=BLUE,darkcolor=BLUE)
        style.map('Primary.TButton',background=[('active','#1D4ED8')],foreground=[('disabled','#B6C7E7'),('active',WHITE)])
        style.configure('Danger.TButton',foreground='#C3434E')
        style.configure('TEntry',padding=9,fieldbackground=WHITE,bordercolor=LINE,lightcolor=WHITE,darkcolor=WHITE)
        style.configure('TCombobox',padding=8,fieldbackground=WHITE,bordercolor=LINE,arrowcolor=MUTED)
        style.map('TCombobox',fieldbackground=[('readonly',WHITE)],selectbackground=[('readonly',WHITE)],selectforeground=[('readonly',INK)])
        style.configure('Compact.TEntry',padding=5)
        style.configure('Compact.TCombobox',padding=5)
        style.configure('Treeview',background=WHITE,fieldbackground=WHITE,foreground=INK,rowheight=40,
                        borderwidth=0,font=(self.font,10),lightcolor=WHITE,darkcolor=WHITE)
        style.configure('Treeview.Heading',background='#F6F8FC',foreground=MUTED,padding=(10,11),
                        font=(self.font,9,'bold'),borderwidth=0,relief='flat')
        style.map('Treeview',background=[('selected','#E5EEFF')],foreground=[('selected','#174EB8')])
        style.configure('TCheckbutton',background=WHITE,foreground=INK)
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(15,10), background='#E9EFF9', foreground=MUTED, font=(self.font,10,'bold'))
        style.map('TNotebook.Tab', background=[('selected',BLUE)], foreground=[('selected',WHITE)])
        style.configure('Vertical.TScrollbar',background='#CCD8E9',troughcolor='#F7F9FC',borderwidth=0,arrowsize=12)

    def label(self,parent,text,size=11,color=INK,bold=False,bg=None,**kwargs):
        return tk.Label(parent,text=text,bg=bg or parent.cget('bg'),fg=color,
                        font=(self.font,size,'bold' if bold else 'normal'),**kwargs)

    def button(self,parent,text,command,primary=False,**kwargs):
        return ttk.Button(parent,text=text,command=command,style='Primary.TButton' if primary else 'TButton',**kwargs)

    def panel(self,parent,**kwargs):
        return tk.Frame(parent,bg=WHITE,highlightbackground=LINE,highlightthickness=1,**kwargs)

    def clear_root(self):
        for child in self.winfo_children(): child.destroy()

    def login_screen(self):
        self.clear_root()
        setup=self.db.needs_setup()
        hero=tk.Canvas(self,bg=NAVY,highlightthickness=0)
        hero.place(relx=0,rely=0,relwidth=.48,relheight=1)
        def draw(event):
            hero.delete('all'); w,h=event.width,event.height
            hero.create_oval(w-260,-180,w+330,420,fill='#153968',outline='')
            hero.create_oval(-220,h-260,380,h+310,fill='#173E72',outline='')
            hero.create_text(48,62,text='D /  DOOMSDAY',anchor='w',fill=WHITE,font=(self.font,20,'bold'))
            hero.create_text(48,150,text='A little order.\nA lot more control.',anchor='nw',fill=WHITE,font=(self.font,32,'bold'))
            hero.create_text(48,265,text='Your products, purchases and sales.\nOne organised workspace.',anchor='nw',fill='#AEC7E9',font=(self.font,13),width=w-85)
            warehouse(hero,70,420,1.3)
            hero.create_text(48,h-66,text='INVENTORY & OPERATIONS  /  TEAM DOOMSDAY',anchor='w',fill='#A5C0E4',font=(self.font,9,'bold'))
        hero.bind('<Configure>',draw)
        side=tk.Frame(self,bg=WHITE)
        side.place(relx=.48,rely=0,relwidth=.52,relheight=1)
        form=tk.Frame(side,bg=WHITE)
        form.place(relx=.5,rely=.5,anchor='center',width=390)
        self.label(form,'LET\'S GET ORGANISED',9,BLUE,True).pack(anchor='w',pady=(0,12))
        self.label(form,'Create your workspace' if setup else 'Welcome back.',24,INK,True).pack(anchor='w')
        self.label(form,'Set up your first administrator account.' if setup else 'Sign in to manage your inventory.',11,MUTED).pack(anchor='w',pady=(8,24))
        variables={}
        specs=[('full_name','Your full name')] if setup else []
        specs += [('username','Username'),('password','Password')]
        if setup: specs += [('confirm','Confirm password')]
        for key,title in specs:
            self.label(form,title,10,INK,True).pack(anchor='w',pady=(8,6))
            variables[key]=tk.StringVar()
            ttk.Entry(form,textvariable=variables[key],show='*' if key in ('password','confirm') else '').pack(fill='x')
        include_demo=tk.BooleanVar(value=True)
        if setup and not self.db.products():
            ttk.Checkbutton(form,text='Start with sample products and orders',variable=include_demo).pack(anchor='w',pady=(17,2))
        error_label=self.label(form,'',10,'#C3434E',wraplength=380,justify='left')
        error_label.pack(anchor='w',pady=(10,5))
        def submit():
            try:
                values={k:v.get() for k,v in variables.items()}
                if setup:
                    if values['password']!=values['confirm']: raise ValueError('The two passwords do not match.')
                    self.db.setup_admin(values['username'],values['full_name'],values['password'])
                    if include_demo.get() and not self.db.products(): self.db.load_demo()
                else: self.db.login(values['username'],values['password'])
                self.open_workspace()
            except (ValueError,sqlite3.Error) as error: error_label.configure(text=str(error))
        self.button(form,'Create workspace' if setup else 'Sign in to workspace',submit,True).pack(fill='x',pady=(7,15))
        self.label(form,'Passwords are stored as salted hashes.\nYour records stay on this computer.',10,MUTED,justify='left').pack(anchor='w')
        for child in form.winfo_children():
            if isinstance(child,ttk.Entry): child.bind('<Return>',lambda e:submit())
        self.auth_variables=variables
        self.auth_submit=submit

    def open_workspace(self):
        self.clear_root(); self.build_shell(); self.show_page('Dashboard')

    def build_shell(self):
        sidebar=tk.Frame(self,bg=NAVY,width=210)
        sidebar.pack(side='left',fill='y'); sidebar.pack_propagate(False)
        brand=tk.Canvas(sidebar,height=88,bg=NAVY,highlightthickness=0)
        brand.pack(fill='x')
        rounded(brand,21,25,58,62,10,fill=BLUE,outline='')
        brand.create_text(40,44,text='D',font=(self.font,21,'bold'),fill=WHITE)
        brand.create_text(70,37,text='DOOMSDAY',font=(self.font,13,'bold'),fill=WHITE,anchor='w')
        brand.create_text(70,56,text='Inventory & operations',font=(self.font,8),fill='#A4BBD9',anchor='w')
        self.label(sidebar,'WORKSPACE',8,'#6F91BA',True).pack(anchor='w',padx=24,pady=(15,10))
        self.nav_buttons={}
        pages=['Dashboard','Products','Sales']
        if self.db.user['role']=='Admin': pages += ['Purchasing','Suppliers','Stock In / Out']
        pages += ['History','Reports','Activity','Accounts']
        pages += ['Our Team']
        for page in pages:
            item=NavItem(sidebar,page,lambda p=page:self.show_page(p))
            item.pack(fill='x',padx=13,pady=2); self.nav_buttons[page]=item
        profile=tk.Frame(sidebar,bg='#173655',padx=14,pady=13)
        profile.pack(side='bottom',fill='x',padx=14,pady=17)
        self.label(profile,self.db.user['full_name'].split()[0],11,WHITE,True).pack(anchor='w')
        self.label(profile,self.db.user['role']+' account',9,'#A9C2E1').pack(anchor='w',pady=(3,8))
        logout=tk.Label(profile,text='Sign out  >',bg='#173655',fg='#92BDFF',cursor='hand2',font=(self.font,10))
        logout.pack(anchor='w'); logout.bind('<Button-1>',lambda e:self.sign_out())
        workspace=tk.Frame(self,bg=BG); workspace.pack(side='left',fill='both',expand=True)
        top=tk.Frame(workspace,bg=WHITE,height=68); top.pack(fill='x'); top.pack_propagate(False)
        self.breadcrumb=self.label(top,'Workspace / Overview',10,MUTED)
        self.breadcrumb.pack(side='left',padx=28)
        self.label(top,datetime.now().strftime('%a, %d %b %Y'),10,MUTED).pack(side='right',padx=26)
        self.label(top,'LOCAL WORKSPACE',8,BLUE,True,bg='#EAF1FF',padx=12,pady=7).pack(side='right')
        bottom=tk.Frame(workspace,bg=BG); bottom.pack(side='bottom',fill='x',padx=28,pady=(0,12))
        tk.Label(bottom,textvariable=self.status,bg=BG,fg='#65806F',font=(self.font,9),anchor='w').pack(side='left')
        self.label(bottom,'Doomsday  /  v3.0',9,MUTED).pack(side='right')
        self.content=tk.Frame(workspace,bg=BG)
        self.content.pack(fill='both',expand=True,padx=28,pady=22)

    def sign_out(self):
        self.db.logout(); self.login_screen()

    def show_page(self,page):
        if page not in self.nav_buttons: return
        self.current_page=page
        for child in self.content.winfo_children(): child.destroy()
        for name,item in self.nav_buttons.items(): item.select(name==page)
        self.breadcrumb.configure(text='Workspace  /  '+page)
        pages={'Dashboard':self.dashboard,'Products':self.products_page,'Stock In / Out':self.stock_page,
               'History':self.history_page,'Reports':self.reports_page,'Our Team':self.team_page,
               'Suppliers':self.suppliers_page,'Purchasing':lambda:self.orders_page('PURCHASE'),
               'Sales':lambda:self.orders_page('SALE'),'Activity':self.activity_page,'Accounts':self.accounts_page}
        pages[page]()

    def heading(self,title,subtitle):
        self.label(self.content,title,24,INK,True).pack(anchor='w')
        self.label(self.content,subtitle,10,MUTED).pack(anchor='w',pady=(5,18))

    def table(self,parent,columns,height=7):
        box=tk.Frame(parent,bg=WHITE); box.pack(fill='both',expand=True)
        tree=ttk.Treeview(box,columns=[c[0] for c in columns],show='headings',height=height,selectmode='browse')
        for key,title,width in columns:
            tree.heading(key,text=title.upper(),anchor='w'); tree.column(key,width=width,minwidth=65,anchor='w')
        vertical=ttk.Scrollbar(box,orient='vertical',command=tree.yview)
        horizontal=ttk.Scrollbar(box,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        tree.grid(row=0,column=0,sticky='nsew'); vertical.grid(row=0,column=1,sticky='ns'); horizontal.grid(row=1,column=0,sticky='ew')
        box.rowconfigure(0,weight=1); box.columnconfigure(0,weight=1)
        tree.tag_configure('low',foreground='#A56A13',background='#FFF9EB')
        tree.tag_configure('empty',foreground='#C04B59',background='#FFF3F4')
        tree.tag_configure('alt',background='#FAFBFE')
        tree.tag_configure('completed',foreground='#228363')
        tree.tag_configure('pending',foreground='#AE781C',background='#FFFAEE')
        tree.tag_configure('cancelled',foreground='#B45A63')
        return tree

    def dashboard(self):
        scroll = tk.Canvas(self.content, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=scroll.yview)
        scrollbar.pack(side="right", fill="y")
        scroll.pack(side="left", fill="both", expand=True)
        scroll.configure(yscrollcommand=scrollbar.set)
        area = tk.Frame(scroll, bg=BG)
        window = scroll.create_window(0, 0, anchor="nw", window=area)
        area.bind("<Configure>", lambda e: scroll.configure(scrollregion=scroll.bbox("all")))
        def fit(event):
            scroll.itemconfigure(window, width=event.width)
            scroll.configure(scrollregion=scroll.bbox("all"))
        scroll.bind("<Configure>", fit)
        bar=tk.Frame(area,bg=BG); bar.pack(fill='x',pady=(0,12))
        self.label(bar,'Overview',24,INK,True).pack(side='left')
        self.button(bar,'+ New sale',lambda:self.order_dialog('SALE'),True).pack(side='right')
        if self.db.user['role']=='Admin': self.button(bar,'+ Add product',self.product_dialog).pack(side='right',padx=10)
        hero=tk.Canvas(area,height=100,bg=BG,highlightthickness=0)
        hero.pack(fill='x',pady=(0,12))
        def draw_hero(e):
            hero.delete('all'); rounded(hero,0,0,e.width,100,16,fill='#1E55BD',outline='')
            hero.create_oval(e.width-240,-110,e.width+60,190,fill='#2A67CE',outline='')
            hero.create_text(24,27,text='YOUR INVENTORY, IN FOCUS',anchor='w',fill='#BBD4FF',font=(self.font,8,'bold'))
            hero.create_text(24,56,text='Ready for a productive day, '+self.db.user['full_name'].split()[0]+'?',anchor='w',fill=WHITE,font=(self.font,18,'bold'))
            hero.create_text(24,86,text='Track what comes in. Know what goes out. Keep every record.',anchor='w',fill='#D8E7FF',font=(self.font,10))
            warehouse(hero,e.width-190,22,.45)
        hero.bind('<Configure>',draw_hero)
        s,b=self.db.summary(),self.db.business_summary()
        metric=tk.Frame(area,bg=BG); metric.pack(fill='x',pady=(0,12))
        metrics=[('Inventory value',money(s['value']),'Across '+str(s['products'])+' active products','Products',BLUE),
                 ('Sales today',money(b['today_sales']),'Completed sales only','Sales','#138A75'),
                 ('Low stock',str(s['low']),'Products needing attention','Stock In / Out','#D28A21'),
                 ('Open purchases',str(b['pending']),'Waiting to be received','Purchasing','#7D64C5')]
        for i,(title,value,sub,kind,color) in enumerate(metrics):
            metric.columnconfigure(i,weight=1,uniform='metric')
            card=Card(metric,height=114,padding=13); card.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==3 else 6))
            self.label(card.body,title,9,MUTED).pack(anchor='w')
            self.label(card.body,value,18 if i<2 else 23,INK,True).pack(anchor='w',pady=(4,2))
            self.label(card.body,sub,8,MUTED).pack(anchor='w')
            glyph=tk.Canvas(card.body,width=27,height=27,bg=WHITE,highlightthickness=0)
            glyph.place(relx=1,x=-29,y=0); icon(glyph,1,1,kind,color,.8)
        middle=tk.Frame(area,bg=BG); middle.pack(fill='x',pady=(0,12))
        middle.columnconfigure(0,weight=3); middle.columnconfigure(1,weight=2)
        trend=Card(middle,height=180,padding=16); trend.grid(row=0,column=0,sticky='ew',padx=(0,8))
        self.label(trend.body,'Sales this week',12,INK,True).pack(anchor='w')
        self.label(trend.body,'Completed sales value in INR',8,MUTED).pack(anchor='w',pady=(2,2))
        chart=tk.Canvas(trend.body,bg=WHITE,highlightthickness=0); chart.pack(fill='both',expand=True)
        series=self.db.weekly_sales()
        def draw_sales(e):
            chart.delete('all'); w,h=e.width,e.height; top=20; bottom=h-22; maximum=max([v for _,v in series]+[100])
            for j in range(3):
                y=top+(bottom-top)*j/2; chart.create_line(35,y,w-8,y,fill='#EEF2F8')
            gap=(w-45)/7
            for i,(day,v) in enumerate(series):
                x=40+i*gap; height=(bottom-top)*v/maximum
                rounded(chart,x,bottom-max(2,height),x+min(25,gap-10),bottom,4,fill=BLUE if i==6 else '#BBD2FF',outline='')
                chart.create_text(x+12,h-9,text=day,fill=MUTED,font=(self.font,8))
                if v: chart.create_text(x+12,bottom-height-10,text=f'{v/100:,.0f}',fill=INK,font=(self.font,8))
        chart.bind('<Configure>',draw_sales)
        stock=Card(middle,height=180,padding=16); stock.grid(row=0,column=1,sticky='ew',padx=(8,0))
        self.label(stock.body,'Stock by category',12,INK,True).pack(anchor='w')
        self.label(stock.body,f'{s["units"]:,} units on hand',8,MUTED).pack(anchor='w',pady=(2,4))
        graph=tk.Canvas(stock.body,bg=WHITE,highlightthickness=0); graph.pack(fill='both',expand=True)
        groups=self.db.category_summary()[:3]
        def draw_stock(e):
            graph.delete('all'); maximum=max([r['units'] for r in groups]+[1])
            if not groups: graph.create_text(8,40,text='Add products to see your stock mix.',anchor='w',fill=MUTED,font=(self.font,9))
            for i,row in enumerate(groups):
                y=i*38+6
                graph.create_text(0,y,text=row['category'][:24],anchor='w',fill=INK,font=(self.font,9))
                graph.create_text(e.width-1,y,text=str(row['units']),anchor='e',fill=MUTED,font=(self.font,9))
                rounded(graph,0,y+12,e.width,y+19,3,fill='#EDF2FA',outline='')
                if row['units']: rounded(graph,0,y+12,max(6,e.width*row['units']/maximum),y+19,3,fill=['#3979EC','#67A7F6','#A7C8F8'][i],outline='')
        graph.bind('<Configure>',draw_stock)
        panel=self.panel(area); panel.pack(fill='both',expand=True)
        row=tk.Frame(panel,bg=WHITE); row.pack(fill='x',padx=16,pady=10)
        self.label(row,'Restock watchlist',12,INK,True).pack(side='left')
        self.label(row,str(s['low'])+' items',9,'#AE781C',bg='#FFF5DB',padx=10,pady=4).pack(side='left',padx=12)
        if not s['products'] and self.db.user['role']=='Admin': self.button(row,'Load demo data',self.demo).pack(side='right')
        tree=self.table(panel,[('sku','SKU',110),('name','Product',260),('qty','Available',90),('level','Reorder at',100),('status','Status',130)],3)
        for p in self.db.products(low_only=True):
            tree.insert('', 'end', values=(p['sku'],p['name'],p['quantity'],p['reorder_level'],'OUT OF STOCK' if not p['quantity'] else 'LOW STOCK'),tags=('empty' if not p['quantity'] else 'low',))
        if not s['low']: tree.insert('','end',values=('','No products need restocking.','','',''))

        def wheel(event):
            units = -int(event.delta) if sys.platform == "darwin" else -int(event.delta / 120)
            scroll.yview_scroll(units, "units")
        def bind_wheel(widget):
            if not isinstance(widget, ttk.Treeview):
                widget.bind("<MouseWheel>", wheel)
                widget.bind("<Button-4>", lambda e: scroll.yview_scroll(-1, "units"))
                widget.bind("<Button-5>", lambda e: scroll.yview_scroll(1, "units"))
            for child in widget.winfo_children(): bind_wheel(child)
        bind_wheel(area)

    def products_page(self):
        self.heading("Products", "Manage your product catalogue. Double-click a row to edit its details.")
        controls = self.panel(self.content)
        controls.pack(fill="x", pady=(0, 14))
        self.search = tk.StringVar()
        self.category = tk.StringVar(value="All categories")
        self.low_only = tk.BooleanVar(value=False)
        entry = ttk.Entry(controls, textvariable=self.search, width=24)
        entry.pack(side="left", padx=(12, 8), pady=12)
        entry.insert(0, "")
        categories = ttk.Combobox(controls, textvariable=self.category, values=["All categories"] + self.db.categories(), state="readonly", width=18)
        categories.pack(side="left", padx=4)
        ttk.Checkbutton(controls, text="Low stock only", variable=self.low_only, command=self.refresh_products).pack(side="left", padx=8)
        if self.db.user["role"] == "Admin":
            self.button(controls, "+ Add", self.product_dialog, True).pack(side="right", padx=12)
        tools = tk.Frame(self.content, bg=BG)
        tools.pack(fill="x", pady=(0, 10))
        self.label(tools, "Search name, SKU or supplier", 10, MUTED).pack(side="left")
        if self.db.user["role"] == "Admin":
            self.button(tools, "Import CSV", self.csv_import_dialog).pack(side="right")
            self.button(tools, "Archived products", self.archives_dialog).pack(side="right", padx=8)
        panel = self.panel(self.content)
        panel.pack(fill="both", expand=True)
        self.product_tree = self.table(panel, [("sku", "SKU", 95), ("name", "Product", 175), ("category", "Category", 110),
                                              ("price", "Price (INR)", 105), ("qty", "Quantity", 75),
                                              ("level", "Reorder at", 85), ("supplier", "Supplier", 150)], 9)
        self.product_tree.bind("<Double-1>", lambda event: self.edit_selected())
        footer = tk.Frame(self.content, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(14, 0), before=panel)
        if self.db.user["role"] == "Admin":
            self.button(footer, "Edit selected", self.edit_selected).pack(side="left")
            ttk.Button(footer, text="Archive selected", style="Danger.TButton", command=self.archive_selected).pack(side="left", padx=8)
        self.button(footer, "Export CSV", lambda: self.export("products")).pack(side="right")
        self.product_count = self.label(footer, "", 10, MUTED)
        self.product_count.pack(side="right", padx=12)
        self.search.trace_add("write", lambda *args: self.refresh_products())
        categories.bind("<<ComboboxSelected>>", lambda event: self.refresh_products())
        self.refresh_products()

    def refresh_products(self):
        self.product_tree.delete(*self.product_tree.get_children())
        self.product_rows = self.db.products(self.search.get(), self.category.get(), self.low_only.get())
        for i, p in enumerate(self.product_rows):
            tag = "empty" if p["quantity"] == 0 else "low" if p["quantity"] <= p["reorder_level"] else "alt" if i % 2 else ""
            self.product_tree.insert("", "end", iid=str(p["id"]), values=(p["sku"], p["name"], p["category"],
                f"{p['price_paise']/100:,.2f}", p["quantity"], p["reorder_level"], p["supplier"]), tags=(tag,))
        self.product_count.configure(text=f"{len(self.product_rows)} product(s)")

    def selected_id(self):
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showinfo("Select a product", "Click a product row first.", parent=self)
            return None
        return int(selection[0])

    def edit_selected(self):
        product_id = self.selected_id()
        if product_id is not None:
            self.product_dialog(product_id)

    def product_dialog(self, product_id=None):
        if self.db.user["role"] != "Admin":
            return messagebox.showinfo("Read-only catalogue", "Ask an Admin to change product details.", parent=self)
        product = self.db.get_product(product_id) if product_id is not None else None
        dialog = tk.Toplevel(self)
        dialog.title("Edit product" if product else "Add product")
        dialog.configure(bg=WHITE)
        dialog.geometry("490x650")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=WHITE, padx=28, pady=22)
        frame.pack(fill="both", expand=True)
        self.label(frame, "Edit product" if product else "Add a new product", 21, INK, True).pack(anchor="w", pady=(0, 7))
        self.label(frame, "Enter product details below. Prices are in INR.", 10, MUTED).pack(anchor="w", pady=(0, 14))
        fields = [("sku", "SKU *"), ("name", "Product name *"), ("category", "Category *"),
                  ("supplier", "Supplier (optional)"), ("price", "Unit price (INR) *"),
                  ("quantity", "Opening quantity *"), ("reorder_level", "Reorder level *")]
        variables = {}
        for key, title in fields:
            if product and key == "quantity":
                continue
            self.label(frame, title, 10, MUTED).pack(anchor="w", pady=(4, 2))
            value = f"{product['price_paise']/100:.2f}" if product and key == "price" else product[key] if product else "0" if key in ("price", "quantity") else "5" if key == "reorder_level" else ""
            variables[key] = tk.StringVar(value=value)
            widget = ttk.Combobox(frame, textvariable=variables[key], values=self.db.categories(), style="Compact.TCombobox") if key == "category" else ttk.Entry(frame, textvariable=variables[key], style="Compact.TEntry")
            widget.pack(fill="x")
            if key == "sku":
                widget.focus_set()
        if product:
            self.label(frame, "Change quantity from the Stock In / Out page.", 10, MUTED).pack(anchor="w", pady=14)

        def save():
            try:
                values = {key: value.get() for key, value in variables.items()}
                if product:
                    self.db.update_product(product_id, **values)
                else:
                    self.db.add_product(**values)
                dialog.destroy()
                self.status.set("Product saved successfully.")
                self.show_page(self.current_page)
            except (ValueError, sqlite3.Error) as error:
                messagebox.showerror("Could not save", str(error), parent=dialog)

        actions = tk.Frame(frame, bg=WHITE)
        actions.pack(side="bottom", fill="x", pady=(16, 0))
        self.button(actions, "Save product", save, True).pack(side="right")
        self.button(actions, "Cancel", dialog.destroy).pack(side="right", padx=8)
        dialog.bind("<Escape>", lambda event: dialog.destroy())

    def archive_selected(self):
        product_id = self.selected_id()
        if product_id is None:
            return
        p = self.db.get_product(product_id)
        if messagebox.askyesno("Archive product", f"Archive {p['name']}?\n\nIts transaction history will be kept. The stock must be zero.", parent=self):
            try:
                self.db.archive_product(product_id)
                self.status.set("Product archived. Transaction history retained.")
                self.show_page("Products")
            except (ValueError, sqlite3.Error) as error:
                messagebox.showerror("Could not archive", str(error), parent=self)

    def stock_page(self):
        self.heading("Stock In / Out", "Record incoming supplies and outgoing items. Every movement is saved.")
        panel = self.panel(self.content)
        panel.pack(fill="both", expand=True)
        form = tk.Frame(panel, bg=WHITE, padx=25, pady=16)
        form.pack(side="left", fill="both", expand=True)
        self.label(form, "New stock movement", 17, INK, True).pack(anchor="w", pady=(0, 14))
        products = self.db.products()
        choices = {f"{p['sku']}  |  {p['name']}": p["id"] for p in products}
        self.stock_product = tk.StringVar()
        self.stock_kind = tk.StringVar(value="IN")
        self.stock_quantity = tk.StringVar()
        self.stock_note = tk.StringVar()
        self.label(form, "Product", 10, MUTED).pack(anchor="w", pady=(0, 5))
        combo = ttk.Combobox(form, textvariable=self.stock_product, values=list(choices), state="readonly", style="Compact.TCombobox")
        combo.pack(fill="x")
        available = self.label(form, "Select a product to see available stock.", 11, BLUE)
        available.pack(anchor="w", pady=8)

        def selection_changed(event=None):
            if self.stock_product.get() in choices:
                p = self.db.get_product(choices[self.stock_product.get()])
                available.configure(text=f"Available: {p['quantity']} units   |   Reorder level: {p['reorder_level']}")

        combo.bind("<<ComboboxSelected>>", selection_changed)
        for title, variable in [("Movement type", self.stock_kind), ("Quantity", self.stock_quantity), ("Note / reason (optional)", self.stock_note)]:
            self.label(form, title, 10, MUTED).pack(anchor="w", pady=(8, 4))
            widget = ttk.Combobox(form, textvariable=variable, values=["IN", "OUT"], state="readonly", style="Compact.TCombobox") if variable is self.stock_kind else ttk.Entry(form, textvariable=variable, style="Compact.TEntry")
            widget.pack(fill="x")

        def save():
            try:
                if self.stock_product.get() not in choices:
                    raise ValueError("Select a product first.")
                balance = self.db.change_stock(choices[self.stock_product.get()], self.stock_kind.get(), self.stock_quantity.get(), self.stock_note.get())
                self.stock_quantity.set("")
                self.stock_note.set("")
                selection_changed()
                self.status.set(f"Stock {self.stock_kind.get()} saved. New balance: {balance} units.")
                messagebox.showinfo("Movement recorded", f"Stock updated successfully.\nNew balance: {balance} units.", parent=self)
            except (ValueError, sqlite3.Error) as error:
                messagebox.showerror("Could not update stock", str(error), parent=self)

        self.stock_save = self.button(form, "Save movement", save, True)
        self.stock_save.pack(anchor="w", pady=14)
        if not products:
            self.stock_save.state(["disabled"])
            available.configure(text="Add a product on the Products page first.")
        guide = tk.Frame(panel, bg="#EAF2FF", padx=22, pady=25, width=275)
        guide.pack(side="right", fill="y", padx=(15, 0))
        self.label(guide, "Keep your stock accurate", 13, NAVY, True).pack(anchor="w", pady=(0, 20))
        self.label(guide, "STOCK IN\nNew supplies or returned items.\nAdds to the current quantity.\n\nSTOCK OUT\nSold, used or damaged items.\nSubtracts from the quantity.\n\nA note helps explain each change.\nYou cannot remove more units\nthan are currently available.",
                   11, NAVY, justify="left", anchor="w").pack(anchor="w")

    def history_page(self):
        self.heading("Transaction history", "A record of opening stock and every stock movement, including archived products.")
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 14))
        search, kind = tk.StringVar(), tk.StringVar(value="All types")
        ttk.Entry(bar, textvariable=search, width=30).pack(side="left")
        combo = ttk.Combobox(bar, textvariable=kind, values=["All types", "OPENING", "IN", "OUT"], state="readonly", width=15)
        combo.pack(side="left", padx=10)
        self.button(bar, "Export CSV", lambda: self.export("history")).pack(side="right")
        self.label(self.content, "Search product, SKU or note", 10, MUTED).pack(anchor="w", pady=(0, 8))
        panel = self.panel(self.content)
        panel.pack(fill="both", expand=True)
        tree = self.table(panel, [("date", "Date & time", 160), ("sku", "SKU", 90), ("name", "Product", 160),
                                 ("kind", "Type", 85), ("qty", "Units", 65), ("balance", "Balance", 75), ("note", "Note", 210)])
        count = self.label(self.content, "", 10, MUTED)
        count.pack(side="bottom", anchor="w", pady=(10, 0), before=panel)

        def refresh(*args):
            tree.delete(*tree.get_children())
            self.history_rows = self.db.history(search.get(), kind.get())
            for i, row in enumerate(self.history_rows):
                tree.insert("", "end", values=tuple(row[k] for k in ("created_at", "sku", "product_name", "kind", "quantity", "balance", "note")), tags=("alt" if i % 2 else "",))
            count.configure(text=f"{len(self.history_rows)} movement(s)")

        search.trace_add("write", refresh)
        combo.bind("<<ComboboxSelected>>", refresh)
        refresh()

    def reports_page(self):
        self.analytics_page()

    def team_page(self):
        self.heading("Meet Team Doomsday", "The people behind this inventory management project.")
        hero = Card(self.content, height=175, color=NAVY, padding=25)
        hero.pack(fill="x", pady=(0, 22))
        self.label(hero.body, "DOOMSDAY", 30, WHITE, True).pack(anchor="w")
        self.label(hero.body, "Inventory & operations, thoughtfully organised.", 13, "#BCD2F2").pack(anchor="w", pady=(8, 0))
        self.label(hero.body, "PYTHON  /  TKINTER  /  SQLITE", 9, "#90B9F3", True).pack(anchor="w", pady=(12, 0))
        members = tk.Frame(self.content, bg=BG)
        members.pack(fill="x", pady=(0, 22))
        for i, (name, registration) in enumerate(TEAM):
            members.columnconfigure(i, weight=1, uniform="member")
            card = Card(members, height=185, padding=17)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i==0 else 7, 0 if i==2 else 7))
            avatar = tk.Canvas(card.body, width=48, height=48, bg=WHITE, highlightthickness=0)
            avatar.pack(anchor="w", pady=(0, 12))
            avatar.create_oval(0,0,47,47,fill=["#DFEBFF","#E8E4FA","#DBF2EF"][i],outline="")
            avatar.create_text(24,24,text="".join(part[0] for part in name.split()[:2]),font=(self.font,15,"bold"),fill=BLUE)
            self.label(card.body, name, 11, INK, True, wraplength=225, justify="left").pack(anchor="w")
            self.label(card.body, registration, 9, BLUE).pack(anchor="w", pady=(8,0))
        detail = Card(self.content, height=130, padding=20)
        detail.pack(fill="x")
        self.label(detail.body, "A complete desktop workflow", 14, INK, True).pack(anchor="w")
        self.label(detail.body, "Manage products and suppliers. Receive purchases. Record sales.\nTrack every stock movement with persistent records and account permissions.", 11, MUTED, justify="left").pack(anchor="w", pady=(9,0))

    def demo(self):
        if messagebox.askyesno("Load demo data", "Add 8 sample products for your demonstration?", parent=self):
            try:
                self.db.load_demo()
                self.status.set("Demo products added. You can edit them or use your own products.")
                self.show_page("Dashboard")
            except (ValueError, sqlite3.Error) as error:
                messagebox.showerror("Demo data", str(error), parent=self)

    def export(self, mode):
        path = filedialog.asksaveasfilename(parent=self, title="Save CSV report", defaultextension=".csv",
                                          initialfile=f"doomsday_{mode}_{datetime.now():%Y%m%d}.csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            if mode in ("history", "all_history"):
                self.db.export_history(path, self.history_rows if mode == "history" else None)
            else:
                rows = self.product_rows if mode == "products" else self.db.products(low_only=True) if mode == "low" else None
                self.db.export_products(path, rows)
            self.status.set("CSV report saved successfully.")
            messagebox.showinfo("Export complete", f"Report saved to:\n{path}", parent=self)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("Export failed", str(error), parent=self)

    def backup(self):
        path = filedialog.asksaveasfilename(parent=self, title="Save database backup", defaultextension=".db",
                                          initialfile=f"doomsday_backup_{datetime.now():%Y%m%d_%H%M%S}.db", filetypes=[("SQLite database", "*.db")])
        if path:
            try:
                self.db.backup(path)
                self.status.set("Database backup saved successfully.")
                messagebox.showinfo("Backup complete", f"Database saved to:\n{path}", parent=self)
            except (ValueError, OSError, sqlite3.Error) as error:
                messagebox.showerror("Backup failed", str(error), parent=self)

    def close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    try:
        app = InventoryApp()
        app.mainloop()
    except (tk.TclError, sqlite3.Error, OSError) as error:
        print(f"Could not start Doomsday Inventory: {error}")
        print("Run python3 -m tkinter to check Tkinter. Open this app on a desktop, not a headless terminal.")
