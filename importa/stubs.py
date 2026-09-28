# -*- coding: utf-8 -*-
"""Genera units STUB: interface de Merge convertida + implementación vacía.
Sirven para compilar un módulo convertido antes de haber convertido todas sus dependencias."""
import re
import conv_pas as cp
import conv_dfm as cd

DIRECTIVAS = r'\b(virtual|override|dynamic|abstract|reintroduce|overload|static|inline|message\s+\w+|stdcall|' \
             r'cdecl|register|safecall|pascal|final)\s*;'
DIRS = r'(?:\s*(?:virtual|override|dynamic|abstract|reintroduce|overload|static|inline|message\s+\w+|stdcall|cdecl|register|safecall|final)\s*;)*'
ANCESTROS = {'TG2KForm': 'TForm', 'THYForm': 'TForm', 'TFormG2K': 'TForm', 'TLFForm': 'TForm'}
TIPOS_QUITAR = set(cd.ELIMINAR) | {'TfrHYReport', 'TfrDBDataSet', 'TfrUserDataset', 'THYReportSource',
                                   'THYReportMailSource', 'THYReport', 'THYReportMail', 'TfrReport', 'TCodeBar',
                                   'TEntornoFind2000', 'TTeclas', 'TLFManager', 'TfrxHYReport',
                                   'TfrxFIBHYComponents', 'TYearPlanner', 'TIOFFind', 'TLetra', 'TfrxHYDesigner',
                                   'TfrxHYMailExport', 'TFRTallas_s', 'TFRTallas_e', 'TGantt', 'TRxClock',
                                   'TCVBNorma34CSB', 'TCVBNorma34_1CSB', 'TCVBNorma34_14CSB', 'TCVBNorma19CSB',
                                   'TCVBNorma32CSB', 'TCVBNorma58CSB', 'TConfirming', 'THYPrinterOptions',
                                   'TRxMemoryData', 'TFormPlacement', 'THYIBBackup'}
# componentes de Merge -> VCL (los del conversor de DFM) para declaraciones de campos
for _k, (_v, _p) in cd.MAPA.items():
    cp.TIPOS_COMPONENTE.setdefault(_k, _v)


TIPOS_PENDIENTES = set()
EVENTO_FR2 = {'tfrview', 'tfrobject', 'tfrmemoview', 'tfrbandview', 'tfrpictureview', 'tfrpage', 'tfrband'}


def _anade_uses_iface(iface, unidad):
    m = re.search(r'\binterface\b(?:\s|\{[^}]*\})*uses\b((?:[^;{]|\{[^}]*\})*);', iface, re.I | re.S)
    if m:
        if unidad.lower() in m.group(1).lower():
            return iface
        return iface[:m.end(1)] + ', ' + unidad + iface[m.end(1):]
    mi = re.search(r'\binterface\b', iface, re.I)
    return iface[:mi.end()] + '\n\nuses ' + unidad + ';\n' + iface[mi.end():]


def unidad_tipos_pendientes():
    lineas = ['unit UTiposPendientesMerge;', '',
              '// Tipos de Merge sin equivalente todavía en Delphi 13 (FastReport 2, componentes propios...).',
              '// Son clases vacías para que el código convertido compile. Cada una se irá sustituyendo',
              '// por su equivalente real (FastReport actual, componente portado...).', '',
              'interface', '', 'uses System.Classes;', '', 'type']
    vistos = set()
    for t in sorted(TIPOS_PENDIENTES, key=str.lower):
        if t.lower() in vistos:
            continue
        vistos.add(t.lower())
        base = 'TObject' if t.lower() in EVENTO_FR2 else 'TComponent'
        lineas.append('  %s = class(%s) end;  // PENDIENTE' % (t, base))
    lineas += ['', 'implementation', '', 'end.', '']
    return '\n'.join(lineas)


def _quitado(texto):
    """¿La declaración usa un tipo que no existe en Delphi 13 (componentes eliminados, FastReport 2...)?"""
    if cd.SIN_TEECHART and re.search(r'\bT(DBChart|Chart|\w*Series|ChartSeries)\b', texto):
        return True
    return bool(re.search(r'\bTFIB\w*|\bTHYFIB\w*', texto))


def _cuerpo(cabecera, clase=None):
    cab = re.sub(DIRECTIVAS, '', cabecera, flags=re.I).strip()
    cab = re.sub(r'\s*;\s*$', '', cab) + ';'
    m = re.match(r'(class\s+)?(procedure|function|constructor|destructor)\s+(\w+)(.*)$', cab, re.I | re.S)
    if not m:
        return ''
    clase_kw, tipo, nombre, resto = m.groups()
    # quitar valores por defecto de parámetros no es necesario en la implementación, pero es legal repetirlos
    cab_impl = '%s%s %s%s' % (clase_kw or '', tipo, (clase + '.' if clase else '') + nombre, resto)
    cuerpo = '  // STUB: pendiente de convertir\n'
    if tipo.lower() == 'constructor':
        cuerpo = '  inherited;\n' if re.search(r'\bAOwner\b', resto) else cuerpo
    if tipo.lower() == 'destructor':
        cuerpo = '  inherited;\n'
    if tipo.lower() == 'function':
        cuerpo = '  Result := Default(%s);\n' % re.search(r':\s*([\w.<>]+)\s*;\s*$', resto).group(1)
    return '%s\nbegin\n%send;\n\n' % (cab_impl, cuerpo)


def genera(src, inf, nombre):
    src = cp.convierte_pas_unit(src, inf, nombre)
    partes = re.split(r'\bimplementation\b', src, maxsplit=1, flags=re.I)
    iface = partes[0]
    # ancestros G2K -> TForm; campos de componentes sin equivalente fuera
    for a, b in ANCESTROS.items():
        iface = re.sub(r'class\s*\(\s*%s\s*\)' % a, 'class(%s)' % b, iface, flags=re.I)
    # Los tipos sin equivalente (FastReport 2, componentes G2K...) se conservan con su nombre: se declaran como
    # clases vacías en UTiposPendientesMerge.pas. Así el código que los usa compila y las sobrecargas siguen
    # siendo distintas; la funcionalidad queda pendiente hasta portar/sustituir cada componente.
    usados = set(re.findall(r'\b(Tfr(?!x)[A-Z]\w*|TfrxHY\w*|THYReport\w*)\b', iface, re.I))
    usados |= {t for t in TIPOS_QUITAR if re.search(r'\b%s\b' % t, iface, re.I)}
    if usados:
        TIPOS_PENDIENTES.update(usados)
        iface = _anade_uses_iface(iface, 'UTiposPendientesMerge')
    lineas = []
    salto = False
    for l in iface.split('\n'):
        if salto:
            salto = not l.rstrip().endswith(';')
            continue
        if re.match(r'\s*(?:class\s+)?(?:procedure|function|\w+\s*:)', l) and _quitado(l):
            salto = not l.rstrip().endswith(';')
            continue
        lineas.append(l)
    iface = '\n'.join(lineas)
    limpio = cp._limpia_comentarios(iface)
    impl = ['implementation', '', '// ==== STUB generado por merge2maxfactu: solo la interfaz de Merge convertida ====', '']
    # métodos de clases
    for m in re.finditer(r'\b(T\w+)\s*=\s*class\b(?!\s*(?:of|;))(.*?)\n\s*end(?:\s+\w+)?\s*;', limpio, re.S | re.I):
        clase, cuerpo = m.group(1), m.group(2)
        for mm in re.finditer(r'^\s*((?:class\s+)?(?:procedure|function|constructor|destructor)\s+\w+\s*'
                              r'(?:\([^)]*\))?\s*(?::\s*[\w.<>]+)?\s*;' + DIRS + ')', cuerpo, re.M | re.I):
            cab = mm.group(1)
            if re.search(r'\babstract\s*;', cab, re.I):
                continue
            if _quitado(cab):
                continue
            impl.append(_cuerpo(cab, clase))
    # rutinas sueltas (fuera de clases)
    sin_clases = re.sub(r'\b(T\w+)\s*=\s*class\b(?!\s*(?:of|;)).*?\n\s*end(?:\s+\w+)?\s*;', '', limpio, flags=re.S | re.I)
    sin_clases = re.sub(r'\b\w+\s*=\s*(?:procedure|function)\b[^;]*(?:\([^)]*\))?[^;]*;(\s*of\s+object\s*;)?', '',
                        sin_clases, flags=re.I)
    for mm in re.finditer(r'^\s*((?:procedure|function)\s+\w+\s*(?:\([^)]*\))?\s*(?::\s*[\w.<>]+)?\s*;'
                          + DIRS + ')', sin_clases, re.M | re.I):
        if _quitado(mm.group(1)):
            continue
        impl.append(_cuerpo(mm.group(1)))
    impl.append('end.\n')
    return quita_sobrecargas_duplicadas(iface.rstrip() + '\n\n' + '\n'.join(impl), inf, nombre)


def _rutinas_top(impl):
    """Bloques de rutinas de primer nivel de una implementación (cabecera en columna 0)."""
    pos = [m.start() for m in re.finditer(r'^(?:procedure|function)\s+\w+', impl, re.M | re.I)]
    fin_impl = re.search(r'^(?:initialization|finalization)\b|^end\.', impl, re.M | re.I)
    limite = fin_impl.start() if fin_impl else len(impl)
    bloques = {}
    for i, p in enumerate(pos):
        if p >= limite:
            break
        f = pos[i + 1] if i + 1 < len(pos) and pos[i + 1] < limite else limite
        nombre = re.match(r'(?:procedure|function)\s+(\w+)', impl[p:], re.I).group(1)
        if '.' in impl[p:p + 200].split('(')[0].split(';')[0]:
            continue   # métodos de clase
        bloques.setdefault(nombre.lower(), []).append(impl[p:f].rstrip() + '\n\n')
    return bloques


def genera_uutiles_merge(src_merge, src_maxfactu, textos_convertidos, inf, otras_mf=()):
    """UUtilesMerge: rutinas de UUtiles de Merge que no existen en MaxFactu y que el código convertido usa.
    Se copian con su código real (convertido), incluyendo las rutinas de las que dependen."""
    iface_mf = cp._limpia_comentarios(re.split(r'\bimplementation\b', src_maxfactu, flags=re.I)[0])
    en_mf = {x.lower() for x in re.findall(r'^\s*(?:function|procedure)\s+(\w+)', iface_mf, re.M | re.I)}
    for otro in otras_mf:   # rutinas globales de otras units de MaxFactu (UEntorno, UDMMain...)
        io = cp._limpia_comentarios(re.split(r'\bimplementation\b', otro, flags=re.I)[0])
        io = re.sub(r'\bclass\b.*?\n\s*end(?:\s+\w+)?\s*;', '', io, flags=re.S | re.I)
        en_mf |= {x.lower() for x in re.findall(r'^\s*(?:function|procedure)\s+(\w+)', io, re.M | re.I)}
    partes = re.split(r'\bimplementation\b', src_merge, maxsplit=1, flags=re.I)
    iface_me, impl_me = partes[0], partes[1]
    decl = {}
    for m in re.finditer(r'^\s*((?:function|procedure)\s+(\w+)\s*(?:\([^)]*\))?\s*(?::\s*[\w.<>]+)?\s*;' + DIRS + ')',
                         cp._limpia_comentarios(iface_me), re.M | re.I):
        decl.setdefault(m.group(2).lower(), []).append(m.group(1).strip())
    bloques = _rutinas_top(impl_me)
    todas = set(bloques)
    usados = set()
    palabras = set()
    for t in textos_convertidos:
        palabras |= {w.lower() for w in re.findall(r'\b\w+\b', cp._limpia_comentarios(t))}
    pendientes = [n for n in decl if n in palabras and n not in en_mf]
    while pendientes:
        n = pendientes.pop()
        if n in usados or n in en_mf or n not in bloques:
            continue
        usados.add(n)
        cuerpo = cp._limpia_comentarios(''.join(bloques[n]))
        for w in {w.lower() for w in re.findall(r'\b\w+\b', cuerpo)} & todas:
            if w not in usados and w not in en_mf:
                pendientes.append(w)
    iface = []
    impl = []
    orden = [n for n in bloques if n in usados]
    for n in orden:
        if n in decl:
            iface += decl[n]
        else:
            # rutina privada de UUtiles: se declara en la interfaz para que el orden no importe
            for b in bloques[n]:
                cab = re.match(r'((?:procedure|function)\s+\w+\s*(?:\([^)]*\))?\s*(?::\s*[\w.<>]+)?\s*;)', b, re.I)
                if cab:
                    iface.append(cab.group(1) + (' overload;' if len(bloques[n]) > 1 else ''))
        impl += bloques[n]
    # uses de la implementación de Merge (se ajustan en la conversión) y var/const globales de la implementación
    usos = re.search(r'^\s*uses\b(.*?);', impl_me, re.S | re.I | re.M)
    texto = ('unit UUtilesMerge;\n\n// Rutinas de UUtiles de Merge que no existen en MaxFactu (código original convertido).\n'
             '// Generado por merge2maxfactu: incluye solo las que usa el código convertido y sus dependencias.\n\n'
             'interface\n\n' + re.search(r'^\s*uses\b.*?;', iface_me, re.S | re.I | re.M).group(0).strip() + '\n\n'
             + '\n'.join(iface) + '\n\nimplementation\n\n'
             + ('uses' + usos.group(1) + ', UUtiles, UEntorno, UDMMain;\n\n' if usos else
                'uses UUtiles, UEntorno, UDMMain;\n\n')
             + ''.join(impl) + 'end.\n')
    inf.auto.append('UUtilesMerge: %d rutinas de UUtiles de Merge (%s)' % (len(orden), ', '.join(sorted(orden))))
    texto = cp.convierte_pas_unit(texto, inf, 'UUtilesMerge.pas')
    return quita_sobrecargas_duplicadas(texto, inf, 'UUtilesMerge.pas')


def quita_sobrecargas_duplicadas(texto, inf, nombre):
    """Al pasar tipos distintos de Merge al mismo tipo VCL (TNsDBGrid y TDBGrid -> TDBGrid) dos sobrecargas
    quedan iguales: se deja solo la primera (declaración y cuerpo)."""
    partes = re.split(r'(\bimplementation\b)', texto, maxsplit=1, flags=re.I)
    if len(partes) < 3:
        return texto
    iface, sep, impl = partes
    norm = lambda h: re.sub(r'\s+', '', re.sub(DIRECTIVAS, '', h, flags=re.I)).lower()
    vistos, lineas = set(), []
    for l in iface.split('\n'):
        m = re.match(r'\s*((?:function|procedure)\s+\w+.*;)', l, re.I)
        if m:
            k = norm(m.group(1))
            if k in vistos:
                inf.auto.append('%s: sobrecarga duplicada eliminada: %s' % (nombre, m.group(1).strip()))
                continue
            vistos.add(k)
        lineas.append(l)
    iface = '\n'.join(lineas)
    pos = [m.start() for m in re.finditer(r'^(?:procedure|function)\s+\w+', impl, re.M | re.I)] + [len(impl)]
    trozos, vistos = [impl[:pos[0]]], set()
    for i in range(len(pos) - 1):
        bloque = impl[pos[i]:pos[i + 1]]
        cab = re.match(r'((?:procedure|function)\s+\w+\s*(?:\([^)]*\))?\s*(?::\s*[\w.<>]+)?\s*;)', bloque, re.I)
        k = norm(cab.group(1)) if cab else None
        if k and k in vistos:
            # conservar lo que haya detrás del último end; (initialization / end.)
            fin = re.search(r'^(?:initialization|finalization)\b|^end\.', bloque, re.M | re.I)
            if fin:
                trozos.append(bloque[fin.start():])
            continue
        if k:
            vistos.add(k)
        trozos.append(bloque)
    return iface + sep + ''.join(trozos)


# Indicadores de Merge (FMain) con equivalente en FMMain de MaxFactu
FMAIN_EQUIV = {'autproveedor': 'LlamaProveedor', 'autcliente': 'LlamaCliente', 'autacreedor': 'LlamaAcreedor',
               'autagente': 'LlamaAgente'}


def adapta_fmain(texto, src_ufmmain, inf):
    """Convierte el STUB de UFMain (Merge) en un adaptador sobre FMMain de MaxFactu.
    - TFMain pasa a ser un formulario invisible creado en tiempo de ejecución (FMain nunca es nil).
    - Acciones que existen en MaxFactu -> propiedades que devuelven la acción de FMMain.
    - Acciones que solo tiene Merge -> TAction deshabilitadas creadas en el constructor.
    - autproveedor/autcliente/... -> LlamaProveedor/LlamaCliente/... de FMMain.
    - EjecutaAccion(Accion, Filtro) -> ejecuta la acción real con el filtro (contrato FiltroAccion de MaxFactu)."""
    mf_if = re.split(r'\bimplementation\b', src_ufmmain, flags=re.I)[0]
    i = mf_if.index('TFMMain = class')
    j = re.search(r'\n\s*end\s*;', mf_if[i:]).end() + i
    mf_campos = {n.strip().lower(): (n.strip(), t) for ns, t in
                 re.findall(r'^\s*([\w, ]+)\s*:\s*([\w.<>]+)\s*;', mf_if[i:j], re.M) for n in ns.split(',')}
    partes = re.split(r'(\bimplementation\b)', texto, maxsplit=1, flags=re.I)
    iface, impl = partes[0], partes[2]
    i = iface.index('TFMain = class')
    j = re.search(r'\n\s*end\s*;', iface[i:]).start() + i
    clase = iface[i:j]
    # campos de la clase de Merge
    reenviadas, acciones_merge, props = [], [], []
    lineas = []
    for l in clase.split('\n'):
        m = re.match(r'^(\s*)([\w, ]+?)\s*:\s*([\w.]+)\s*;(.*)$', l)
        if m and not re.match(r'\s*(procedure|function|property)\b', l, re.I):
            nombres = [x.strip() for x in m.group(2).split(',')]
            tipo = m.group(3)
            quedan = []
            for nm in nombres:
                k = nm.lower()
                if k in mf_campos and mf_campos[k][1] == 'TAction' and tipo == 'TAction':
                    reenviadas.append(mf_campos[k][0])
                elif k in FMAIN_EQUIV and FMAIN_EQUIV[k].lower() in mf_campos:
                    props.append((nm, tipo, FMAIN_EQUIV[k]))
                else:
                    quedan.append(nm)
                    if tipo == 'TAction':
                        acciones_merge.append(nm)
            if quedan:
                lineas.append('%s%s: %s;%s' % (m.group(1), ', '.join(quedan), tipo, m.group(4)))
            continue
        lineas.append(l)
    clase = '\n'.join(lineas)
    clase = clase.replace('TFMain = class(TForm)', 'TFMain = class(TForm)  // ADAPTADOR sobre FMMain de MaxFactu', 1)
    extra_priv = ''.join('    function Get%s: TAction;\n' % a for a in reenviadas)
    for nm, tipo, eq in props:
        extra_priv += '    function Get%s: %s;\n    procedure Set%s(const Value: %s);\n' % (nm, tipo, nm, tipo)
    extra_pub = '    constructor CreaAdaptador;\n'
    extra_pub += ''.join('    property %s: TAction read Get%s;\n' % (a, a) for a in reenviadas)
    extra_pub += ''.join('    property %s: %s read Get%s write Set%s;\n' % (nm, t, nm, nm) for nm, t, _ in props)
    clase += '\n  private\n' + extra_priv + '  public\n' + extra_pub
    iface = iface[:i] + clase + iface[j:]
    # implementación
    cuerpo = ''.join('function TFMain.Get%s: TAction;\nbegin\n  Result := FMMain.%s;\nend;\n\n' % (a, a)
                     for a in reenviadas)
    for nm, tipo, eq in props:
        cuerpo += ('function TFMain.Get%s: %s;\nbegin\n  Result := FMMain.%s;\nend;\n\n'
                   'procedure TFMain.Set%s(const Value: %s);\nbegin\n  FMMain.%s := Value;\nend;\n\n'
                   % (nm, tipo, eq, nm, tipo, eq))
    crea = ['constructor TFMain.CreaAdaptador;', 'begin', '  inherited CreateNew(Application);',
            '  // Acciones que solo existen en Merge: se crean deshabilitadas hasta convertir su módulo']
    for a in acciones_merge:
        crea.append("  %s := TAction.Create(Self); %s.Name := '%s'; %s.Enabled := False;" % (a, a, a, a))
    crea += ['end;', '', '']
    cuerpo += '\n'.join(crea)
    # EjecutaAccion real
    impl = re.sub(r'procedure TFMain\.EjecutaAccion\(([^)]*)\);\s*\nbegin\n.*?\nend;\n',
                  lambda m: ('procedure TFMain.EjecutaAccion(%s);\nbegin\n'
                             '  // Merge: ejecuta la acción de menú con un filtro. En MaxFactu el filtro va en FMMain.FiltroAccion\n'
                             '  if Accion = nil then\n    Exit;\n'
                             '  if Accion.Owner = FMMain then\n    UFMMain.FiltroAccion := Filtro;\n'
                             '  if Accion.Enabled then\n    Accion.Execute\n  else\n'
                             "    LogMerge('FMain.EjecutaAccion pendiente: ' + Accion.Name);\nend;\n" % m.group(1)),
                  impl, count=1, flags=re.S)
    # resto de métodos vacíos: que dejen rastro
    impl = re.sub(r'((?:procedure|function)\s+(TFMain\.\w+)[^\n]*\n(?:[^\n]*\n)*?begin\n)  // STUB: pendiente de convertir\n',
                  lambda m: m.group(1) + "  LogMerge('PENDIENTE (stub): %s');\n" % m.group(2), impl)
    ini = ('\ninitialization\n  FMain := TFMain.CreaAdaptador;\n\nfinalization\n  FreeAndNil(FMain);\n\nend.\n')
    impl = re.sub(r'\bend\.\s*$', ini.lstrip('\n'), impl.rstrip() + '\n')
    usos = 'uses UFMMain, UAuxMerge;\n\n'
    inf.auto.append('UFMain: adaptador sobre FMMain (%d acciones reenviadas, %d acciones de Merge, %d indicadores)'
                    % (len(reenviadas), len(acciones_merge), len(props)))
    return iface + partes[1] + '\n\n' + usos + cuerpo + impl
