#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construiește data.json și pozele optimizate pentru aplicația de raportare
a investigațiilor de teren – VGP Park Sibiu (clădirile C, D, E).

Surse:
  - fise foraj Sibiu.xlsx   (foaia "Fise": stratificație, apă, dată, GPS, probe) – transcriere din fișele manuscrise
  - VGP_Sibiu_CDE_investigatii_rev1.csv  (punctele proiectate FC/FD/FE + CPT executate, Stereo 70 + WGS84)
  - VGP_Sibiu_CDE_foraje_raze30m_rev1.kml (conturul halelor C, D, E – layout 28.09.2026)
  - foldere "FC2", "FC3" … cu poze (WhatsApp) + fișa manuscrisă (FC2-1.jpeg, FC2-2.jpeg …)
  - meteo.json  (Open-Meteo archive)
  - cpt.json    (generat de build_cpt.py; folosit doar pentru stadiu/perioadă)

Rulare:
  python3 scripts/build_data.py --fise "<xlsx>" --csv "<csv>" --kml "<kml hale>" --poze "<folder Sibiu>" \
      --meteo scripts/meteo.json --cpt cpt.json --out .
"""
import argparse, csv, html, json, os, re, datetime
import openpyxl
from PIL import Image, ImageOps

MAX_W = 1200
THUMB_W = 420
QUALITY = 68


def dms_to_dec(s):
    m = re.search(r'([NSEW])\s*(\d+)[°\s]+(\d+)[\'\s]+([\d.]+)', str(s or ''))
    if not m: return None
    h, d, mi, se = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
    v = d + mi / 60 + se / 3600
    return round(-v if h in 'SW' else v, 6)


def norm_date(s):
    if not s: return None
    if isinstance(s, (datetime.date, datetime.datetime)): return s.strftime('%Y-%m-%d')
    m = re.match(r'(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})', str(s).strip())
    return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}' if m else None


def parse_probe(txt):
    out = []
    for part in re.split(r';', txt or ''):
        m = re.search(r'p(\d+)\s*[–\-]\s*([\d,\.]+)(?:\s*[–\-]\s*([\d,\.]+))?\s*m\s*(.*)', part.strip())
        if not m: continue
        ad = float(m.group(2).replace(',', '.'))
        rest = m.group(4).strip()
        tip = 'ștuț (probă netulburată)' if 'ștuț' in rest or 'stut' in rest else 'probă tulburată (pungă)'
        obs = rest.replace('pp', '').replace('ștuț', '').strip(' ,')
        if m.group(3): obs = (f'interval {m.group(2)}–{m.group(3)} m ' + obs).strip()
        out.append({'nr': int(m.group(1)), 'adancime': ad, 'tip': tip, 'observatii': obs})
    return out


def parse_fise(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Fise']
    inv = {}
    for r in ws.iter_rows(min_row=1, values_only=True):
        name = r[0]
        if not name or str(name).strip() in ('foraj', 'Amplasament:'): continue
        name = str(name).strip()
        d = inv.setdefault(name, {'id': name, 'straturi': [], 'apa': None, 'data': None, 'gps_dms': [], 'note_apa': [], 'probe': [], 'obs': []})
        de, la, desc = r[1], r[2], r[4]
        if desc and isinstance(de, (int, float)):
            d['straturi'].append({'de': float(de), 'la': float(la) if isinstance(la, (int, float)) else None, 'descriere': str(desc).strip()})
        elif desc:
            d['obs'].append(re.sub(r'^Obs\.?:\s*', '', str(desc).strip()))
        if r[5]:
            if d['apa'] is None: d['apa'] = str(r[5]).strip()
            else: d['note_apa'].append(str(r[5]).strip())
        if r[6]: d['data'] = norm_date(r[6])
        if r[7]: d['gps_dms'].append(str(r[7]).strip())
        if len(r) > 8 and r[8]: d['probe'] += parse_probe(str(r[8]))
    for d in inv.values():
        lat = lon = None
        for g in d['gps_dms']:
            v = dms_to_dec(g)
            if g.strip().startswith('N'): lat = v
            elif g.strip().startswith('E'): lon = v
        d['lat'], d['lon'] = lat, lon
        vals = [s['la'] for s in d['straturi'] if s['la'] is not None] + [s['de'] for s in d['straturi']]
        d['adancime'] = max(vals) if vals else None
        allw = ' '.join([d['apa'] or ''] + d['note_apa'])
        m = re.search(r'NH\s*=\s*([\d.,]+)', allw); d['NH'] = float(m.group(1).replace(',', '.')) if m else None
        m = re.search(r'IN\s*=\s*([\d.,]+)', allw); d['IN'] = float(m.group(1).replace(',', '.')) if m else None
        m = re.search(r'24\s*h\s*=\s*([\d.,]+)', allw); d['NH_24h'] = float(m.group(1).replace(',', '.')) if m else None
        d['probe'].sort(key=lambda p: p['nr'])
    return inv


def parse_csv(path):
    pts = []
    with open(path, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            pts.append({'id': r['ID'].strip(), 'status': r['Status'], 'tip': r['Tip'], 'hala': r['Hala (plan 2026, <=30 m)'],
                        'hala_2025': r['Hala (plan 2025)'], 'data': norm_date(r['Data']) if r['Data'] else None,
                        'adancime': float(r['Adancime (m)']) if r['Adancime (m)'] else None,
                        'stereo70': {'E': float(r['X Stereo70 (E)']), 'N': float(r['Y Stereo70 (N)'])},
                        'lat': float(r['Lat']), 'lon': float(r['Lon']), 'sursa': r['Sursa pozitie']})
    return pts


def parse_hale(path):
    s = open(path, encoding='utf-8').read()
    hale = []
    for p in re.findall(r'<Placemark>(.*?)</Placemark>', s, re.S):
        n = re.search(r'<name>(.*?)</name>', p); c = re.search(r'<Polygon>.*?<coordinates>(.*?)</coordinates>', p, re.S)
        if not (n and c and n.group(1).startswith('Hala')): continue
        ring = [[float(x.split(',')[1]), float(x.split(',')[0])] for x in c.group(1).split()]
        hale.append({'nume': html.unescape(n.group(1)), 'contur': ring})
    return hale


def process_photos(folder, out_dir, rel, iid):
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(folder) if re.search(r'\.jpe?g$|\.png$', f, re.I))
    fise, pics, n, nf = [], [], 0, 0
    for f in files:
        src = os.path.join(folder, f)
        try:
            im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        except Exception as e:
            print('  ! poza ignorată', src, e); continue
        is_fisa = 'fisa' in f.lower() or bool(re.match(rf'^{re.escape(iid)}[\s_-]*\d*\.(jpe?g|png)$', f, re.I))
        if is_fisa: nf += 1; name = f'fisa{nf}'
        else: n += 1; name = f'{n:02d}'
        for w, suffix in ((MAX_W, ''), (THUMB_W, 't_')):
            img = im.copy(); img.thumbnail((w, w))
            dst = os.path.join(out_dir, f'{suffix}{name}.jpg')
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src): continue
            img.save(dst, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
        entry = {'src': f'{rel}/{name}.jpg', 'thumb': f'{rel}/t_{name}.jpg', 'original': f, 'w': im.width, 'h': im.height}
        m = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{2})\.(\d{2})', f)
        if m: entry['timestamp'] = f'{m.group(1)} {m.group(2)}:{m.group(3)}'
        (fise if is_fisa else pics).append(entry)
    return fise, pics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fise', required=True); ap.add_argument('--csv', required=True); ap.add_argument('--kml', required=True)
    ap.add_argument('--poze', required=True); ap.add_argument('--meteo', default=None); ap.add_argument('--cpt', default=None)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    fise = parse_fise(a.fise)
    pts = parse_csv(a.csv)
    hale = parse_hale(a.kml)
    by_id = {p['id']: p for p in pts}
    foraje_pl = [p for p in pts if p['tip'].startswith('Foraj')]
    print(f'fise: {len(fise)}  puncte csv: {len(pts)}  foraje proiectate: {len(foraje_pl)}  hale: {len(hale)}')

    investigatii = []
    for iid in sorted(fise, key=lambda x: (x[:2], int(re.sub(r'\D', '', x) or 0))):
        f = fise[iid]; planned = by_id.get(iid)
        folder = os.path.join(a.poze, iid)
        fise_img, pics = ([], [])
        if os.path.isdir(folder):
            print('poze', iid); fise_img, pics = process_photos(folder, os.path.join(a.out, 'photos', iid), f'photos/{iid}', iid)
        lat, lon, src = f['lat'], f['lon'], 'GPS teren'
        if (lat is None or lon is None) and planned: lat, lon, src = planned['lat'], planned['lon'], 'punct proiectat (fără GPS în fișă)'
        hala = planned['hala'] if planned else iid[1]
        nota = None
        pd = sorted({x['timestamp'][:10] for x in pics if x.get('timestamp')})
        if f['data'] and pd and f['data'] not in pd:
            nota = f"Fișa este datată {f['data']}; fotografiile au fost transmise pe {', '.join(pd)}. S-a reținut data din fișă."
        if f['obs']: nota = (nota + ' ' if nota else '') + ' '.join(f['obs'])
        investigatii.append({
            'id': iid, 'id_fisa': iid, 'tip': 'foraj', 'nr': int(re.sub(r'\D', '', iid)), 'hala': hala,
            'categorie_kml': f'Foraj geotehnic – clădirea {hala}',
            'eticheta': f'Foraj geotehnic {iid}', 'data': f['data'], 'nota_data': nota,
            'adancime': f['adancime'], 'adancime_proiectata': planned['adancime'] if planned else None,
            'apa': f['apa'], 'NH': f['NH'], 'NH_24h': f['NH_24h'], 'IN': f['IN'], 'note_apa': f['note_apa'],
            'gps_dms': f['gps_dms'], 'lat': lat, 'lon': lon, 'coord_sursa': src,
            'proiectat': planned and {'id': planned['id'], 'lat': planned['lat'], 'lon': planned['lon'], 'stereo70': planned['stereo70'],
                                      'obs': f"{planned['tip']} – clădirea {planned['hala']}", 'adancime': f"{planned['adancime']:.0f} m"},
            'rt': None, 'straturi': f['straturi'], 'probe': f['probe'],
            'fisa_foto': fise_img[0] if fise_img else None, 'fise_foto': fise_img, 'poze': pics,
        })

    meteo = {}
    if a.meteo and os.path.exists(a.meteo):
        mj = json.load(open(a.meteo, encoding='utf-8')); d = mj['daily']
        for i, t in enumerate(d['time']): meteo[t] = {k: d[k][i] for k in d if k != 'time'}
        meteo['_meta'] = {'sursa': 'Open-Meteo (ERA5 / archive API)', 'lat': mj.get('latitude'), 'lon': mj.get('longitude'), 'elevatie_m': mj.get('elevation')}

    cpt_meta = None
    if a.cpt and os.path.exists(a.cpt):
        cj = json.load(open(a.cpt, encoding='utf-8')); cpt_meta = cj['meta']
        cpt_meta['teste'] = [{'id': t['id'], 'tip': t['tip'], 'data': t['data'], 'adancime': t['adancime'], 'hala': t['hala'],
                              'hala_2025': t['hala_2025'], 'coord_sursa': t['coord_sursa'],
                              'lat': t['lat'], 'lon': t['lon'], 'stereo70': t['stereo70'], 'qc_med': t['sumar']['qc_med'], 'qc_max': t['sumar']['qc_max'],
                              'straturi_sbt': t['straturi_sbt'], 'benzi_1m': [{k: b[k] for k in ('de', 'la', 'qc_med', 'qc_max')} for b in t['benzi_1m']]} for t in cj['teste']]

    exec_ids = {i['id'] for i in investigatii}
    stadiu = []
    for h in ('C', 'D', 'E'):
        ids = [p['id'] for p in foraje_pl if p['hala'] == h]
        stadiu.append({'categorie': f'Foraje geotehnice – clădirea {h}', 'hala': h, 'proiectate': len(ids),
                       'executate': len([x for x in ids if x in exec_ids]), 'neexecutate': [x for x in ids if x not in exec_ids]})
    stadiu.append({'categorie': 'Foraje geotehnice – total', 'hala': None, 'proiectate': len(foraje_pl),
                   'executate': len(investigatii), 'neexecutate': [p['id'] for p in foraje_pl if p['id'] not in exec_ids]})
    if cpt_meta:
        stadiu.append({'categorie': 'Penetrări statice CPT/CPTu (apr. 2025)', 'hala': None, 'proiectate': cpt_meta['nr'], 'executate': cpt_meta['nr'], 'neexecutate': []})

    dates = [i['data'] for i in investigatii if i['data']]
    out = {
        'stadiu': stadiu,
        'proiect': {
            'titlu': 'Investigații geotehnice – VGP Park Sibiu, clădirile C, D, E',
            'beneficiar_lucrare': 'VGP PARK SIBIU SRL – hale logistice C, D și E (Sameday)',
            'amplasament': 'VGP Park Sibiu, Calea Șurii Mari / DN 14, mun. Sibiu, jud. Sibiu',
            'executant': 'SC BBCGEOTECHNIC SRL',
            'tip_lucrari': 'Foraje geotehnice cu prelevare de probe (12 m, FC/FD/FE) și penetrări statice CPT/CPTu (15 m, aprilie 2025)',
            'perioada': {'de_la': min(dates) if dates else None, 'pana_la': max(dates) if dates else None},
            'perioada_cpt': cpt_meta['perioada'] if cpt_meta else None,
            'generat': datetime.date.today().isoformat(),
        },
        'investigatii': investigatii,
        'puncte_proiectate': [{'id': p['id'], 'lat': p['lat'], 'lon': p['lon'], 'tip': p['tip'], 'hala': p['hala'], 'status': p['status'],
                               'adancime': f"{p['adancime']:.0f} m" if p['adancime'] else '', 'obs': f"clădirea {p['hala']}", 'stereo70': p['stereo70']} for p in foraje_pl],
        'hale': hale,
        'cpt': cpt_meta,
        'meteo': meteo,
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'data.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print('scris data.json', len(investigatii), 'foraje')


if __name__ == '__main__':
    main()
