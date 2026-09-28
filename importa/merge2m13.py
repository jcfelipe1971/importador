# -*- coding: utf-8 -*-
"""
merge2m13.py - Importa módulos de Merge (Delphi 6) en Merge13 (Delphi 13, ventanas con la API de Merge).

  python merge2m13.py --merge C:\\Delfos\\Proyectos\\Merge --proyecto C:\\Delfos\\Merge13
                      --maxfactu C:\\Delfos\\maxfactu --modulo UFMFamilias
                      [--bd localhost:C:\\Datos\\EMPRESA.FDB] [--fbclient ruta\\fbclient.dll] [--sin-teechart]

- El formulario se queda como formulario (misma unit, clase y base TFPEdit...), en <proyecto>\\Merge\\<carpeta de Merge>.
- Su módulo de datos (UDMxxx) se convierte también (FIB -> FireDAC con los tipos reales de la base de datos).
- Units de Merge de las que depende y aún no existen: las pequeñas se convierten; formularios y listados se crean
  como STUB en <proyecto>\\Pendientes (interfaz real, cuerpo vacío) hasta que se importen.
- La acción de FMain que abría el módulo en Merge queda registrada (aparece en el menú).
- Merge13.dpr se actualiza solo. Se puede volver a importar un módulo cuantas veces haga falta.
"""
import argparse, os, re, glob, shutil, json
import dfmparser as dp
import conv_dfm as cd
import conv_pas as cp
from tipos import Tipos
import merge2maxfactu as m2

AQUI = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK = ['UBuscadorCampo.pas', 'UControlConcurrencia.pas', 'UAuxMerge.pas']


def indice_merge(dir_merge):
    idx = {}
    for p in glob.glob(os.path.join(dir_merge, '**', '*.pas'), recursive=True):
        idx.setdefault(os.path.basename(p)[:-4].lower(), p)
    return idx


def units_proyecto(proy):
    return {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(proy, '**', '*.pas'), recursive=True)
            if '_dcu' not in p and '__history' not in p}


def uses_de(src):
    t = cp._limpia_comentarios(src)
    out = []
    for m in re.finditer(r'\buses\b(.*?);', t, re.S | re.I):
        out += [x.strip().split()[0] for x in m.group(1).split(',') if x.strip()]
    return out


def registro_de(src_ufmain, form_cls, form_var):
    """En Merge, qué acción de FMain abría el formulario y con qué método se le pasaba el filtro."""
    m = re.search(r'procedure TFMain\.(\w+)Execute\(Sender: TObject\);(?:(?!\nend;).)*?AbreForm\(\s*%s\s*,\s*%s\b(.*?)\nend;'
                  % (form_cls, form_var), src_ufmain, re.S | re.I)
    if not m:
        return None
    filtro = re.search(r'%s\.(\w+)\(\s*FiltroAccion\s*\)' % form_var, m.group(2), re.I)
    return "RegistraModulo('%s', %s, @%s%s);" % (m.group(1), form_cls, form_var,
                                                 (", '%s'" % filtro.group(1)) if filtro else '')


def actualiza_dpr(proy, dpr='Merge13.dpr'):
    ruta = os.path.join(proy, dpr)
    t = m2.lee(ruta)
    t = re.sub(r'\s*\{MERGE2M13-INICIO\}.*?\{MERGE2M13-FIN\}', '', t, flags=re.S)
    lineas = []
    for sub in ('Conversion', 'Pendientes', 'Merge'):
        for p in sorted(glob.glob(os.path.join(proy, sub, '**', '*.pas'), recursive=True)):
            rel = os.path.relpath(p, proy).replace('/', '\\')
            u = os.path.basename(p)[:-4]
            dfm = os.path.exists(p[:-4] + '.dfm')
            comp = ''
            if dfm:
                r = dp.parse(m2.lee(p[:-4] + '.dfm'))
                comp = ' {%s%s}' % (r.name, ': TDataModule' if r.cls.startswith('TDM') else '')
            lineas.append("  %s in '%s'%s," % (u, rel, comp))
    bloque = '\n  {MERGE2M13-INICIO} // units importadas de Merge (las mantiene merge2m13.py)\n' + '\n'.join(lineas) + \
             '\n  {MERGE2M13-FIN}'
    t = re.sub(r"(UMensajesDeError in 'UMensajesDeError.pas',)", lambda m: m.group(1) + bloque, t, count=1)
    m2.escribe(ruta, t, bom=False)
    return len(lineas)


def main():
    ap = argparse.ArgumentParser(description='Importa módulos de Merge en Merge13')
    ap.add_argument('--merge', required=True)
    ap.add_argument('--proyecto', required=True)
    ap.add_argument('--maxfactu', required=True, help='MaxFactu como referencia de tipos FireDAC')
    ap.add_argument('--modulo', help='formulario de Merge, p.ej. UFMFamilias')
    ap.add_argument('--dm', help='módulo de datos (si no se indica se deduce: UFMxxx -> UDMxxx)')
    ap.add_argument('--unit', help='units sin DFM, separadas por comas')
    ap.add_argument('--bd')
    ap.add_argument('--bd-usuario', default='SYSDBA')
    ap.add_argument('--bd-clave', default='masterkey')
    ap.add_argument('--fbclient')
    ap.add_argument('--sin-teechart', action='store_true')
    a = ap.parse_args()
    proy = a.proyecto
    cp.PERFIL = 'merge13'
    cd.MODO_M13 = True
    cd.SIN_TEECHART = a.sin_teechart
    cd.carga_bases_m13(proy)
    cd.carga_bases_merge(a.merge)
    for sub in ('Conversion', 'Pendientes', 'Merge', os.path.join('Conversion', 'informes')):
        os.makedirs(os.path.join(proy, sub), exist_ok=True)
    for f in FRAMEWORK:
        origen = os.path.join(AQUI, 'framework', f)
        if os.path.exists(origen):
            t = m2.lee(origen)
            if f == 'UAuxMerge.pas':
                # En Merge13 FMain y UFormGest (AbreForm, AbreData...) ya existen con la API de Merge
                t = re.sub(r'\bUFMMain\b', 'UFMain', re.sub(r'\bFMMain\b', 'FMain', t))
                for r in ('AbreData', 'AbreDataVarias', 'CierraData', 'AbreForm', 'CierraForm', 'AbreFrame'):
                    t = re.sub(r'\n(?:procedure|function) %s\([^)]*\)[^;]*;' % r, '', t, count=1)
                    t = re.sub(r'\n(?:procedure|function) %s\(.*?\nend;\n' % r, '\n', t, count=1, flags=re.S)
                t = t.replace('// ---- UFormGest de Merge ----', '')
            m2.escribe(os.path.join(proy, 'Conversion', f), t)
    idx = indice_merge(a.merge)
    inf = cd.Informe()
    inf.api_entorno, inf.api_dmmain = m2.api_maxfactu(proy)
    inf.units_maxfactu = units_proyecto(proy) | {'UControlConcurrencia', 'UBuscadorCampo', 'UAuxMerge', 'UUtilesMerge',
                                                  'UTiposPendientesMerge', 'UModulos', 'UFormGest'}
    inf.dir_merge = a.merge
    inf.dir_proyecto = proy
    inf.equivalencias = cp.carga_equivalencias(os.path.join(AQUI, 'equivalencias.txt'))
    inf.units_convertidas = set()
    tipos = Tipos(a.maxfactu)
    tipos.bd = None
    import tipos_bd
    if a.bd or os.path.exists(tipos_bd.CACHE):
        try:
            tipos.bd = tipos_bd.TiposBD(a.bd, a.bd_usuario, a.bd_clave, a.fbclient)
            tipos.bd.aprende_de_maxfactu(a.maxfactu)
        except Exception as e:
            print('AVISO: sin tipos de la base de datos (%s)' % e)
    convertidas = []

    def destino(u):
        rel = os.path.relpath(os.path.dirname(idx[u.lower()]), a.merge)
        d = os.path.join(proy, 'Merge', '' if rel == '.' else rel)
        os.makedirs(d, exist_ok=True)
        return d

    if a.modulo:
        form = a.modulo
        dm = a.dm or ('UDM' + form[3:] if form.upper().startswith('UFM') else None)
        if dm and dm.lower() not in idx:
            dm = None
        inf.units_convertidas |= {form} | ({dm} if dm else set())
        # ---- módulo de datos
        if dm:
            ruta = idx[dm.lower()]
            dm_root = dp.parse(m2.lee(ruta[:-4] + '.dfm'))
            dm_new, bloqueos = cd.convierte_dm(dm_root, tipos, inf)
            campos_tipos = {n.name: n.cls for n in dm_new.walk() if n.cls.endswith('Field')}
            updates = [n.name for n in dm_new.children if n.cls == 'TFDUpdateSQL']
            trans = [n.name for n in dm_new.children if n.cls == 'TFDTransaction']
            ren_tr = {r'(%s)\.InTransaction\b' % '|'.join(trans): r'\1.Active'} if trans else {}
            d = destino(dm)
            m2.escribe(os.path.join(d, os.path.basename(ruta)[:-4] + '.dfm'), dp.dumps(dm_new), bom=False)
            m2.escribe(os.path.join(d, os.path.basename(ruta)),
                       cp.convierte_pas_dm(m2.lee(ruta), inf, dm + '.pas', campos_tipos, updates, bloqueos, ren_tr))
            convertidas.append(dm)
        else:
            dm_root = dp.Node('object', 'DMNinguno', 'TDataModule')
        # ---- formulario
        ruta = idx[form.lower()]
        f_root = dp.parse(m2.lee(ruta[:-4] + '.dfm'))
        f_pas = m2.lee(ruta)
        ctx = cd.Contexto(dm_root.name, dm_root)
        ctx.firmas = cd.firmas_pas(f_pas, f_root.cls)
        ctx.tipos = tipos
        nuevo = cd.convierte_form_m13(f_root, ctx, inf)
        # nombres de componentes propios que ya existen en las bases de Merge13 -> se renombran
        ren = {}
        for n in nuevo.walk():
            if n is not nuevo and n.kind == 'object' and n.name in cd.BASE_M13:
                ren[n.name] = n.name + 'Merge'
                n.name = ren[n.name]
        for viejo, nv in ren.items():
            f_pas = re.sub(r'\b%s\b' % re.escape(viejo), nv, f_pas)
            inf.auto.append('%s -> %s (el nombre ya existe en la base de Merge13)' % (viejo, nv))
        finales = {n.name.lower() for n in nuevo.walk()}
        eliminados = sorted({n.name for n in f_root.walk() if n is not f_root and n.name.lower() not in finales
                             and n.name not in ren})
        form_var = f_root.name
        reg = registro_de(m2.lee(idx['ufmain']), f_root.cls, form_var)
        if not reg:
            inf.revisar.append('No se ha encontrado en FMain de Merge la acción que abre %s: registrar a mano.' % form)
        pas = cp.convierte_pas_form_m13(f_pas, inf, form + '.pas', f_root.cls, ctx, eliminados, reg)
        if getattr(ctx, 'formcreate_creado', False):
            nuevo.set('OnCreate', 'FormCreate')
        d = destino(form)
        m2.escribe(os.path.join(d, os.path.basename(ruta)[:-4] + '.dfm'), dp.dumps(nuevo), bom=False)
        m2.escribe(os.path.join(d, os.path.basename(ruta)), pas)
        convertidas.append(form)
        print('Convertido %s%s -> %s  (%s)' % (form, (' + ' + dm) if dm else '', os.path.relpath(d, proy),
                                               reg or 'sin registro en el menú'))
    for u in [x.strip() for x in (a.unit or '').split(',') if x.strip()]:
        ruta = idx[u.lower()]
        inf.units_convertidas.add(u)
        m2.escribe(os.path.join(destino(u), os.path.basename(ruta)), cp.convierte_pas_unit(m2.lee(ruta), inf, u + '.pas'))
        convertidas.append(u)
        print('Convertida', u)
    # ---- dependencias que faltan: STUB en Pendientes (se sustituyen al importarlas)
    import stubs
    existentes = {u.lower() for u in units_proyecto(proy)}
    pend_dir = os.path.join(proy, 'Pendientes')
    faltan, vistos = [], set()
    cola = []
    for u in convertidas:
        cola += uses_de(m2.lee(glob.glob(os.path.join(proy, 'Merge', '**', u + '.pas'), recursive=True)[0]))
    while cola:
        u = cola.pop()
        k = u.lower()
        if k in vistos or k in existentes or k not in idx or k in ('ufmain', 'uformgest', 'uentorno', 'udmmain', 'uutiles'):
            continue
        vistos.add(k)
        faltan.append(u)
        src = m2.lee(idx[k])
        cola += uses_de(re.split(r'\bimplementation\b', src, flags=re.I)[0])
    # units sin formulario (funciones): se convierten de verdad; formularios, listados y las de
    # m13_pendientes.txt: STUB en Pendientes
    forzados = set()
    rp = os.path.join(AQUI, 'm13_pendientes.txt')
    if os.path.exists(rp):
        forzados = {l.split('#')[0].strip().lower() for l in open(rp, encoding='utf-8') if l.split('#')[0].strip()}
    es_stub = lambda u: os.path.exists(idx[u.lower()][:-4] + '.dfm') or u.lower() in forzados
    reales = [u for u in faltan if not es_stub(u)]
    while reales:
        u = reales.pop(0)
        for x in uses_de(m2.lee(idx[u.lower()])):
            k = x.lower()
            if k in idx and k not in vistos and k not in existentes and \
                    k not in ('ufmain', 'uformgest', 'uentorno', 'udmmain', 'uutiles'):
                vistos.add(k)
                faltan.append(x)
                if not es_stub(x):
                    reales.append(x)
    inf.units_convertidas |= set(faltan) | {'UTiposPendientesMerge'}
    for u in faltan:
        nombre = os.path.basename(idx[u.lower()])[:-4]
        if es_stub(u):
            m2.escribe(os.path.join(pend_dir, nombre + '.pas'), stubs.genera(m2.lee(idx[u.lower()]), inf, nombre + '.pas'))
            for p in glob.glob(os.path.join(proy, 'Merge', '**', nombre + '.pas'), recursive=True):
                os.remove(p)
        else:
            m2.escribe(os.path.join(destino(u), nombre + '.pas'), cp.convierte_pas_unit(m2.lee(idx[u.lower()]), inf, nombre + '.pas'))
            convertidas.append(nombre)
            for p in glob.glob(os.path.join(pend_dir, nombre + '.*')):
                os.remove(p)
    faltan = [u for u in faltan if es_stub(u)]
    if stubs.TIPOS_PENDIENTES:
        rt = os.path.join(pend_dir, 'UTiposPendientesMerge.pas')
        if os.path.exists(rt):
            stubs.TIPOS_PENDIENTES.update(re.findall(r'^\s*(T\w+) = class', m2.lee(rt), re.M))
        m2.escribe(rt, stubs.unidad_tipos_pendientes())
    # un STUB que ya se ha importado de verdad sobra
    for u in convertidas:
        for p in glob.glob(os.path.join(pend_dir, u + '.*')):
            os.remove(p)
    if faltan:
        print('Pendientes (STUB):', ', '.join(sorted(faltan, key=str.lower)))
    # ---- rutinas de UUtiles de Merge que usa lo importado
    textos = [m2.lee(p) for p in glob.glob(os.path.join(proy, 'Merge', '**', '*.pas'), recursive=True)]
    textos += [m2.lee(p) for p in glob.glob(os.path.join(pend_dir, '*.pas'))]
    uu = stubs.genera_uutiles_merge(m2.lee(idx['uutiles']), m2.lee(os.path.join(proy, 'UUtiles.pas')), textos, inf,
                                    [m2.lee(f) for f in glob.glob(os.path.join(proy, '*.pas'))])
    m2.escribe(os.path.join(proy, 'Conversion', 'UUtilesMerge.pas'), uu)
    n = actualiza_dpr(proy)
    print('Merge13.dpr actualizado (%d units importadas / pendientes / conversión)' % n)
    # ---- informe
    nombre = a.modulo or (a.unit or 'units').split(',')[0]
    with open(os.path.join(proy, 'Conversion', 'informes', 'informe_%s.txt' % nombre), 'w', encoding='utf-8') as f:
        f.write('BLOQUEANTES (%d)\n' % len(inf.bloqueantes) + ''.join('  - %s\n' % x for x in inf.bloqueantes))
        f.write('\nPENDIENTES DE REVISAR (%d)\n' % len(inf.revisar) + ''.join('  - %s\n' % x for x in inf.revisar))
        f.write('\nCONVERSIONES AUTOMATICAS\n' + ''.join('  - %s\n' % x for x in inf.auto))
    if tipos.bd is not None:
        tipos.bd.cierra()
    print('BLOQUEANTES: %d | pendientes de revisar: %d -> Conversion\\informes\\informe_%s.txt'
          % (len(inf.bloqueantes), len(inf.revisar), nombre))


if __name__ == '__main__':
    main()
