#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construiește cpt.json din fișierele Geo-Explorer (*.txt) ale penetrărilor statice
CPT / CPTu executate la VGP Park Sibiu (aprilie 2025).

Surse:
  - 1-CPTxxx.txt  (export Geo-Explorer 2.0: antet + tabel Depth/qc/fs/u2/Incl)
  - VGP_Sibiu_CDE_investigatii_rev1.csv  (ID, tip, hala, dată, adâncime, Stereo70, lat/lon)

Rulare:
  python3 scripts/build_cpt.py --txt "<folder cu 1-CPT*.txt>" --csv "<csv investigatii>" --out .

Derivate (Robertson 2009/2010, proceduri uzuale):
  Rf = fs / qc · 100 [%];  qt = qc + u2(1-a), a = 0.80 (piezocon), qt = qc la CPT mecanic/electric fără u2
  Ic = sqrt[(3.47 - log Qt)^2 + (log Fr + 1.22)^2], Qt = (qt-σv)/σ'v · (pa/σ'v)^n, n = f(Ic) iterativ
  γ estimat din Ic (Robertson & Cabal 2010); NH presupus la 2,40 m (FC2/FC3, oct. 2026) – de verificat
"""
import argparse, csv, glob, json, math, os, re, datetime

A_NET = 0.80      # raport arii piezocon
GWL = 2.40        # m – nivel apă presupus pentru σ'v (FC2: 2,20 m; FC3: 2,60 m, oct. 2026)
GW = 9.81
PA = 100.0        # kPa

SBT = {1: 'sensibil, fin', 2: 'organic / turbă', 3: 'argilă – argilă prăfoasă', 4: 'praf argilos – argilă prăfoasă',
       5: 'nisip prăfos – praf nisipos', 6: 'nisip – nisip prăfos', 7: 'nisip îndesat – nisip cu pietriș',
       8: 'nisip foarte îndesat / cimentat', 9: 'fin, foarte rigid (supraconsolidat)'}
SBT_COL = {1: '#B5B5B5', 2: '#8B6B4E', 3: '#A8814D', 4: '#C9A46B', 5: '#E4C27C', 6: '#F3D36B', 7: '#F0B35B', 8: '#D98F3E', 9: '#9C8C78'}


def ic_zone(ic):
    if ic is None: return 0
    if ic > 3.6: return 2
    if ic > 2.95: return 3
    if ic > 2.6: return 4
    if ic > 2.05: return 5
    if ic > 1.31: return 6
    return 7


def parse_txt(path):
    lines = open(path, encoding='latin-1').read().splitlines()
    hdr, di = {}, None
    for i, l in enumerate(lines):
        if l.replace('"', '').startswith('Depth'):
            di = i; break
        m = re.match(r'([A-Za-z .0-9]+?)\s*:\s*(.*)', l)
        if m: hdr[m.group(1).strip()] = m.group(2).strip()
    end = next((re.search(r'End of Test\s*:\s*(\S+)', l).group(1) for l in lines if 'End of Test' in l), None)
    z, qc, fs, u2, inc = [], [], [], [], []
    for l in lines[di + 3:]:
        c = l.replace('"', '').split('\t')
        if len(c) < 5 or not c[0].strip(): continue
        try:
            z.append(float(c[0])); qc.append(float(c[1])); fs.append(float(c[2]))
        except ValueError:
            continue
        u2.append(None if c[3].strip() in ('Disabled', '') else float(c[3]))
        try:
            inc.append(math.hypot(float(c[4]), float(c[5])))
        except ValueError:
            inc.append(None)
    has_u = any(v is not None for v in u2)
    return hdr, z, qc, fs, (u2 if has_u else None), inc, end


def derive(z, qc, fs, u2):
    """Rf, Ic, γ, σv, SBT pe fiecare rând."""
    n = len(z)
    rf, ic, zone = [None] * n, [None] * n, [0] * n
    sv = 0.0; zprev = 0.0; gam = 18.0
    gam_list = []
    for i in range(n):
        qci = max(qc[i], 0.01) * 1000.0  # kPa
        fsi = max(fs[i], 0.0)
        qt = qci + (u2[i] * (1 - A_NET) if (u2 and u2[i] is not None) else 0.0)
        # γ din Ic-ul anterior (Robertson & Cabal 2010)
        if i > 0 and ic[i - 1] is not None:
            rf_prev = max(rf[i - 1], 0.01)
            gam = GW * (0.27 * math.log10(rf_prev) + 0.36 * math.log10(qt / PA) + 1.236)
            gam = min(max(gam, 15.0), 22.0)
        dz = z[i] - zprev; zprev = z[i]
        sv += gam * dz
        u0 = GW * max(z[i] - GWL, 0.0)
        svp = max(sv - u0, 1.0)
        rfi = fsi / qci * 100.0
        rf[i] = rfi
        if z[i] < 0.05:
            ic[i] = None; gam_list.append(gam); continue
        fr = max(fsi / max(qt - sv, 1.0) * 100.0, 0.01)
        nn = 1.0; ici = None
        for _ in range(8):
            Q = max((qt - sv) / PA * (PA / svp) ** nn, 0.01)
            ici = math.sqrt((3.47 - math.log10(Q)) ** 2 + (math.log10(fr) + 1.22) ** 2)
            n_new = min(0.381 * ici + 0.05 * (svp / PA) - 0.15, 1.0)
            if abs(n_new - nn) < 0.01: break
            nn = n_new
        ic[i] = ici; zone[i] = ic_zone(ici)
        gam_list.append(gam)
    return rf, ic, zone, gam_list


def layers_from_zone(z, zone, min_th=0.40):
    """Zone SBT contigue, apoi fuzionare straturi subțiri cu vecinul mai gros."""
    segs = []
    for zi, zo in zip(z, zone):
        if zo == 0: continue
        if segs and segs[-1]['zona'] == zo:
            segs[-1]['la'] = zi
        else:
            segs.append({'de': segs[-1]['la'] if segs else 0.0, 'la': zi, 'zona': zo})
    changed = True
    while changed and len(segs) > 1:
        changed = False
        for k, s in enumerate(segs):
            if s['la'] - s['de'] < min_th:
                nb = []
                if k > 0: nb.append(k - 1)
                if k < len(segs) - 1: nb.append(k + 1)
                j = max(nb, key=lambda q: segs[q]['la'] - segs[q]['de'])
                lo, hi = (j, k) if j < k else (k, j)
                segs[lo]['la'] = segs[hi]['la']; segs[lo]['zona'] = segs[j]['zona']
                del segs[hi]; changed = True; break
    # fuzionare zone identice adiacente
    out = []
    for s in segs:
        if out and out[-1]['zona'] == s['zona']: out[-1]['la'] = s['la']
        else: out.append(dict(s))
    for s in out:
        s['de'] = round(s['de'], 2); s['la'] = round(s['la'], 2); s['sbt'] = SBT[s['zona']]; s['culoare'] = SBT_COL[s['zona']]
    return out


def stats(z, qc, fs, rf, ic, zone, de, la):
    idx = [i for i in range(len(z)) if de <= z[i] < la]
    if not idx: return None
    q = [qc[i] for i in idx]; f = [fs[i] for i in idx]; r = [rf[i] for i in idx]; c = [ic[i] for i in idx if ic[i] is not None]
    return {'de': de, 'la': la, 'qc_med': round(sum(q) / len(q), 2), 'qc_min': round(min(q), 2), 'qc_max': round(max(q), 2),
            'fs_med': round(sum(f) / len(f), 1), 'Rf_med': round(sum(r) / len(r), 2),
            'Ic_med': round(sum(c) / len(c), 2) if c else None}


def norm_date(s):
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})', s or '')
    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--txt', required=True); ap.add_argument('--csv', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    meta = {}
    with open(a.csv, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            meta[r['ID'].strip()] = r
    tests = []
    for f in sorted(glob.glob(os.path.join(a.txt, '1-CPT*.txt'))):
        fid = re.sub(r'^1-|\.txt$', '', os.path.basename(f))
        hdr, z, qc, fs, u2, inc, end = parse_txt(f)
        rf, ic, zone, gam = derive(z, qc, fs, u2)
        m = meta.get(fid, {})
        note = []
        if hdr.get('TestNumber') and hdr['TestNumber'] != fid:
            note.append(f"În antetul fișierului numărul testului este „{hdr['TestNumber']}” (eroare de operator); s-a reținut denumirea din numele fișierului și din planul de amplasare.")
        depth = z[-1]
        band = [stats(z, qc, fs, rf, ic, zone, d, min(d + 1.0, depth + 1e-9)) for d in range(0, int(math.ceil(depth)))]
        band = [b for b in band if b]
        allq = qc[5:]
        tests.append({
            'id': fid, 'tip': 'CPTu' if u2 else 'CPT',
            'con': hdr.get('ConeNumber'), 'con_tip': 'piezocon (con electric cu filtru u2)' if u2 else 'con electric',
            'data': norm_date(hdr.get('Date')) or norm_date(m.get('Data')),
            'ora_start': hdr.get('Time Start'), 'ora_final': end,
            'adancime': round(depth, 2), 'pre_drill': float(hdr.get('Pre Drill') or 0),
            'hala': m.get('Hala (plan 2026, <=30 m)') or '', 'hala_2025': m.get('Hala (plan 2025)') or '',
            'lat': float(m['Lat']) if m.get('Lat') else None, 'lon': float(m['Lon']) if m.get('Lon') else None,
            'stereo70': {'E': float(m['X Stereo70 (E)']), 'N': float(m['Y Stereo70 (N)'])} if m.get('X Stereo70 (E)') else None,
            'coord_sursa': m.get('Sursa pozitie') or '',
            'nota': ' '.join(note) or None,
            'sumar': {'qc_med': round(sum(allq) / len(allq), 2), 'qc_max': round(max(allq), 2), 'qc_min': round(min(allq), 2),
                      'fs_med': round(sum(fs[5:]) / len(fs[5:]), 1), 'Rf_med': round(sum(rf[5:]) / len(rf[5:]), 2),
                      'u2_max': round(max(v for v in u2 if v is not None), 1) if u2 else None,
                      'incl_max': round(max(v for v in inc if v is not None), 1) if any(v is not None for v in inc) else None,
                      'n_puncte': len(z)},
            'straturi_sbt': layers_from_zone(z, zone),
            'benzi_1m': band,
            'dz': 0.01, 'z0': z[0],
            'z': [round(v, 2) for v in z],
            'qc': [round(v, 2) for v in qc], 'fs': [round(v, 1) for v in fs],
            'u2': ([None if v is None else round(v, 1) for v in u2] if u2 else None),
            'Rf': [round(v, 2) for v in rf], 'Ic': [None if v is None else round(v, 2) for v in ic],
        })
        print(fid, tests[-1]['tip'], tests[-1]['data'], depth, 'qc_med', tests[-1]['sumar']['qc_med'], 'straturi', len(tests[-1]['straturi_sbt']))
    # ordine: pe hale, apoi numeric
    def key(t):
        m = re.match(r'CPT(U?)([A-Z]+)(\d+)', t['id'])
        return (m.group(2), int(m.group(3)), m.group(1))
    tests.sort(key=key)
    out = {
        'meta': {'generat': datetime.date.today().isoformat(), 'nr': len(tests),
                 'nr_cptu': sum(1 for t in tests if t['tip'] == 'CPTu'),
                 'ml': round(sum(t['adancime'] for t in tests), 2),
                 'perioada': {'de_la': min(t['data'] for t in tests), 'pana_la': max(t['data'] for t in tests)},
                 'echipament': 'Geo-Explorer v2.0 (Geomil); con electric S10-CFI.2030 (10 cm²) / piezocon C15-CFIP.2194 (15 cm²)',
                 'ipoteze': f'Ic după Robertson (2009), γ estimat din Ic (Robertson & Cabal 2010), a = {A_NET} pentru piezocon, NH presupus la {GWL:.2f} m (din FC2/FC3, oct. 2026).',
                 'sbt': SBT, 'sbt_culori': SBT_COL},
        'teste': tests,
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'cpt.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print('scris cpt.json', len(tests), 'teste', os.path.getsize(os.path.join(a.out, 'cpt.json')) // 1024, 'kB')


if __name__ == '__main__':
    main()
