"""Small reusable Tkinter drawing helpers. No external UI packages required."""
import tkinter as tk

BLUE = '#2563EB'
NAVY = '#102746'
BG = '#F3F6FB'
WHITE = '#FFFFFF'
INK = '#142742'
MUTED = '#718098'
LINE = '#E4EAF3'
FONT = 'DejaVu Sans'


def rounded(canvas, x1, y1, x2, y2, radius=14, **options):
    r = min(radius, (x2-x1)/2, (y2-y1)/2)
    points = [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
              x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **options)


def icon(c, x, y, name, color=BLUE, scale=1):
    def line(*p):
        c.create_line(*[v*scale+(x if i%2==0 else y) for i,v in enumerate(p)], fill=color, width=1.6)
    def rect(a,b,d,e):
        c.create_rectangle(x+a*scale,y+b*scale,x+d*scale,y+e*scale,outline=color,width=1.6)
    if name in ('Dashboard','Reports'):
        for i,h in enumerate([8,15,11]): rect(2+i*7,22-h,6+i*7,22)
    elif name in ('Products','Purchasing','Stock In / Out'):
        line(2,7,12,2,22,7,12,12,2,7,2,19,12,24,22,19,22,7)
        line(12,12,12,24); line(7,4,17,9)
    elif name in ('Sales','History','Activity'):
        rect(4,2,21,24); line(8,8,17,8); line(8,13,17,13); line(8,18,14,18)
    elif name in ('Suppliers','Our Team','Accounts'):
        c.create_oval(x+8*scale,y+2*scale,x+17*scale,y+11*scale,outline=color,width=1.6)
        line(3,23,3,20,7,15,18,15,22,20,22,23)
    else:
        rect(3,4,22,21); line(7,9,18,9); line(7,15,15,15)


class Card(tk.Canvas):
    def __init__(self, parent, color=WHITE, padding=16, **kwargs):
        super().__init__(parent, bg=parent.cget('bg'), highlightthickness=0, bd=0, **kwargs)
        self.color, self.padding = color, padding
        self.body = tk.Frame(self, bg=color)
        self.window = self.create_window(padding, padding, anchor='nw', window=self.body)
        self.bind('<Configure>', self.resize)

    def resize(self, event):
        self.delete('surface')
        rounded(self, 1,1,event.width-1,event.height-1,16,fill=self.color,outline=LINE if self.color==WHITE else self.color,tags='surface')
        self.tag_lower('surface')
        self.itemconfigure(self.window,width=max(1,event.width-2*self.padding),height=max(1,event.height-2*self.padding))


class NavItem(tk.Canvas):
    def __init__(self,parent,title,command):
        super().__init__(parent,height=39,bg=NAVY,highlightthickness=0,bd=0,cursor='hand2',takefocus=True)
        self.title,self.command,self.active=title,command,False
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Button-1>',lambda e:command())
        self.bind('<Return>',lambda e:command())
        self.bind('<space>',lambda e:command())
        self.bind('<Enter>',lambda e:self.draw(True))
        self.bind('<Leave>',lambda e:self.draw())
        self.bind('<FocusIn>',lambda e:self.draw(True))
        self.bind('<FocusOut>',lambda e:self.draw())

    def select(self,value):
        self.active=value; self.draw()

    def draw(self,hover=False):
        self.delete('all')
        color=WHITE if self.active else '#B5C7E0'
        if self.active or hover:
            rounded(self,1,1,self.winfo_width()-1,38,9,fill=BLUE if self.active else '#1A385B',outline='')
        icon(self,14,8,self.title,color,.78)
        self.create_text(46,20,text=self.title,anchor='w',font=(FONT,11),fill=color)
        if self.active: self.create_oval(self.winfo_width()-19,17,self.winfo_width()-14,22,fill='#A5C4FF',outline='')


def warehouse(c, x, y, scale=1):
    # Isometric cartons drawn with Canvas polygons, so no image assets are needed.
    for dx,dy,size,color in [(0,40,52,'#62A0FF'),(83,75,40,'#C9DEFF'),(74,-18,59,'#8CB8FF')]:
        a,b,s=x+dx*scale,y+dy*scale,size*scale
        c.create_polygon(a,b,a+s,b-s*.45,a+2*s,b,a+s,b+s*.45,fill=color,outline='#B4D1FF')
        c.create_polygon(a,b,a+s,b+s*.45,a+s,b+s*1.55,a,b+s*1.1,fill='#2A69D8',outline='#8BB7FF')
        c.create_polygon(a+s,b+s*.45,a+2*s,b,a+2*s,b+s*1.1,a+s,b+s*1.55,fill='#4385EF',outline='#B4D1FF')
        c.create_line(a+s*.5,b-s*.22,a+s*1.5,b+s*.22,a+s*1.5,b+s*.65,fill='#E5F0FF',width=4*scale)
