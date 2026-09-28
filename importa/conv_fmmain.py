# -*- coding: utf-8 -*-
"""Añade a UFMMain.pas (MaxFactu) los miembros de FMain (Merge) que usa el código convertido y no existen.
El bloque añadido va entre marcas y se regenera en cada conversión (se acumulan los miembros ya añadidos)."""
import re
import dfmparser as dp
import conv_pas as cp

INI, FIN = '{MERGE2MAXFACTU-INICIO}', '{MERGE2MAXFACTU-FIN}'

# Métodos de FMain con implementación propia para MaxFactu (el cuerpo de Merge depende de ventanas de Merge)
PLANTILLAS = {
    'addcomponentepunto': ('procedure AddComponentePunto(Componente: TComponent);',
        'begin\n  if ComponentesPunto.IndexOf(Componente) = -1 then\n    ComponentesPunto.Add(Componente);\nend;',
        ['ComponentesPunto']),
    'delcomponentepunto': ('procedure DelComponentePunto(Componente: TComponent);',
        'begin\n  ComponentesPunto.Remove(Componente);\nend;', ['ComponentesPunto']),
    'traspasodedocumentosentrada': ('procedure TraspasoDeDocumentosEntrada(id_e: Integer);',
        "var\n  Tipo: string;\nbegin\n"
        "  // Merge abría el documento de compra por su ID_E. En MaxFactu: acción del tipo de documento filtrada\n"
        "  Tipo := DMMain.DameTitulo('GES_CABECERAS_E', 'TIPO', 'ID_E', '', '', id_e);\n"
        "  if Tipo = 'PEP' then\n    EjecutaAccionFiltro(APedidosCompraProveedor, ' ID_E = ' + IntToStr(id_e), True)\n"
        "  else if Tipo = 'ALP' then\n    EjecutaAccionFiltro(AAlbaranesCompraProveedor, ' ID_E = ' + IntToStr(id_e), True)\n"
        "  else if Tipo = 'FAP' then\n    EjecutaAccionFiltro(AFacturasCompraProveedor, ' ID_E = ' + IntToStr(id_e), True)\n"
        "  else if Tipo = 'FCR' then\n    EjecutaAccionFiltro(AFacturasAcreedor, ' ID_E = ' + IntToStr(id_e), True);\nend;", []),
}
CAMPOS_EXTRA = {'componentespunto': ('ComponentesPunto', 'TList', 'ComponentesPunto := TList.Create;')}


def _clase(src, nombre):
    i = src.index('%s = class' % nombre)
    j = re.search(r'\n\s*end\s*;', src[i:]).start() + i
    return i, j


def miembros_clase(src, nombre):
    i, j = _clase(src, nombre)
    cuerpo = cp._limpia_comentarios(src[i:j])
    n = {x.strip().lower() for ns in re.findall(r'^\s*([\w, ]+)\s*:\s*[\w.<>]+\s*;', cuerpo, re.M)
         for x in ns.split(',')}
    n |= {x.lower() for x in re.findall(r'^\s*(?:procedure|function|property|constructor)\s+(\w+)', cuerpo,
                                          re.M | re.I)}
    return n


def parchea(src_mf, src_merge, dfm_merge, usados, inf):
    # quitar un bloque anterior recordando qué contenía
    previos = set(re.findall(r'\{MERGE2MAXFACTU-MIEMBROS: ([^}]*)\}', src_mf))
    previos = {x.strip() for p in previos for x in p.split(',') if x.strip()}
    src_mf = re.sub(r'[ \t]*' + re.escape(INI) + r'.*?' + re.escape(FIN) + r'[ \t]*\r?\n?', '', src_mf, flags=re.S)
    existentes = miembros_clase(src_mf, 'TFMMain')
    # declaraciones de Merge
    mi, mj = _clase(src_merge, 'TFMain')
    decl_merge = cp._limpia_comentarios(src_merge[mi:mj])
    campos = {}
    for ns, t in re.findall(r'^\s*([\w, ]+)\s*:\s*([\w.]+)\s*;', decl_merge, re.M):
        for x in ns.split(','):
            campos[x.strip().lower()] = (x.strip(), t)
    metodos = {m.group(2).lower(): m.group(1).strip() for m in
               re.finditer(r'^\s*((?:procedure|function)\s+(\w+)\s*(?:\([^)]*\))?\s*(?::\s*\w+)?\s*;)', decl_merge,
                           re.M | re.I)}
    captions = {}
    if dfm_merge:
        r = dp.parse(dfm_merge)
        for n in r.walk():
            if n.cls in ('TAction', 'TLFCategoryAction', 'TLFDatasetAction', 'TLFNoSaveAction') and n.get('Caption'):
                captions[n.name.lower()] = n.getv('Caption')
    faltan = sorted({u for u in set(usados) | previos if u.lower() not in existentes}, key=str.lower)
    decl, impl, crea, pendientes, nombres = [], [], [], [], []
    extra_campos = set()
    for u in faltan:
        k = u.lower()
        if k in PLANTILLAS:
            cab, cuerpo, deps = PLANTILLAS[k]
            decl.append('    ' + cab)
            nm = re.match(r'(?:procedure|function)\s+(\w+)', cab).group(1)
            impl.append(re.sub(r'^(procedure|function)\s+', r'\1 TFMMain.', cab) + '\n' + cuerpo + '\n')
            extra_campos |= {d.lower() for d in deps}
            nombres.append(u)
        elif k in campos:
            nombre, tipo = campos[k]
            if tipo in ('TAction', 'TLFCategoryAction', 'TLFDatasetAction', 'TLFNoSaveAction'):
                decl.append('    %s: TAction;  // acción de Merge sin módulo convertido todavía' % nombre)
                cap = captions.get(k, dp.quote(nombre))
                crea.append("  %s := TAction.Create(Self);\n  %s.Name := '%s';\n  %s.Caption := %s;\n"
                            "  %s.Enabled := False;  // se habilitará al convertir su módulo" %
                            (nombre, nombre, nombre, nombre, cap, nombre))
                pendientes.append(nombre)
            elif k in CAMPOS_EXTRA:
                extra_campos.add(k)
            else:
                t = cp.TIPOS_COMPONENTE.get(tipo, tipo)
                decl.append('    %s: %s;' % (nombre, t))
            nombres.append(nombre)
        elif k in metodos:
            cab = re.sub(r'\bTFMain\b', 'TFMMain', metodos[k])
            decl.append('    ' + cab)
            impl.append(re.sub(r'^(procedure|function)\s+', r'\1 TFMMain.', cab) + '\nbegin\n'
                        "  ShowMessage('Pendiente de convertir desde Merge: FMain.%s');\nend;\n" % u)
            pendientes.append(u + ' (método)')
            nombres.append(u)
        else:
            inf.revisar.append('FMMain: "%s" no existe en TFMMain ni en TFMain de Merge; revisar.' % u)
    for k in sorted(extra_campos):
        nombre, tipo, ini = CAMPOS_EXTRA[k]
        if k not in existentes:
            decl.insert(0, '    %s: %s;' % (nombre, tipo))
            crea.insert(0, '  ' + ini)
            nombres.append(nombre)
    if not decl:
        return src_mf, []
    # en Delphi los campos van antes que los métodos dentro de cada sección
    decl = [d for d in decl if not re.match(r'\s*(procedure|function)\b', d)] + \
           [d for d in decl if re.match(r'\s*(procedure|function)\b', d)]
    marca = '%s: %s' % ('{MERGE2MAXFACTU-MIEMBROS', ', '.join(sorted(set(nombres), key=str.lower)) + '}')
    # 1) declaraciones al final de la clase
    i, j = _clase(src_mf, 'TFMMain')
    bloque = ('  %s\n  %s\n  public\n    // Miembros de FMain de Merge que usa el código convertido (generado por merge2maxfactu)\n'
              '%s\n    procedure CreaMiembrosMerge;\n  %s\n' % (INI, marca, '\n'.join(decl), FIN))
    src_mf = src_mf[:j] + '\n' + bloque + src_mf[j:]
    # 2) implementación antes de initialization / end.
    fin = re.search(r'^(?:initialization|end\.)', src_mf, re.M)
    cuerpo = ('%s\nprocedure TFMMain.CreaMiembrosMerge;\nbegin\n%s\nend;\n\n%s%s\n\n'
              % (INI, '\n'.join(crea), '\n'.join(impl), FIN))
    src_mf = src_mf[:fin.start()] + cuerpo + src_mf[fin.start():]
    # 3) llamada al principio de FormCreate
    src_mf = re.sub(r'(procedure TFMMain\.FormCreate\(Sender: TObject\);.*?\bbegin\b)',
                    lambda m: m.group(1) + '\n  CreaMiembrosMerge;  ' + INI + ' ' + FIN, src_mf, count=1, flags=re.S)
    inf.auto.append('UFMMain.pas: añadidos %d miembros de FMain de Merge: %s' % (len(nombres), ', '.join(nombres)))
    for p in pendientes:
        inf.revisar.append('FMMain.%s: creado para que compile; su módulo/implementación está pendiente.' % p)
    return src_mf, nombres
