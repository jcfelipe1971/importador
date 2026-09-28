# -*- coding: utf-8 -*-
"""
merge2maxfactu.py - Conversor Merge (Delphi 6) -> patrón MaxFactu (Delphi 13, FireDAC, VCL estándar)

Uso:
  Módulo (DM + formulario):
    python merge2maxfactu.py --merge RUTA_MERGE --maxfactu RUTA_MAXFACTU --dm UDMProveedores
                             --form UFMProveedores --salida DIR
  Solo módulo de datos:
    python merge2maxfactu.py --merge RUTA_MERGE --maxfactu RUTA_MAXFACTU --dm UDMListados --salida DIR
  Unit sin DFM (una o varias, separadas por comas):
    python merge2maxfactu.py --merge RUTA_MERGE --maxfactu RUTA_MAXFACTU --unit UDameDato,uFBusca --salida DIR
"""
import argparse, os, re, json, collections, datetime
import dfmparser as dp
from tipos import Tipos, tabla_de
import conv_dfm as cd
import conv_pas as cp


def lee(ruta):
    with open(ruta, 'rb') as f:
        b = f.read()
    if b.startswith(b'\xef\xbb\xbf'):
        return b[3:].decode('utf-8')
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b.decode('cp1252')


def escribe(ruta, txt, bom=True):
    with open(ruta, 'wb') as f:
        if bom:
            f.write(b'\xef\xbb\xbf')
        f.write(txt.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8'))


def api_maxfactu(dir_mf):
    ent = lee(os.path.join(dir_mf, 'UEntorno.pas')).split('implementation')[0]
    api_e = set(re.findall(r'property\s+(\w+)', ent))
    for g in re.findall(r'^\s+([\w, ]+):\s*[\w\[\]\. ]+;', ent, re.M):
        api_e |= {x.strip() for x in g.split(',')}
    api_e |= set(re.findall(r'(?:procedure|function)\s+(\w+)', ent))
    dm = lee(os.path.join(dir_mf, 'UDMMain.pas'))
    iface = dm.split('implementation')[0]
    api_d = set(re.findall(r'(?:procedure|function)\s+(\w+)', iface))
    for g in re.findall(r'^\s+([\w, ]+):\s*[\w\[\]\.<> ]+;', iface, re.M):
        api_d |= {x.strip() for x in g.split(',')}
    return api_e, api_d


def vp_es_evento(p):
    import vcl_props
    return vcl_props.es_evento(p)


def mover_toolbar(frame):
    pnl = next((c for c in frame.children if c.name == 'PNLMain'), None)
    if not pnl:
        return
    tb = next((c for c in pnl.children if c.name == 'TBMain'), None)
    if tb:
        pnl.children.remove(tb)
        frame.children.insert(1, tb)


def parchea_fmmain(a, inf):
    usados = getattr(inf, 'fmain_usados', set())
    if not usados:
        return
    import conv_fmmain as cf
    ruta_sal = os.path.join(a.salida, 'UFMMain.pas')
    base = lee(ruta_sal) if os.path.exists(ruta_sal) else lee(os.path.join(a.maxfactu, 'UFMMain.pas'))
    dfm_m = os.path.join(a.merge, 'UFMain.dfm')
    nuevo, nombres = cf.parchea(base, lee(os.path.join(a.merge, 'UFMain.pas')),
                                lee(dfm_m) if os.path.exists(dfm_m) else None, usados, inf)
    if nombres:
        escribe(ruta_sal, nuevo)
        print('UFMMain.pas completado con:', ', '.join(nombres))


def informe_final(a, inf, tipos, ctx):
    parchea_fmmain(a, inf)
    if getattr(tipos, 'bd', None) is not None:
        for e in tipos.bd.errores:
            inf.revisar.append('SQL que la base de datos no acepta: ' + e)
        tipos.bd.cierra()
    nombre = a.form or a.dm or (a.unit.split(',')[0].strip() if a.unit else 'UUtilesMerge')
    datos = {'contadores': inf.contadores, 'bloqueantes': inf.bloqueantes, 'revisar': inf.revisar, 'auto': inf.auto,
             'quitados': inf.quitados, 'tipos': dict(tipos.stats)}
    if ctx is not None:
        datos.update({'buscadores': ctx.buscadores, 'datasources_locales': ctx.ds_usados})
    json.dump(datos, open(os.path.join(a.salida, 'informe_%s.json' % nombre), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    with open(os.path.join(a.salida, 'informe_%s.txt' % nombre), 'w', encoding='utf-8') as f:
        f.write('BLOQUEANTES: IMPIDEN CARGAR EL DFM (%d)\n' % len(inf.bloqueantes))
        for x in inf.bloqueantes:
            f.write('  - %s\n' % x)
        f.write('\nPENDIENTES DE REVISAR (%d)\n' % len(inf.revisar))
        for x in inf.revisar:
            f.write('  - %s\n' % x)
        f.write('\nCONVERSIONES AUTOMATICAS\n')
        for x in inf.auto:
            f.write('  - %s\n' % x)
    print('Contadores:')
    for k, v in sorted(inf.contadores.items()):
        print('  %-45s %d' % (k, v))
    print('BLOQUEANTES:', len(inf.bloqueantes), '| Pendientes de revisar:', len(inf.revisar),
          '-> ver informe_%s.txt' % nombre)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--merge', required=True)
    ap.add_argument('--maxfactu', required=True)
    ap.add_argument('--dm')
    ap.add_argument('--form')
    ap.add_argument('--sin-teechart', action='store_true', help='TeeChart VCL no instalado: gráficos -> TPanel')
    ap.add_argument('--stub', help='units de Merge para las que generar STUB (interfaz convertida, cuerpo vacío)')
    ap.add_argument('--uutiles-merge', help='carpeta(s) con código ya convertido, separadas por comas: genera '
                                            'UUtilesMerge.pas con las rutinas de UUtiles de Merge que usan')
    ap.add_argument('--bd', help='base de datos Firebird para leer los tipos reales, p.ej. localhost:C:\\datos\\EMPRESA.FDB')
    ap.add_argument('--bd-usuario', default='SYSDBA')
    ap.add_argument('--bd-clave', default='masterkey')
    ap.add_argument('--fbclient', help='ruta de fbclient.dll / libfbclient.so si no está en el PATH')
    ap.add_argument('--unit', help='units .pas sin DFM, separadas por comas')
    ap.add_argument('--salida', required=True)
    ap.add_argument('--base', default='TFRMMantenimientoSimple')
    ap.add_argument('--equivalencias', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                             'equivalencias.txt'),
                    help='fichero "origen => destino" con renombres propios (por defecto equivalencias.txt)')
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    for ruta, que in ((a.merge, '--merge'), (a.maxfactu, '--maxfactu')):
        if not os.path.isdir(ruta):
            ap.error('%s: no existe la carpeta %s' % (que, ruta))
    if not os.path.exists(os.path.join(a.maxfactu, 'UEntorno.pas')):
        ap.error('--maxfactu debe apuntar a la carpeta de fuentes de MaxFactu (donde está UEntorno.pas)')

    cd.SIN_TEECHART = a.sin_teechart
    tipos = Tipos(a.maxfactu)
    tipos.bd = None
    import tipos_bd
    if a.bd or os.path.exists(tipos_bd.CACHE):
        try:
            tipos.bd = tipos_bd.TiposBD(a.bd, a.bd_usuario, a.bd_clave, a.fbclient)
            tipos.bd.aprende_de_maxfactu(a.maxfactu)
        except Exception as e:
            print('AVISO: no se pueden leer los tipos de la base de datos (%s); se usarán reglas.' % e)
            tipos.bd = None
    cd.carga_bases_merge(a.merge)
    inf = cd.Informe()
    inf.api_entorno, inf.api_dmmain = api_maxfactu(a.maxfactu)
    import glob
    inf.units_maxfactu = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(a.maxfactu, '*.pas'))}
    inf.units_maxfactu |= {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(a.maxfactu, 'Utilidades', '*.pas'))}
    inf.units_maxfactu |= {'UControlConcurrencia', 'UBuscadorCampo', 'UAuxMerge', 'UCompatMerge', 'UFormGest', 'gnugettext', 'ShellAPI', 'Math', 'StrUtils',
                           'DateUtils', 'Variants', 'IniFiles', 'Clipbrd', 'Printers', 'Registry', 'ComObj', 'ActiveX'}
    inf.dir_merge = a.merge
    inf.equivalencias = cp.carga_equivalencias(a.equivalencias)
    inf.units_convertidas = set()
    if a.dm: inf.units_convertidas.add(a.dm)
    if a.form: inf.units_convertidas.add('UFRM' + a.form[3:])
    if a.unit: inf.units_convertidas |= {u.strip() for u in a.unit.split(',') if u.strip()}
    if a.uutiles_merge:
        import stubs, glob as _g
        textos = []
        for d in a.uutiles_merge.split(','):
            for f in _g.glob(os.path.join(d.strip(), '*.pas')):
                textos.append(lee(f))
        inf.units_convertidas.add('UUtilesMerge')
        txt = stubs.genera_uutiles_merge(lee(os.path.join(a.merge, 'UUtiles.pas')),
                                         lee(os.path.join(a.maxfactu, 'UUtiles.pas')), textos, inf,
                                         [lee(f) for f in _g.glob(os.path.join(a.maxfactu, '*.pas'))])
        escribe(os.path.join(a.salida, 'UUtilesMerge.pas'), txt)
        informe_final(a, inf, tipos, None)
        return
    if a.stub:
        import stubs
        inf.units_convertidas |= {u.strip() for u in a.stub.split(',') if u.strip()} | {'UTiposPendientesMerge'}
        import glob as _g
        idx = {os.path.basename(p)[:-4].lower(): p for p in _g.glob(os.path.join(a.merge, '**', '*.pas'), recursive=True)}
        for u in [x.strip() for x in a.stub.split(',') if x.strip()]:
            ruta = idx.get(u.lower())
            if not ruta:
                print('No encuentro', u); continue
            nombre = os.path.basename(ruta)[:-4]
            txt = stubs.genera(lee(ruta), inf, nombre + '.pas')
            if nombre.lower() == 'ufmain':
                txt = stubs.adapta_fmain(txt, lee(os.path.join(a.maxfactu, 'UFMMain.pas')), inf)
            escribe(os.path.join(a.salida, nombre + '.pas'), txt)
        if stubs.TIPOS_PENDIENTES:
            ruta_tp = os.path.join(a.salida, 'UTiposPendientesMerge.pas')
            if os.path.exists(ruta_tp):
                stubs.TIPOS_PENDIENTES.update(re.findall(r'^\s*(T\w+) = class', lee(ruta_tp), re.M))
            escribe(ruta_tp, stubs.unidad_tipos_pendientes())
        print('Stubs generados:', a.stub)
        return
    if not (a.dm or a.form or a.unit):
        ap.error('indica --unit, --dm o --dm y --form')
    if a.form and not a.dm:
        ap.error('--form necesita también --dm (el módulo de datos del formulario)')

    if a.unit:
        for u in [x.strip() for x in a.unit.split(',') if x.strip()]:
            u = u[:-4] if u.lower().endswith('.pas') else u
            ruta = os.path.join(a.merge, u + '.pas')
            if not os.path.exists(ruta):
                print('No encuentro', ruta); continue
            if os.path.exists(os.path.join(a.merge, u + '.dfm')):
                print('AVISO: %s tiene .dfm; si es un DM usa --dm, si es un formulario --dm y --form.' % u)
            escribe(os.path.join(a.salida, u + '.pas'), cp.convierte_pas_unit(lee(ruta), inf, u + '.pas'))
            print('Convertida', u)
        informe_final(a, inf, tipos, None)
        return

    # ---------------- Módulo de datos ----------------
    if not a.form:
        dm_root = dp.parse(lee(os.path.join(a.merge, a.dm + '.dfm')))
        dm_new, bloqueos = cd.convierte_dm(dm_root, tipos, inf)
        campos_tipos = {n.name: n.cls for n in dm_new.walk() if n.cls.endswith('Field')}
        updates = [n.name for n in dm_new.children if n.cls == 'TFDUpdateSQL']
        trans = [n.name for n in dm_new.children if n.cls == 'TFDTransaction']
        ren_tr = {r'(%s)\\.InTransaction\\b' % '|'.join(trans): r'\\1.Active'} if trans else {}
        escribe(os.path.join(a.salida, a.dm + '.dfm'), dp.dumps(dm_new), bom=False)
        escribe(os.path.join(a.salida, a.dm + '.pas'),
                cp.convierte_pas_dm(lee(os.path.join(a.merge, a.dm + '.pas')), inf, a.dm + '.pas', campos_tipos,
                                    updates, bloqueos, ren_tr))
        informe_final(a, inf, tipos, None)
        return
    dm_dfm = lee(os.path.join(a.merge, a.dm + '.dfm'))
    dm_pas = lee(os.path.join(a.merge, a.dm + '.pas'))
    dm_root = dp.parse(dm_dfm)
    dm_new, bloqueos = cd.convierte_dm(dm_root, tipos, inf)
    campos_tipos = {n.name: n.cls for n in dm_new.walk() if n.cls.endswith('Field')}
    updates = [n.name for n in dm_new.children if n.cls == 'TFDUpdateSQL']
    trans = [n.name for n in dm_new.children if n.cls == 'TFDTransaction']
    ren_tr = {r'(%s)\.InTransaction\b' % '|'.join(trans): r'\1.Active'} if trans else {}
    dm_pas_new = cp.convierte_pas_dm(dm_pas, inf, a.dm + '.pas', campos_tipos, updates, bloqueos, ren_tr)
    escribe(os.path.join(a.salida, a.dm + '.dfm'), dp.dumps(dm_new), bom=False)
    escribe(os.path.join(a.salida, a.dm + '.pas'), dm_pas_new)

    # ---------------- Formulario -> Frame ----------------
    f_dfm = lee(os.path.join(a.merge, a.form + '.dfm'))
    f_pas = lee(os.path.join(a.merge, a.form + '.pas'))
    f_root = dp.parse(f_dfm)
    form_name = f_root.name                      # FMProveedores
    form_cls = f_root.cls                        # TFMProveedores
    base_name = form_name[2:]                    # Proveedores
    frame_name, frame_cls, frame_unit = 'FRM' + base_name, 'TFRM' + base_name, 'UFRM' + base_name
    dm_name = dm_root.name                       # DMProveedores
    ctx = cd.Contexto(dm_name, dm_root)
    q_princ = None
    for cand in (f_root.find('NavMain'), f_root.find('DBGMain')):
        if cand is not None and cand.get('DataSource'):
            ds = cand.getv('DataSource').split('.')[-1]
            q_princ = ctx.datasources.get(ds)
            break
    qn = dm_root.find(q_princ) if q_princ else None
    if qn is not None and any((c.getv('FieldName') or '').strip("'").upper() == 'TITULO' for c in qn.children):
        inf.titulo_adjunto = 'DM.%sTITULO.AsString' % q_princ
    ctx.firmas = cd.firmas_pas(f_pas, form_cls)
    ctx.tipos = tipos
    frame = cd.convierte_form(f_root, ctx, inf, frame_name, frame_cls)
    mover_toolbar(frame)
    # (1) Nombres que ya existen en la base de MaxFactu (TFRMMantenimientoSimple y sus ancestros):
    #     un componente propio con el mismo nombre da "A component named X already exists" al crearse.
    base_nombres = set()
    for bn in ('UFRMSimple', 'UFRMNavegador', 'UFRMMantenimientoSimple'):
        ruta_b = os.path.join(a.maxfactu, bn + '.dfm')
        if os.path.exists(ruta_b):
            rb = dp.parse(lee(ruta_b))
            base_nombres |= {n.name.lower() for n in rb.walk() if n is not rb}
    renombres = {}
    for n in frame.walk():
        if n is not frame and n.kind == 'object' and n.name.lower() in base_nombres:
            nuevo = n.name + 'Merge'
            renombres[n.name] = nuevo
            inf.auto.append('%s -> %s (el nombre ya existe en la base de MaxFactu)' % (n.name, nuevo))
            n.name = nuevo
    if renombres:
        patron = re.compile(r'\b(%s)\b' % '|'.join(map(re.escape, renombres)))
        for n in frame.walk():
            for p in n.props:
                if not vp_es_evento(p[0]):
                    p[1] = [patron.sub(lambda mm: renombres[mm.group(1)], v) for v in p[1]]
    # (2) Componentes de Merge que no llegan al DFM final (eliminados con su padre, FR2, gráficos...)
    finales = {n.name.lower() for n in frame.walk()}
    eliminados = sorted({n.name for n in f_root.walk() if n is not f_root and n.name.lower() not in finales
                         and n.name not in renombres})
    principal_q = ctx.datasources.get(ctx.principal, '')

    for viejo, nuevo in renombres.items():
        f_pas = re.sub(r'\b%s\b' % re.escape(viejo), nuevo, f_pas)
    frame_pas = cp.convierte_pas_frame(f_pas, inf, frame_unit + '.pas', form_cls, frame_cls, frame_unit, a.base,
                                       'T' + dm_name, dm_name, ctx.ds_usados, ctx.principal, principal_q,
                                       ctx.buscadores, ctx, dict({r'PEdit\b': 'SBFicha', r'PMain\b': 'PNLMain', r'ALMain\b': 'Acciones'},
                                            **{r'(DM\.(?:%s))\.InTransaction\b' % '|'.join(trans): r'\1.Active'}), eliminados)
    # miembros de la jerarquía Merge usados en el código y ausentes en la base MaxFactu
    mm = set()
    for u in ('UFPEdit', 'UFPEditSimple', 'UFPEditSinNavegador', 'UFormGest'):
        p = os.path.join(a.merge, u + '.pas')
        if os.path.exists(p):
            mm |= cp.miembros_clase(lee(p))
    mf = set()
    for u in ('UFRMMantenimientoSimple', 'UFRMNavegador', 'UFRMSimple', 'UUtiles', 'UUtilGuardaConfiguracion'):
        p = os.path.join(a.maxfactu, u + '.pas')
        if os.path.exists(p):
            mf |= cp.miembros_clase(lee(p))
    mf |= {'Create', 'Destroy', 'Name', 'Owner', 'Parent', 'Handle', 'Width', 'Height', 'Visible', 'Enabled',
           'Tag', 'Hint', 'Left', 'Top', 'Align', 'Font', 'Color', 'Caption', 'Show', 'Hide', 'Free'}
    propios = cp.miembros_clase(frame_pas) | {n.name for n in frame.walk()}
    cp.avisa_miembros_base(frame_pas, inf, frame_unit + '.pas', mm, mf, propios)
    escribe(os.path.join(a.salida, frame_unit + '.dfm'), dp.dumps(frame), bom=False)
    escribe(os.path.join(a.salida, frame_unit + '.pas'), frame_pas)

    # ---------------- Script de verificación de tipos ----------------
    tablas = sorted({tabla_de(n.strings('SQL.Strings')) for n in dm_new.walk() if n.cls == 'TFDQuery'} - {''})
    sql = ['-- Tipos reales de los campos usados por los datasets convertidos (ejecutar en IBExpert/isql)',
           'SELECT TRIM(rf.RDB$RELATION_NAME) AS TABLA, TRIM(rf.RDB$FIELD_NAME) AS CAMPO,',
           '       f.RDB$FIELD_TYPE AS TIPO, f.RDB$FIELD_SUB_TYPE AS SUBTIPO, f.RDB$FIELD_SCALE AS ESCALA,',
           '       f.RDB$FIELD_PRECISION AS PRECISION, f.RDB$CHARACTER_LENGTH AS LONGITUD',
           'FROM RDB$RELATION_FIELDS rf JOIN RDB$FIELDS f ON f.RDB$FIELD_NAME = rf.RDB$FIELD_SOURCE',
           'WHERE rf.RDB$RELATION_NAME IN (%s)' % ', '.join("'%s'" % t for t in tablas),
           'ORDER BY 1, rf.RDB$FIELD_POSITION;', '']
    escribe(os.path.join(a.salida, 'verifica_tipos.sql'), '\n'.join(sql), bom=False)

    informe_final(a, inf, tipos, ctx)


if __name__ == '__main__':
    main()
