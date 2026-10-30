"""Read-only forensic extraction of the Dalby reference OBX files (Phase 1 evidence).

Usage: python -I dalby_obx_forensics.py <obx_dir> <ocd_db_dir> <out_dir>
Writes: obx_inventory.csv, dalby_articles.csv, top_finish_reconciliation.csv, side_table_gbp_56.csv
Prints the check summaries quoted in Dalby_OBX_Forensic_Analysis.md. Does not modify inputs.
"""
import csv
import collections
import glob
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

OBX, DB, OUT = sys.argv[1], sys.argv[2].rstrip('/\\') + '/', sys.argv[3]
os.makedirs(OUT, exist_ok=True)


def load(p):
    b = open(p, 'rb').read()
    t = b.decode('utf-8')  # raises if not valid UTF-8 (all inspected files are valid)
    return ET.fromstring(re.sub(r'^<\?xml[^>]*\?>', '', t.lstrip())), len(b)


def parse(root, fname):
    out = []
    for a in root.iter('bskArticle'):
        def art(t):
            e = [x for x in a.findall('artNr') if x.get('type') == t]
            return e[0].text if e else None
        pi = a.find('pdInfo')
        gc = a.find('geometryChecksum')
        pd = a.find('priceDate')
        pv = [e.text for e in a.findall('propVarCode') if e.get('aggr') is None]
        out.append(dict(
            file=fname, base=art('base'), final=art('final'), varcode=art('varcode'), ofmlvarcode=art('ofmlvarcode'),
            features=[(f.get('name'), f.get('value'), f.get('flags')) for f in a.findall('features/feature')],
            propVarCode=pv[0] if pv else None,
            prices=[(e.get('type'), e.get('pd'), e.get('currency'), e.get('value')) for e in a.findall('itemPrice')],
            comps=[(c.findtext('name'), c.get('value')) for c in a.findall('priceComponents/priceComponent')],
            priceDate=pd.get('value') if pd is not None else None,
            geo=gc.get('value') if gc is not None else None,
            addState=[e.get('type') for e in a.findall('addStateCode')],
            progId=pi.get('progId') if pi is not None else None,
            region=pi.get('region') if pi is not None else None))
    return out


inv, rows = [], []
for p in sorted(glob.glob(OBX + '/*.obx')):
    n = os.path.basename(p)
    root, sz = load(p)
    vi = root.find('.//versionInfo')
    arts = parse(root, n)
    rows += arts
    fin = [x['final'] for x in arts]
    inv.append(dict(
        file=n, bytes=sz, root=root.tag,
        app=(vi.get('appKey') + ' ' + vi.get('appVersion')) if vi is not None else '(no versionInfo)',
        articles=len(arts), unique_final=len(set(fin)), duplicates=len(fin) - len(set(fin)),
        bases=' '.join(sorted(set(x['base'] for x in arts))),
        currency=' '.join(sorted(set(q[2] for x in arts for q in x['prices']))),
        price_date=' '.join(sorted(set(str(x['priceDate']) for x in arts))),
        progId=' '.join(sorted(set(str(x['progId']) for x in arts))),
        region=' '.join(sorted(set(str(x['region']) for x in arts)))))
with open(OUT + '/obx_inventory.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(inv[0].keys()))
    w.writeheader()
    w.writerows(inv)


def fm(r):
    return {n: v for n, v, _ in r['features']}


def rd(n):
    return [l.rstrip('\r\n').split(';') for l in open(DB + n, encoding='latin-1')]


art = {a[0]: a for a in rd('ocd_article.csv')}
sch = {r[0]: r for r in csv.reader(open(DB + 'ocd_codescheme.csv', newline='', encoding='latin-1'), delimiter=';')}
price = rd('ocd_price.csv')

D = [r for r in rows if r['base'].startswith('NODLE') and 'Mismatch' not in r['file']]
L = [r for r in rows if r['base'].startswith('MI')]
print('Dalby pCon exports (excl Price_Mismatch):', len(D), ' Lino:', len(L))


def walk(r, ocd_art, ocd_sch):
    s = ocd_sch[ocd_art[r['base']][10]][1]
    f = fm(r)
    out = ''
    pos = 0
    for tok in s.split(','):
        if tok == '@':
            out += r['base'][pos:pos + 1]
            pos += 1
        elif ':' in tok:
            out += f.get(tok.split(':')[1], '') or ''
        else:
            out += tok
    return out


c = collections.Counter()
for r in D:
    c['dalby final==scheme walk', walk(r, art, sch) == r['final']] += 1
program_dir = Path(DB).parents[2]
LDB = str(program_dir.with_name('lino') / Path(DB).relative_to(program_dir)) + os.sep
if os.path.exists(LDB + 'ocd_article.csv'):
    la = {a[0]: a for a in (l.rstrip('\r\n').split(';') for l in open(LDB + 'ocd_article.csv', encoding='latin-1'))}
    ls = {r[0]: r for r in csv.reader(open(LDB + 'ocd_codescheme.csv', newline='', encoding='latin-1'), delimiter=';')}
    for r in L:
        c['lino final==scheme walk', walk(r, la, ls) == r['final']] += 1
for r in D + L:
    ov = [kv.split('=', 1)[1] for kv in r['ofmlvarcode'].split(';')]
    c['varcode == final@space-joined ofml values', r['varcode'] == r['final'] + '@' + ' '.join(ov)] += 1
    f = fm(r)
    for tok in r['propVarCode'].split(';'):
        k, v = tok.split('=', 1)
        name = k.replace('__', '_')
        if v == '""':
            c['propVarCode empty-string == empty feature', f.get(name) in ('', None)] += 1
        elif v == '@VOID':
            c['propVarCode @VOID == feature omitted', name not in f] += 1
        else:
            val = f.get(name)
            c['propVarCode @value (+"_" if leading digit)', v == '@' + ('_' + val if val[:1].isdigit() else val)] += 1

MDF = set('Q01 Q02 Q03 Q04 Q05 Q07 Q08 Q09 Q10 Q11 Q12 Q23 Q32 Q54 Q55 Q66 Q72 Q74 Q75 Q76 Q77 Q79 Q83 Q84'.split())
casc = collections.Counter()
for r in D:
    f = fm(r)
    t = f['Top_Finish']
    exp = 'MDF' if t in MDF else (t if t in ('OAK', 'WLN', 'BRC', 'WRC') else None)
    c['Bottom_Material_G == OCD-derived value', f.get('Bottom_Material_G') == exp] += 1
    exp_se = t if t in ('BSE', 'WSE') else None
    c['Bottom_Stright_Edge == OCD-derived value', f.get('Bottom_Stright_Edge') == exp_se] += 1
    c['Bottom_WFT == Bottom_Material_G or Bottom_Stright_Edge',
      f.get('Bottom_WFT') == (f.get('Bottom_Material_G') or f.get('Bottom_Stright_Edge'))] += 1
    casc[(t if t not in MDF else 'Q*', f.get('Bottom_Material_G'), f.get('Bottom_Stright_Edge'), f.get('Bottom_WFT'))] += 1

KEYS = (('Access_Cutout', '6821'), ('Cable_leg', '7030'), ('Frame_Finish', '6699'), ('Top_Finish', '6695'))


def calc(r):
    cur = r['prices'][0][2]
    d = r['priceDate'].replace('-', '')
    f = fm(r)
    keys = ['']
    keys += [f'{k}={f[p]}' for p, k in KEYS if f.get(p)]
    amt = []
    for vc in keys:
        rows_ = [p for p in price if p[0] == r['base'] and p[1] == vc and p[2] == 'S' and p[8] == cur
                 and p[9] <= d <= p[10] and p[11] == '1']
        if len(rows_) > 1:
            return None
        if rows_:
            amt.append((vc, float(rows_[0][6])))
    return amt


def sale_of(r):
    return float([p for p in r['prices'] if p[0] == 'sale' and p[1] == '1'][0][3])


for r in D:
    amt = calc(r)
    sale = sale_of(r)
    ok = amt is not None and abs(sum(a for _, a in amt) - sale) < 1e-9
    c['price total == OCD recompute (OBX priceDate+currency)', ok] += 1
    pc = [float(x[1]) for x in r['comps']]
    exp = [a / sale * 100 for _, a in amt] if len(amt) > 1 else []
    c['priceComponents == % of total (none when base only)',
      len(pc) == len(exp) and all(abs(x - y) < 1e-6 for x, y in zip(pc, exp))] += 1
    c['purchase==sale', len(set(p[3] for p in r['prices'])) == 1] += 1
for k, v in sorted(c.items(), key=str):
    print(k, v)
print('cascade table:')
for k, v in sorted(casc.items(), key=str):
    print(' ', k, v)

with open(OUT + '/dalby_articles.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['file', 'base', 'final', 'varcode', 'ofmlvarcode', 'Frame_Finish', 'Top_Finish', 'Bottom_Material_G',
                'Bottom_Stright_Edge', 'Bottom_WFT', 'Access_Cutout', 'Cable_leg', 'currency', 'sale_price',
                'price_date', 'n_components', 'geometryChecksum', 'addStateCode_types'])
    for r in rows:
        if not r['base'].startswith('NODLE'):
            continue
        x = fm(r)
        w.writerow([r['file'], r['base'], r['final'], r['varcode'], r['ofmlvarcode']]
                   + [x.get(k, '') for k in ('Frame_Finish', 'Top_Finish', 'Bottom_Material_G', 'Bottom_Stright_Edge',
                                              'Bottom_WFT', 'Access_Cutout', 'Cable_leg')]
                   + [r['prices'][0][2], sale_of(r), r['priceDate'], len(r['comps']), r['geo'], '+'.join(r['addState'])])

S = [r for r in D if r['file'] == '2_Dalby_Side_Table_GBP.obx']
pv = {}
tx = {}
for p in rd('ocd_propertyvalue.csv'):
    if p[0] == 'DALBY_OPT' and p[1] == 'Top_Finish':
        pv[p[8]] = (int(p[3]), p[4])
for l in open(DB + 'ocd_propvaluetext.csv', encoding='latin-1'):
    m = re.match(r'0*(\d+);en;[^;]*;[^;]*;"(.*)"', l)
    if m:
        tx[int(m[1])] = m[2]
obx_top = collections.Counter(fm(r)['Top_Finish'] for r in S)


def rows6695(cur, v):
    return [p for p in price if p[0] == 'NODLE150' and p[1] == '6695=' + v and p[8] == cur and p[9] <= '20251027' <= p[10]]


with open(OUT + '/top_finish_reconciliation.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Top_Finish', 'value_rel_obj', 'english_text', 'text_contains_forbo', 'in_OBX_2_GBP', 'obx_articles',
                'GBP_6695_rows_20251027', 'EUR_6695_rows_20251027'])
    for v, (tid, ro) in pv.items():
        w.writerow([v, ro, tx.get(tid, ''), 'forbo' in tx.get(tid, '').lower(), v in obx_top, obx_top.get(v, 0),
                    '/'.join(p[6] for p in rows6695('GBP', v)), '/'.join(p[6] for p in rows6695('EUR', v))])

with open(OUT + '/side_table_gbp_56.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['#', 'final', 'varcode', 'ofmlvarcode', 'Frame', 'Top', 'BM_G', 'BSE', 'WFT', 'GBP_total', 'components_pct'])
    for i, r in enumerate(S, 1):
        x = fm(r)
        w.writerow([i, r['final'], r['varcode'], r['ofmlvarcode'], x['Frame_Finish'], x['Top_Finish'],
                    x.get('Bottom_Material_G', ''), x.get('Bottom_Stright_Edge', ''), x.get('Bottom_WFT', ''),
                    sale_of(r), '|'.join(f"{n}={float(v):.3f}" for n, v in r['comps'])])
print('2_GBP distinct (base,frame,top):', len({(r['base'], fm(r)['Frame_Finish'], fm(r)['Top_Finish']) for r in S}),
      collections.Counter(r['base'] for r in S), 'tops', len(obx_top),
      collections.Counter(fm(r)['Frame_Finish'] for r in S))
