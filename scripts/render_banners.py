#!/usr/bin/env python3
"""Draw FC's authored pixel banners as portable SVGs; Python standard library only.

Edit the glyphs, sprites, coordinates, and palettes here. No image model, raster
input, external asset, font, random texture, or network request is involved.
Run from any directory: python3 scripts/render_banners.py
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'visuals'
GLYPHS = {
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'F':['11111','10000','10000','11110','10000','10000','10000'],
 'N':['10001','11001','11001','10101','10011','10011','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'V':['10001','10001','10001','10001','10001','01010','00100'],
 'Y':['10001','10001','01010','00100','00100','00100','00100'],
 '×':['00000','10001','01010','00100','01010','10001','00000'],
 ' ':['00000']*7,
}
PALETTES = {
 'canon': dict(bg='#FFF3E2', ink='#493E68', pale='#FFFCF3', pink='#F2B8C8',
               rose='#C888A9', mint='#B7DACD', leaf='#719F93', lilac='#C5B9DF',
               shade='#9381B6', wood='#EBC8B0', edge='#8D7597', sky='#E7E0F1'),
 'moon': dict(bg='#393650', ink='#FFF0D6', pale='#FFF6E5', pink='#E9B4CB',
              rose='#B280A9', mint='#B5D5CD', leaf='#668F8D', lilac='#B7AFE0',
              shade='#8980B3', wood='#B6A1BD', edge='#716886', sky='#4C4865'),
 'garden': dict(bg='#F7DCE1', ink='#68455D', pale='#FFF5DB', pink='#ECB3C5',
                rose='#C97F9C', mint='#BBD9BD', leaf='#779C88', lilac='#D2BCD9',
                shade='#9F84B6', wood='#E8C4A4', edge='#967384', sky='#F9E9CF'),
}

class PixelArt:
    def __init__(self, name):
        self.name = name
        self.c = PALETTES[name]
        self.parts = []
    def rect(self,x,y,w,h,color):
        color=self.c.get(color,color)
        self.parts.append(f'<path d="M{x} {y}h{w}v{h}h-{w}z" fill="{color}"/>')
    def sprite(self,x,y,rows,colors,scale=1):
        # Adjacent pixels of the same color share one horizontal run.
        for j,row in enumerate(rows):
            i=0
            while i<len(row):
                char=row[i]; end=i+1
                while end<len(row) and row[end]==char: end+=1
                if char!='.': self.rect(x+i*scale,y+j*scale,(end-i)*scale,scale,colors[char])
                i=end
    def word(self,x,y,value,scale,color):
        self.parts.append(f'<g aria-label="{escape(value)}">')
        for i,char in enumerate(value):
            self.sprite(x+i*6*scale,y,[r.replace('0','.') for r in GLYPHS[char]],{'1':color},scale)
        self.parts.append('</g>')
    def star(self,x,y,color='rose'):
        for dx,dy,w,h in [(2,0,1,5),(0,2,5,1)]: self.rect(x+dx,y+dy,w,h,color)
    def cloud(self,x,y):
        for dx,dy,w,h in [(5,0,14,3),(2,3,26,3),(0,6,33,4),(3,10,26,2)]:
            self.rect(x+dx,y+dy,w,h,'pale')
    def plant(self,x,y):
        self.sprite(x,y,[
            '....gg......','....gGg..gg.','.....Gg.gGg.',
            '..gg..G.gG..','.gGGg.GGG...','..ggGGG.....',
            '.....G......','..eeeeeee...','..epppppe...',
            '...epppe....','...eeeee....'],
            {'g':'mint','G':'leaf','e':'edge','p':'pink'},1)
    def cat(self,x,y):
        self.sprite(x,y,[
            '..ee.......ee.....','..epe.....epe.....','..epppeeeepppe....',
            '.eppppppppppppe...','epppwwppppwwpppe..','epppweppppwepppe..',
            'eppppppwwppppppe..','.eppprpwwprpppe...', '..eeeeeeeeeeee....',
            '...eppppppppe..ee.','...eppwwwwppe.epe.', '...eppwwwwppe.epe.',
            '..epppwwwwpppepe..','..eeeeeeeeeeeee...'],
            {'e':'edge','p':'pale','w':'wood','r':'rose'},1)
    def desk(self):
        # A small cream CRT with mint/lilac layout studies, deliberately nontextual.
        self.rect(206,35,67,43,'edge'); self.rect(209,32,61,3,'edge')
        self.rect(209,35,61,40,'pale'); self.rect(213,39,53,30,'shade')
        self.rect(215,41,49,26,'sky'); self.rect(218,44,13,20,'mint')
        self.rect(234,44,27,4,'pink'); self.rect(234,51,12,13,'lilac')
        self.rect(249,51,12,6,'pale'); self.rect(249,60,8,4,'wood')
        self.rect(256,71,4,2,'rose'); self.rect(234,78,10,5,'edge')
        self.rect(226,83,27,3,'edge'); self.rect(228,82,23,2,'lilac')
        self.rect(197,90,107,5,'edge'); self.rect(195,87,107,4,'wood')
        self.rect(200,88,98,1,'pale'); self.rect(201,95,5,18,'edge')
        self.rect(294,95,5,18,'edge'); self.rect(206,95,88,2,'rose')
        # Keyboard, a sketchbook, and one pixel cat perched next to the monitor.
        self.rect(214,85,42,2,'pale')
        for x in range(217,253,4): self.rect(x,85,2,1,'edge')
        self.rect(277,83,19,4,'shade'); self.rect(277,82,19,2,'pale')
        self.cat(277,66)
        self.plant(191,72)
    def icecream(self,x,y,scale=1):
        self.sprite(x,y,[
            '......rrrr......','....rrpppprr....','...rppwpppppr...',
            '..rppwwppppppr..','..rppppppppppr..','...rrrrrrrrrr...',
            '....emmmmmme....','....emwmmmme....','.....emmmme.....',
            '.....ewmwme.....','......emme......','......ewe.......',
            '.......e........'],
            {'r':'rose','p':'pink','w':'pale','e':'edge','m':'wood'},scale)
    def hill(self,points,color):
        self.parts.append('<path d="M'+ ' L'.join(f'{x} {y}' for x,y in points) +
                          ' V120 H0 Z" fill="'+self.c[color]+'"/>')
    def flower(self,x,y,color='pink',scale=1):
        self.sprite(x,y,['..pp...','.pppp..','ppwwpp.','ppwwpp.',
                         '.pppp..','..pG...','...Ggg.','...GG..'],
                    {'p':color,'w':'pale','G':'leaf','g':'mint'},scale)
    def draw(self):
        self.rect(0,0,320,120,'bg')
        self.parts.append('<g id="landscape">')
        # The full width is one tiny landscape: stepped distant hills,
        # a stream, a picnic-sized atelier and foreground flowers.
        for x,y in [(4,8),(279,5),(92,3)]: self.cloud(x,y)
        self.hill([(0,69),(16,69),(16,65),(39,65),(39,70),(63,70),
                   (63,66),(91,66),(91,73),(113,73),(113,67),(133,67),
                   (133,72),(161,72),(161,63),(177,63),(177,66),(207,66),
                   (207,70),(241,70),(241,65),(273,65),(273,70),(300,70),(300,67),(320,67)],'lilac')
        self.hill([(0,82),(23,82),(23,76),(53,76),(53,79),(83,79),(83,83),
                   (127,83),(127,77),(162,77),(162,80),(204,80),(204,84),
                   (250,84),(250,77),(290,77),(290,79),(320,79)],'mint')
        self.hill([(0,97),(34,97),(34,94),(73,94),(73,99),(109,99),
                   (109,104),(161,104),(161,101),(211,101),(211,96),
                   (263,96),(263,102),(291,102),(291,99),(320,99)],'pale')
        # A meandering lilac brook, punctuated by small cream reflections.
        for x,y,w,h in [(94,83,28,3),(103,86,30,3),(117,89,25,3),
                        (123,92,18,3),(113,95,27,3),(96,98,33,3),
                        (84,101,34,3),(91,104,40,3),(112,107,28,3),
                        (130,110,38,3),(140,113,45,7)]: self.rect(x,y,w,h,'sky')
        for x,y,w in [(101,84,11),(120,90,12),(98,99,14),(144,114,15)]:
            self.rect(x,y,w,1,'pale')
        # A little ice-cream-colored shelter; all details stay on the pixel grid.
        self.rect(219,62,2,44,'edge'); self.rect(299,62,2,44,'edge')
        self.rect(215,61,90,5,'pink'); self.rect(219,57,82,4,'pink')
        self.rect(224,54,72,3,'pale')
        for x in range(220,300,12): self.rect(x,61,6,7,'pale')
        # Render the desk at three-quarters its original size, snapped by SVG
        # crispEdges; its components are drawn here at their native pixel scale.
        self.parts.append('<g transform="translate(64 43) scale(.75)">')
        self.desk(); self.parts.append('</g>')
        for row in range(2):
            for col in range(7):
                self.rect(216+col*12,106+row*5,12,5,'pink' if (row+col)%2 else 'pale')
        # A tiny blanket and a companion cat on the left balance the studio.
        self.rect(30,89,48,17,'lilac')
        for x in range(32,76,8):
            self.rect(x,91,4,13,'pale')
        self.rect(32,96,44,3,'pink')
        self.cat(42,74); self.icecream(65,84)
        self.plant(11,75)
        for x,y,c,size in [(1,103,'rose',2),(19,111,'lilac',1),(73,111,'pink',1),
                           (167,102,'pink',2),(195,113,'lilac',1),(300,102,'rose',2),
                           (279,114,'pink',1),(149,78,'pale',1),(85,74,'pale',1)]:
            self.flower(x,y,c,size)
        for x,y in [(19,60),(181,68),(309,83),(81,100),(189,95)]:
            self.rect(x,y,1,3,'leaf'); self.rect(x-2,y+1,2,1,'leaf')
        if self.name=='moon':
            self.sprite(295,13,['..mm..','.mmmm.','mmmmmm','mmmmmm','.mmmm.','..mm..'],{'m':'pale'},2)
            for x,y in [(12,30),(22,46),(307,40),(273,10),(165,7)]: self.star(x,y,'pink')
        elif self.name=='garden':
            for x,y in [(4,45),(297,41),(185,78)]: self.flower(x,y,'pink',2)
        else:
            self.sprite(298,35,['..pp..','.pppp.','pppppp','pppppp','.pppp.','..pp..'],{'p':'pink'},2)
            self.star(16,44,'rose'); self.star(283,41,'lilac')
        self.parts.append('</g><g id="lettering">')
        # Full name is the scene title. FC is not used as a logo or monogram.
        self.word(35,20,'FRONTEND CRAFT',3,'ink')
        self.word(86,44,'FAYE × COVE',2,'ink')
        self.parts.append('</g>')
        title=f'Frontend Craft — Faye × Cove — {self.name}'
        desc=('Hand-authored pixel art in ice-cream colors. Frontend Craft and Faye × Cove '
              'share the initials FC. Custom pixel lettering floats over a tiny pastel landscape with a small '
              'cream computer, interface studies, a sketchbook and a pixel cat. '
              'Every shape is drawn by the repository’s Python source; no generated imagery is used.')
        output=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="480" viewBox="0 0 320 120" role="img" aria-labelledby="title desc" lang="en" shape-rendering="crispEdges"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><g id="pixel-art">{''.join(self.parts)}</g></svg>\n'''
        return output

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for edition in PALETTES:
        (OUT/f'banner-{edition}.svg').write_text(PixelArt(edition).draw(),encoding='utf-8')
    print('Rendered three authored pixel banners; no external inputs.')
