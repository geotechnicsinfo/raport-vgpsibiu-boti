# -*- coding: utf-8 -*-
"""Transcrierea fișelor manuscrise FC2, FC3 (Sibiu) -> 'fise foraj Sibiu.xlsx' (format identic cu Însurăței + coloana 'probe')."""
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

FISE = [
 {'id': 'FC2', 'data': '05.10.2026', 'gps': ['N 45°49\'33.823"', 'E 024°08\'46.201"'],
  'apa': ['NH=2.20m', 'NH la 24 h = 2,20 m'],
  'straturi': [
   (0.00, 0.10, 'umplutură – praf argilos slab nisipos, negru, cu pietriș mic', ''),
   (0.10, 0.60, 'argilă prăfoasă, slab nisipoasă, neagră, vârtoasă', ''),
   (0.60, 1.30, 'argilă prăfoasă, nisipoasă, cafeniu-negricioasă, vârtoasă', 'p1 – 1,00 m pp'),
   (1.30, 3.50, 'argilă prăfoasă nisipoasă, cafenie, consistentă/vârtoasă, cu mici fragmente de piatră; la 2,20 m apă; de la 2,30 m consistentă', 'p2 – 2,00 m pp; p3 – 3,00 m pp'),
   (3.50, 3.60, 'nisip fin prăfos, cenușiu', ''),
   (3.60, 5.80, 'argilă nisipoasă cafenie, consistent-vârtoasă, în alternanță cu praf nisipos', 'p4 – 4,00 m ștuț; p5 – 5,00 m pp'),
   (5.80, 6.60, 'nisip mediu cafeniu cu intercalații cenușii', 'p6 – 6,00 m pp'),
   (6.60, 6.90, 'nisip cu granulație mare, cafeniu, cu pietriș mic', ''),
   (6.90, 7.70, 'nisip argilos cenușiu', 'p7 – 7,00 m pp'),
   (7.70, 8.20, 'nisip prăfos cenușiu', 'p8 – 8,00 m pp'),
   (8.20, 9.30, 'nisip cu granulație mare, cenușiu, cu pietriș mic, în liant prăfos', 'p9 – 9,00 m pp'),
   (9.30, 10.20, 'nisip mediu cenușiu', 'p10 – 10,00 m pp'),
   (10.20, 10.40, 'argilă nisipoasă, cenușiu-negricioasă, consistentă, cu miros de baltă, resturi vegetale și mici fragmente de cochilii', 'p11 – 10,20–10,80 m pp'),
   (10.40, 10.80, 'nisip cu granulație mare, cenușiu, cu rar pietriș mic, în alternanță cu mici lentile de argilă', ''),
   (10.80, 12.50, 'argilă cenușiu-negricioasă, slab nisipoasă, consistentă', 'p12 – 11,50 m pp; p13 – 12,50 m ștuț inox Ø60'),
  ],
  'obs': 'Între 6,60 și 10,80 m: alternanță de nisip cu lentile de nisip argilos (notă din fișă).'},
 {'id': 'FC3', 'data': '06.10.2026', 'gps': ['N 45°49\'35.386"', 'E 024°08\'45.377"'],
  'apa': ['NH=2.60m', 'NH la 24 h = 2,46 m'],
  'straturi': [
   (0.00, 0.10, 'umplutură – praf argilos cu pietriș', ''),
   (0.10, 0.80, 'argilă prăfoasă cafeniu-negricioasă, vârtoasă', ''),
   (0.80, 1.60, 'argilă prăfoasă cafenie, vârtoasă; de la 1,30 m consistentă, cu concrețiuni calcaroase', 'p1 – 1,00 m pp'),
   (1.60, 3.30, 'argilă nisipoasă cafenie, consistentă; la 2,70 m apă', 'p2 – 2,00 m ștuț; p3 – 3,00 m pp'),
   (3.30, 4.70, 'nisip fin prăfos, cafeniu', 'p4 – 4,00 m ștuț'),
   (4.70, 5.70, 'argilă nisipoasă cafenie, consistentă', 'p5 – 5,00 m pp'),
   (5.70, 6.30, 'nisip mediu cafeniu, slab argilos', 'p6 – 6,00 m pp'),
   (6.30, 7.10, 'nisip cu granulație mare, cafeniu, cu rar pietriș mic; la 6,70 m o lentilă de argilă de 10 cm', 'p7 – 7,00 m pp'),
   (7.10, 7.60, 'pietriș mic nisipos, cafeniu', ''),
   (7.60, 8.40, 'argilă nisipoasă cenușie, consistentă, cu un ușor miros de baltă', 'p8 – 8,00 m ștuț inox Ø60'),
   (8.40, 8.80, 'mâl nisipos cenușiu-negricios, consistent/moale', ''),
   (8.80, 9.50, 'nisip fin mâlos, cenușiu-negricios', 'p9 – 9,00 m pp'),
  ],
  'obs': 'Între 8,40 și 9,50 m: alternanță de mâl nisipos cu nisip mâlos.'},
]


def write(path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Fise'
    thin = Side(style='thin', color='BBBBBB'); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill('solid', fgColor='DDEBF7')
    ws.append(['Amplasament:', 'VGP Park Sibiu – clădirile C, D, E', None, None, 'transcriere fișe manuscrise (foraje 12 m, Ø ~ 60–100 mm)'])
    r = 3
    for f in FISE:
        ws.cell(r, 1, 'foraj'); ws.cell(r, 2, 'de la'); ws.cell(r, 3, 'pana la'); ws.cell(r, 5, 'descriere'); ws.cell(r, 6, 'apa'); ws.cell(r, 7, 'data'); ws.cell(r, 8, 'GPS'); ws.cell(r, 9, 'probe')
        for c in range(1, 10):
            ws.cell(r, c).font = Font(bold=True); ws.cell(r, c).fill = hdr_fill; ws.cell(r, c).border = bd
        r += 1
        for k, (de, la, desc, probe) in enumerate(f['straturi']):
            ws.cell(r, 1, f['id']); ws.cell(r, 2, de); ws.cell(r, 3, la); ws.cell(r, 5, desc)
            if k < len(f['apa']): ws.cell(r, 6, f['apa'][k])
            if k == 0: ws.cell(r, 7, f['data'])
            if k < 2: ws.cell(r, 8, f['gps'][k])
            if probe: ws.cell(r, 9, probe)
            for c in range(1, 10):
                ws.cell(r, c).border = bd; ws.cell(r, c).alignment = Alignment(wrap_text=True, vertical='top')
            ws.cell(r, 2).number_format = '0.00'; ws.cell(r, 3).number_format = '0.00'
            r += 1
        if f.get('obs'):
            ws.cell(r, 1, f['id']); ws.cell(r, 5, 'Obs.: ' + f['obs']); ws.cell(r, 5).font = Font(italic=True); r += 1
        r += 1
    for col, w in zip('ABCDEFGHI', (8, 8, 8, 2, 70, 20, 12, 18, 34)):
        ws.column_dimensions[col].width = w
    wb.save(path)


if __name__ == '__main__':
    import sys
    write(sys.argv[1] if len(sys.argv) > 1 else 'fise foraj Sibiu.xlsx')
    print('ok')
