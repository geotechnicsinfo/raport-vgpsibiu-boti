# Investigații de teren – VGP Park Sibiu (clădirile C, D, E)

Aplicație web statică (fără backend) pentru raportarea investigațiilor geotehnice de teren
executate la VGP Park Sibiu (Calea Șurii Mari / DN 14, mun. Sibiu) pentru halele C, D și E (Sameday):

- **foraje geotehnice** FC / FD / FE (12 m, cu prelevare de probe) – campania din octombrie 2026;
- **penetrări statice CPT / CPTu** (15 m, 40 de teste) – campania din 03–13.04.2025.

Conține, pentru fiecare foraj: fotografii de teren + fișa manuscrisă (mai multe pagini), stratificația
transcrisă cu coloană litologică, nivelul apei (NH, NH la 24 h), probele (ștuțuri / probe tulburate),
GPS teren vs. punct proiectat (Stereo 70), meteo în ziua execuției, CPT-urile din vecinătate.

Pentru fiecare CPT / CPTu: diagramele q<sub>c</sub>, f<sub>s</sub>, R<sub>f</sub>, u<sub>2</sub> (piezocon),
I<sub>c</sub> cu straturile SBT (Robertson), valori medii pe benzi de 1 m, poziție, mini-hartă, meteo.

Plus: intro 3D (bloc de teren EU-DEM cu forajele și tijele CPT „extrase” în ordinea execuției),
hartă interactivă cu conturul halelor (layout 28.09.2026), stadiu execuție, calendar, centralizatoare + CSV.

## Structura

```
index.html            aplicația (HTML + CSS + JS, un singur fișier)
intro3d.js            intro 3D (Three.js r128)
data.json             foraje + puncte proiectate + hale + meteo + sumar CPT (generat)
cpt.json              datele complete CPT/CPTu, pas 1 cm (generat, ~1,6 MB, încărcat la cerere)
terrain.json          grilă de cote EU-DEM 25 m (24×24) pentru intro-ul 3D
photos/<ID>/          poze optimizate (1200 px) + miniaturi t_*.jpg + fisa1.jpg, fisa2.jpg (generat)
scripts/build_cpt.py  parser Geo-Explorer -> cpt.json (Rf, Ic, SBT, benzi de 1 m)
scripts/build_data.py generatorul data.json + poze
scripts/fise_sibiu_src.py  transcrierea fișelor manuscrise -> fise foraj Sibiu.xlsx (sursa de adevăr rămâne Excelul)
scripts/meteo.json    răspunsul Open-Meteo pentru cele două campanii
```

## Surse de date (Google Drive office.geotehnica)

- Poze + fișe manuscrise: `Lucrari geo dosar comun\Poze foraje si penetrare\Poze foraj si penetrare 2026\Sibiu\<ID>\`
  (fișa = `FC2-1.jpeg`, `FC2-2.jpeg` …; restul sunt poze WhatsApp).
- Fișe transcrise: `Work\2026\VGP Sibiu\2. Fise de foraj\fise foraj Sibiu.xlsx`, foaia „Fise”
  (coloane: foraj | de la | pana la | – | descriere | apa | data | GPS | probe). Un rând fără adâncimi și cu
  „Obs.: …” în descriere devine notă pe fișă. Probe: `p4 – 4,00 m ștuț; p5 – 5,00 m pp` (pp = probă tulburată).
- Plan investigații rev. 1 (28.09.2026): `Work\2026\VGP Sibiu\1. Input\VGP Sibiu\28092026\VGP_Sibiu_CDE_investigatii_rev1.csv`
  (+ `VGP_Sibiu_CDE_foraje_raze30m_rev1.kml` pentru conturul halelor).
- CPT: `Work\2026\VGP Sibiu\4. CPT\Sibiu CPT\1-CPT*.txt` (export Geo-Explorer 2.0).

## Regenerarea datelor

```bash
python3 scripts/build_cpt.py  --txt "../4. CPT/Sibiu CPT" \
  --csv "../1. Input/VGP Sibiu/28092026/VGP_Sibiu_CDE_investigatii_rev1.csv" --out .
python3 scripts/build_data.py --fise "../2. Fise de foraj/fise foraj Sibiu.xlsx" \
  --csv "../1. Input/VGP Sibiu/28092026/VGP_Sibiu_CDE_investigatii_rev1.csv" \
  --kml "../1. Input/VGP Sibiu/28092026/VGP_Sibiu_CDE_foraje_raze30m_rev1.kml" \
  --poze "<folder Sibiu cu poze>" --meteo scripts/meteo.json --cpt cpt.json --out .
```

Necesită `openpyxl` și `Pillow`. Pentru un foraj nou: adaugă blocul în Excel + folderul de poze `<ID>` și rulează
`build_data.py` (pozele deja procesate sunt sărite). Dacă apar zile noi, completează `scripts/meteo.json`
(Open-Meteo archive, `latitude=45.827&longitude=24.145`, aceleași variabile `daily`).

## Observații asupra datelor

- FC2: fișa este datată 05.10.2026, pozele au fost transmise pe 06.10.2026; adâncime 12,50 m (proiectat 12 m); NH = 2,20 m.
- FC3: oprit la 9,50 m (proiectat 12 m); NH = 2,60 m, la 24 h 2,46 m.
- Fișierul `1-CPTB12.txt` are în antet `TestNumber: CPTB22` (eroare de operator); s-a reținut CPTB12 (nume fișier + plan).
- CPTB211 este înregistrat cu piezocon (u2 măsurat), deci apare ca CPTu (6 CPTu în total, nu 5 ca în ofertă).
- Pozițiile CPT provin din KMZ-ul de teren (`SIBIU - CPT - 11-April.kmz`); pentru 10 teste nu există poziție măsurată
  și s-a folosit punctul proiectat („pozitie proiectata (KMZ)” în centralizator).
- I<sub>c</sub>/SBT: Robertson (2009), γ estimat din I<sub>c</sub>, a = 0,80, NH presupus la 2,40 m – indicativ,
  nu înlocuiește prelucrarea din studiul geotehnic.
- Intro 3D: relief exagerat ×14 (amplitudine ~11 m), investigații ×24; se dezactivează singur fără WebGL.

## Rulare locală / publicare

```bash
python -m http.server 8000     # apoi http://localhost:8000
```

Publicare: repo GitHub `geotechnicsinfo/raport-vgpsibiu-boti`, Settings → Pages → Source: *GitHub Actions*;
workflow-ul `.github/workflows/pages.yml` publică la fiecare push pe `main`.
