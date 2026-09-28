# -*- coding: utf-8 -*-
"""Conversión de unidades .pas Merge -> patrón MaxFactu."""
import re, collections

TIPOS_COMPONENTE = {
    'TFIBTableSet': 'TFDQuery', 'TFIBDataSet': 'TFDQuery', 'TFIBDataSetRO': 'TFDQuery',
    'TFIBTableSetRO': 'TFDQuery', 'TFIBDataSetRW': 'TFDQuery', 'TFIBInfoSet': 'TFDQuery',
    'THYFIBQuery': 'TFDQuery', 'TFIBQuery': 'TFDQuery', 'THYTransaction': 'TFDTransaction',
    'TFIBTransaction': 'TFDTransaction', 'THYDatabase': 'TFDConnection', 'TFIBDatabase': 'TFDConnection',
    'TFIBStringField': 'TStringField',
    'TLFLabel': 'TLabel', 'TLFEdit': 'TEdit', 'TLFDbedit': 'TDBEdit', 'TLFDBMemo': 'TDBMemo', 'TLFMemo': 'TMemo',
    'TLFDBCheckBox': 'TDBCheckBox', 'TLFCheckBox': 'TCheckBox', 'TFlatCheckBox': 'TCheckBox',
    'TLFComboBox': 'TComboBox', 'TLFPanel': 'TPanel', 'TFlatPanel': 'TPanel', 'TLFPageControl': 'TPageControl',
    'TLFToolBar': 'TToolBar', 'TLFDBCtrlGrid': 'TDBCtrlGrid', 'TLFDBDateEdit': 'TDBEdit',
    'TLFDateEdit': 'TDateTimePicker', 'THYGRightEdit': 'TEdit', 'TDBComboBoxValue': 'TDBComboBox',
    'TLFDBEditFind2000': 'TDBEdit', 'TDBEditFind2000': 'TDBEdit', 'TLFEditFind2000': 'TEdit',
    'THYTDBGrid': 'TDBGrid', 'TDBGridFind2000': 'TDBGrid', 'TLFActionList': 'TActionList',
    'TLFCategoryAction': 'TAction', 'TLFDatasetAction': 'TAction', 'THYMNavigator': 'TDBNavigator',
}
TIPOS_ELIMINAR = {'TControlEdit', 'TPopUpTeclas', 'THYMEditPanel', 'TG2KTBLoc', 'TLFFibFormStorage',
                  'TFormStorage'}

USES_DM = ('System.SysUtils, System.Classes, System.Variants, System.Generics.Collections, Data.DB, '
           'Vcl.Forms, Vcl.Controls, Vcl.Dialogs, Winapi.Windows, Winapi.ShellAPI, '
           'FireDAC.Stan.Intf, FireDAC.Stan.Option, FireDAC.Stan.Param, FireDAC.Stan.Error, FireDAC.DatS, '
           'FireDAC.Phys.Intf, FireDAC.DApt.Intf, FireDAC.Stan.Async, FireDAC.DApt, FireDAC.Comp.DataSet, '
           'FireDAC.Comp.Client, gnugettext, UAuxMerge')
USES_FRAME = ('Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, '
              'System.Actions, System.ImageList, System.Generics.Collections, Vcl.Graphics, Vcl.Controls, '
              'Vcl.Forms, Vcl.Dialogs, Vcl.Menus, Vcl.StdCtrls, Vcl.Buttons, Vcl.DBCtrls, Vcl.ToolWin, '
              'Vcl.ComCtrls, Vcl.Grids, Vcl.DBGrids, Vcl.ExtCtrls, Vcl.Mask, Vcl.ActnList, Vcl.ImgList, '
              'Vcl.DBCGrids, Data.DB, VclTee.TeEngine, VclTee.Series, VclTee.TeeProcs, VclTee.Chart, '
              'VclTee.DBChart, UFRMMantenimientoSimple, UUtilGuardaConfiguracion, UBuscadorCampo, gnugettext, UAuxMerge')


def _limpia_comentarios(s):
    return re.sub(r'\{[^}]*\}|\(\*.*?\*\)|//[^\n]*', lambda m: ' ' * len(m.group(0)), s, flags=re.S)


def reemplazo_en_codigo(src, patron, repl, flags=0):
    """Aplica una sustitución solo fuera de comentarios y literales."""
    out = []
    pos = 0
    token = re.compile(r"\{[^}]*\}|\(\*.*?\*\)|//[^\n]*|'(?:[^']|'')*'", re.S)
    for m in token.finditer(src):
        out.append(re.sub(patron, repl, src[pos:m.start()], flags=flags))
        out.append(m.group(0))
        pos = m.end()
    out.append(re.sub(patron, repl, src[pos:], flags=flags))
    return ''.join(out)


def reemplazo_sin_comentarios(src, patron, repl, flags=0):
    """Sustitución que puede abarcar literales (p.ej. ByName['X']) pero no toca comentarios."""
    out, pos = [], 0
    token = re.compile(r"'(?:[^']|'')*'|\{[^}]*\}|\(\*.*?\*\)|//[^\n]*", re.S)
    trozos = []
    for m in token.finditer(src):
        if m.group(0).startswith("'"):
            continue
        trozos.append((m.start(), m.end()))
    for a, b in trozos:
        out.append(re.sub(patron, repl, src[pos:a], flags=flags))
        out.append(src[a:b])
        pos = b
    out.append(re.sub(patron, repl, src[pos:], flags=flags))
    return ''.join(out)


def reemplazo_en_literales(src, fn):
    token = re.compile(r"\{[^}]*\}|\(\*.*?\*\)|//[^\n]*|'(?:[^']|'')*'", re.S)
    def r(m):
        t = m.group(0)
        return fn(t) if t.startswith("'") else t
    return token.sub(r, src)


def sql_literal(t):
    """Parámetros ?X dentro de literales que parecen SQL."""
    if not re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|WHERE|FROM|SET|AND|OR|VALUES|EXECUTE|LIKE|IN)\b|'
                     r'(^|[\s=<>(,!])\?[A-Za-z_]', t, re.I):
        return t
    t = re.sub(r'\?old_(\w+)', lambda m: ':OLD_' + m.group(1), t, flags=re.I)
    return re.sub(r'(?<![\w?¿])\?(?=[A-Za-z_])', ':', t)


def reescribe_uses(src, nuevos, conservar=()):
    """Sustituye la cláusula uses de la interface por la lista nueva (+ unidades propias conservadas)."""
    m = re.search(r'\binterface\b(.*?)\buses\b(.*?);', src, re.S | re.I)
    if not m:
        return src
    viejos = [u.strip() for u in re.sub(r'\{[^}]*\}', '', m.group(2)).split(',') if u.strip()]
    extra = [u for u in viejos if u.lower() not in {x.strip().lower() for x in nuevos.split(',')}]
    lista = nuevos + (', ' + ', '.join(extra) if extra else '')
    return src[:m.start(2)] + '\r\n  ' + lista + src[m.end(2):]


UNITS_FIB = {'hyfibquery', 'fibquery', 'fibdataset', 'fibdatabase', 'fibtabledataset', 'fibtabledatasetro',
             'fibdatasetro', 'fibdatasetrw', 'ufibmodificados', 'ibase', 'ib_externals', 'fib', 'fibmisc',
             'fibsqlmonitor', 'scriptquery', 'fr_class', 'fr_dset', 'fr_dbset', 'fr_hyreport', 'dbtables',
             'ufibdbeditfind', 'fibutiles', 'ibquery'}

_UC = None


def _units_componentes():
    """Units de la carpeta Componentes de Merge (LF, HY, CompG2k, Rx, FlatStyle, FR2...): desaparecen de los uses."""
    global _UC
    if _UC is None:
        import os
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'units_componentes_merge.txt')
        _UC = set()
        if os.path.exists(ruta):
            conservar = {'gnugettext', 'ulkjson', 'delphizxingqrcode'}
            _UC = {l.strip().lower() for l in open(ruta, encoding='utf-8') if l.strip()} - conservar
    return _UC


EQUIV_UNITS = {'UFMain': 'UFMMain', 
               'ShellApi': 'Winapi.ShellAPI', 'UFormGest': ''}
# Nombres cortos de Delphi 6 -> nombres con ámbito de Delphi 13
for _u in ('Classes SysUtils DateUtils Variants StrUtils Math IniFiles Types TypInfo Masks Contnrs SyncObjs '
           'ZLib SysConst RTLConsts Character').split():
    EQUIV_UNITS[_u] = 'System.' + _u
for _u in ('Graphics Controls Forms Dialogs StdCtrls ExtCtrls ComCtrls Menus DBCtrls Grids DBGrids Buttons '
           'ActnList Mask ToolWin ImgList DBActns Clipbrd Printers ExtDlgs FileCtrl CheckLst Tabs Themes '
           'DBCGrids ValEdit AppEvnts StdActns ComStrs Consts').split():
    EQUIV_UNITS[_u] = 'Vcl.' + _u
EQUIV_UNITS.update({'Spin': 'Vcl.Samples.Spin', 'Gauges': 'Vcl.Samples.Gauges', 'Calendar': 'Vcl.Samples.Calendar',
                    'ExtActns': 'Vcl.ExtActns', 'OleCtrls': 'Vcl.OleCtrls', 'Outline': 'Vcl.Outline',
                    'Windows': 'Winapi.Windows', 'Messages': 'Winapi.Messages', 'ShellAPI': 'Winapi.ShellAPI',
                    'ShlObj': 'Winapi.ShlObj', 'ActiveX': 'Winapi.ActiveX', 'MMSystem': 'Winapi.MMSystem',
                    'WinInet': 'Winapi.WinInet', 'CommCtrl': 'Winapi.CommCtrl', 'DB': 'Data.DB',
                    'DBClient': 'Datasnap.DBClient', 'ADODB': 'Data.Win.ADODB', 'ComObj': 'System.Win.ComObj',
                    'Registry': 'System.Win.Registry', 'Jpeg': 'Vcl.Imaging.jpeg', 'jpeg': 'Vcl.Imaging.jpeg',
                    'pngimage': 'Vcl.Imaging.pngimage', 'GIFImage': 'Vcl.Imaging.GIFImg', 'XMLDoc': 'Xml.XMLDoc',
                    'XMLIntf': 'Xml.XMLIntf', 'OleServer': 'Vcl.OleServer', 'Chart': 'VclTee.Chart',
                    'Series': 'VclTee.Series', 'TeEngine': 'VclTee.TeEngine', 'TeeProcs': 'VclTee.TeeProcs',
                    'DbChart': 'VclTee.DBChart'})


def renombra_units(src, inf, nombre):
    """En cláusulas uses: UFMxxx -> UFRMxxx si MaxFactu ya tiene el frame; equivalencias conocidas."""
    lower = {u.lower(): u for u in inf.units_maxfactu | inf.units_convertidas}
    def fix_lista(m):
        partes = m.group(1).split(',')
        out = []
        for p in partes:
            u = p.strip()
            if not u:
                out.append(p); continue
            import conv_dfm as _cd
            if _cd.SIN_TEECHART and (u.lower().startswith('vcltee.') or
                                     u.lower() in ('chart', 'series', 'teengine', 'teeprocs', 'dbchart', 'teeshape')):
                inf.auto.append('%s: uses %s eliminada (TeeChart no instalado)' % (nombre, u))
                continue
            if u.lower() in UNITS_FIB or u.lower() in _units_componentes():
                if u.lower() not in UNITS_FIB:
                    inf.auto.append('%s: uses %s eliminada (componente de Merge sustituido por VCL)' % (nombre, u))
                    continue
                inf.auto.append('%s: uses %s eliminada (FreeIB/FR2 -> FireDAC)' % (nombre, u))
                continue
            nuevo = EQUIV_UNITS.get(u)
            if PERFIL == 'merge13' and u.lower() == 'ufmain':
                nuevo = None
            if nuevo is None and not (PERFIL == 'merge13' and u.lower() == 'ufmain'):
                nuevo = next((v for k, v in EQUIV_UNITS.items() if k.lower() == u.lower()), None)
            if not nuevo and u.upper().startswith('UFM') and ('UFRM' + u[3:]).lower() in \
                    {x.lower() for x in inf.units_convertidas}:
                nuevo = 'UFRM' + u[3:]
            if not nuevo and u.upper().startswith('UFM') and getattr(inf, 'renombrar_ufm', False):
                cand = 'UFRM' + u[3:]
                nuevo = lower.get(cand.lower())
            if not nuevo and u.lower() in lower and lower[u.lower()] != u:
                nuevo = lower[u.lower()]
            if nuevo == '':
                inf.auto.append('%s: uses %s eliminada (la sustituye UAuxMerge)' % (nombre, u))
                continue
            if nuevo and nuevo != u:
                inf.auto.append('%s: uses %s -> %s' % (nombre, u, nuevo))
                p = p.replace(u, nuevo)
            out.append(p)
        if any(re.sub(r'\{[^}]*\}', '', p).strip().lower() == 'uutiles' for p in out) and \
                nombre.lower() != 'uutilesmerge.pas' and getattr(inf, 'con_uutiles_merge', True):
            out.append(' UUtilesMerge')
        vistos, unicos = set(), []
        for p in out:
            k = re.sub(r'\{[^}]*\}', '', p).strip().lower()
            if k and k in vistos:
                continue
            vistos.add(k)
            unicos.append(p)
        return 'uses' + ','.join(unicos) + ';'
    src = re.sub(r'\buses\b((?:[^;{]|\{[^}]*\})*);', fix_lista, src, flags=re.I)
    src = quita_units_no_usadas(src, inf, nombre)
    return quita_duplicados_uses(src)


def quita_duplicados_uses(src):
    """Una unidad no puede estar en el uses de interface y en el de implementation."""
    corte = re.search(r'\bimplementation\b', src, re.I)
    m_int = re.search(r'\binterface\b.*?\buses\b((?:[^;{]|\{[^}]*\})*);', src[:corte.start()] if corte else src,
                      re.S | re.I)
    m_imp = re.search(r'\bimplementation\b(?:\s|\{[^}]*\})*\buses\b((?:[^;{]|\{[^}]*\})*);', src, re.S | re.I)
    if not (m_int and m_imp):
        return src
    ya = {re.sub(r'\{[^}]*\}', '', x).strip().lower() for x in m_int.group(1).split(',')}
    vistos = set()
    items = []
    for x in m_imp.group(1).split(','):
        k = re.sub(r'\{[^}]*\}', '', x).strip().lower()
        if not k or k in ya or k in vistos:
            continue
        vistos.add(k)
        items.append(x)
    nuevo = ','.join(items)
    if not items:
        return src[:m_imp.start()] + 'implementation' + src[m_imp.end():]
    return src[:m_imp.start(1)] + nuevo + src[m_imp.end(1):]


_INDICE_MERGE = {}
_IDENT_UNIT = {}


def _indice_merge(dir_merge):
    import os
    if not _INDICE_MERGE and dir_merge:
        for raiz, _, ficheros in os.walk(dir_merge):
            for f in ficheros:
                if f.lower().endswith('.pas'):
                    _INDICE_MERGE.setdefault(f[:-4].lower(), os.path.join(raiz, f))
    return _INDICE_MERGE


def identificadores_interface(ruta):
    """Identificadores públicos (tipos, rutinas, variables, constantes) de la interface de una unit."""
    if ruta in _IDENT_UNIT:
        return _IDENT_UNIT[ruta]
    with open(ruta, 'rb') as fh:
        t = fh.read().decode('cp1252', errors='replace')
    t = _limpia_comentarios(t)
    iface = re.split(r'\bimplementation\b', t, flags=re.I)[0]
    ids = set(re.findall(r'^\s*(?:function|procedure)\s+(\w+)', iface, re.M | re.I))
    ids |= set(re.findall(r'^\s*(\w+)\s*=\s*(?:class|record|packed|set|array|\(|interface|\^|type\b|procedure|function|[\w.]+\s*;)', iface, re.M | re.I))
    for bloque in re.findall(r'\b(?:var|const|threadvar)\b(.*?)(?=\b(?:type|var|const|function|procedure|implementation)\b|$)', iface, re.S | re.I):
        ids |= set(re.findall(r'^\s*(\w+)\s*[:=,]', bloque, re.M))
    ids -= {'end', 'begin', 'private', 'public', 'protected', 'published'}
    _IDENT_UNIT[ruta] = ids
    return ids


def quita_units_no_usadas(src, inf, nombre):
    """Quita de los uses las units de Merge de las que el fichero no usa ningún identificador."""
    indice = _indice_merge(getattr(inf, 'dir_merge', None))
    if not indice:
        return src
    limpio = _limpia_comentarios(src)
    cuerpo = re.sub(r'\buses\b(?:[^;{]|\{[^}]*\})*;', ' ', limpio, flags=re.I)
    palabras = {w.lower() for w in re.findall(r'\b\w+\b', cuerpo)}
    propias = {x.lower() for x in inf.units_maxfactu | inf.units_convertidas}
    def fix(m):
        out = []
        for p in m.group(1).split(','):
            u = re.sub(r'\{[^}]*\}', '', p).strip()
            ul = u.lower()
            if ul and ul not in propias and ul in indice:
                ids = identificadores_interface(indice[ul])
                if ids and not any(i.lower() in palabras for i in ids):
                    inf.auto.append('%s: uses %s eliminada (no se usa nada de ella)' % (nombre, u))
                    continue
            out.append(p)
        return 'uses' + ','.join(out) + ';' if any(x.strip() for x in out) else ''
    return re.sub(r'\buses\b((?:[^;{]|\{[^}]*\})*);', fix, src, flags=re.I)


def comprueba_units(src, inf, nombre):
    limpio = _limpia_comentarios(src)
    for m in re.finditer(r'\buses\b(.*?);', limpio, re.S | re.I):
        for u in [x.strip().split()[0] for x in m.group(1).split(',') if x.strip()]:
            base = u.split('.')[0]
            if base in ('System', 'Vcl', 'Winapi', 'Data', 'FireDAC', 'VclTee', 'Xml', 'REST', 'Soap', 'Web'):
                continue
            if u.lower() in {x.lower() for x in inf.units_maxfactu | inf.units_convertidas}:
                continue
            inf.revisar.append('%s: usa la unidad "%s", que no existe en MaxFactu (convertir o sustituir).' % (nombre, u))
            inf.cuenta('unidades de Merge sin equivalente')


# Miembros de Entorno/DMMain que el conversor ya redirige a UAuxMerge (no se avisan como ausentes)
COMPAT_ENTORNO = {'ColorCampoID', 'ColorEdtFnd', 'DatosAbiertos', 'Delegacion', 'SerieRestringida', 'ColorEnlaceActivo', 'DirectorioComunicaciones',  'DatosAbiertos', 'Delegacion', 'SerieRestringida',
                  'ColorEnlaceActivo', 'DirectorioComunicaciones'}
COMPAT_DMMAIN = {'FiltraRO', 'FiltraSQL', 'MinTercero', 'AbrirArchivo', 'DameDirectorioComunicaciones',
                 'DameDirectorioCodCliPro'}


def comprueba_api(src, api_entorno, api_dmmain, inf, nombre):
    comprueba_units(src, inf, nombre)
    limpio = _limpia_comentarios(src)
    ae = {x.lower() for x in api_entorno} | {x.lower() for x in COMPAT_ENTORNO}
    ad = {x.lower() for x in api_dmmain} | {x.lower() for x in COMPAT_DMMAIN}
    faltan_e = sorted({x for x in re.findall(r'\bEntorno\.(\w+)', limpio) if x.lower() not in ae})
    faltan_d = sorted({x for x in re.findall(r'\bDMMain\.(\w+)', limpio) if x.lower() not in ad})
    for x in faltan_e:
        inf.revisar.append('%s: Entorno.%s no existe en UEntorno de MaxFactu (añadir al TEntorno).' % (nombre, x))
    for x in faltan_d:
        inf.revisar.append('%s: DMMain.%s no existe en UDMMain de MaxFactu (portar la función).' % (nombre, x))
    inf.cuenta('API: Entorno.* ausentes', len(faltan_e))
    inf.cuenta('API: DMMain.* ausentes', len(faltan_d))
    return faltan_e, faltan_d


# Destino de la conversión: 'maxfactu' (frames de MaxFactu) o 'merge13' (ventanas con la API de Merge)
PERFIL = 'maxfactu'


def conversiones_comunes(src, inf, nombre, ren=None):
    import conv_dfm as _cd
    for _k, _v in _cd.MAPA.items():
        TIPOS_COMPONENTE.setdefault(_k, _v[0])
    n0 = src
    # Tipos (en declaraciones y en código)
    for a, b in TIPOS_COMPONENTE.items():
        src = reemplazo_en_codigo(src, r'\b%s\b' % a, b)
    # Acceso a datos FreeIB -> FireDAC
    reglas = [
        (r'\bREntorno\.', 'Entorno.'),
        (r'\bDMMain\.DataBase\b', 'DMMain.DB' if PERFIL == 'maxfactu' else 'DMMain.DataBase'),
        (r'\bDataBase\s*:=\s*DMMain\.DB\b', 'Connection := DMMain.DB'),
        (r'(?i)\bDatabase\s*:=', 'Connection :='),
        (r'\.SelectSQL\b', '.SQL'),
        (r'\.AsDouble\b', '.AsFloat'),          # FreeIB AsDouble -> FireDAC/TField AsFloat
        (r'\.AsLong\b', '.AsInteger'),
        (r'(?<![\w.])SelectSQL\b', 'SQL'),
        (r'\.Params\.ByName\s*\(', '.ParamByName('),
        (r'(?<![\w.])Params\.ByName\s*\(', 'ParamByName('),
        (r'(?<![\w.])(DecimalSeparator|ThousandSeparator|ShortDateFormat|LongDateFormat|DateSeparator|'
         r'TimeSeparator|CurrencyString|ShortTimeFormat|LongTimeFormat)\b',
         r'FormatSettings.\1'),
        (r'FormatSettings\.FormatSettings\.', 'FormatSettings.'),
    ]
    for p, r in [(r'\.Params\.ByName\s*\[([^\]\[;]+)\]', r'.ParamByName(\1)'),
                 (r'(?<![\w.])Params\.ByName\s*\[([^\]\[;]+)\]', r'ParamByName(\1)'),
                 (r'\bFieldByName\s*\[([^\]\[;]+)\]', r'FieldByName(\1)')]:
        antes = src
        src = reemplazo_sin_comentarios(src, p, r)
        if src != antes:
            inf.cuenta('ByName[]/FieldByName[] -> ()', len(re.findall(p, antes)))
    for p, r in reglas:
        src = reemplazo_en_codigo(src, p, r)
    if ren:
        for a, b in ren.items():
            src = reemplazo_en_codigo(src, r'\b%s' % a, b)
    src = reemplazo_en_literales(src, sql_literal)
    # propiedades de FreeIB sin equivalente en TFDQuery: la sentencia se comenta
    for prop in ('AutoTrans', 'BufferChunks', 'UsaNulls', 'ParamCheck', 'GoToFirstRecordOnExecute'):
        patron = r'^([ \t]*)((?:[\w.]+\.)?%s\s*:=[^;\n]*;)' % prop
        k = len(re.findall(patron, src, flags=re.M))
        if k:
            src = re.sub(patron, r'\1// \2  // FreeIB: sin equivalente en FireDAC', src, flags=re.M)
            inf.cuenta('sentencias FreeIB comentadas', k)
    for patron, motivo in ((r'\.(?:ColumnaInicial|Insercion|UsaDicG2K|AutoCambiarColumna|AutoPostEnCheckBox|'
                            r'AutoStartDrag|Tabla_a_buscar|CampoNum|CampoStr|CondicionBusqueda|Campos_Desplegar|'
                            r'CampoADevolver)\s*:=', 'propiedad de EditFind/GridFind sin equivalente'),
                           (r'(?<![\w.])Campo\s*:=', 'localizador de la base G2K'),
                           (r'(?<![\w.])ControlEdit\s*:=', 'TControlEdit')):
        lineas = re.findall(r'^[ \t]*[^/\n]*%s[^\n]*;[ \t]*\r?$' % patron, src, flags=re.M)
        if lineas:
            src = re.sub(r'^([ \t]*)([^/\n]*%s[^\n]*;)([ \t]*\r?)$' % patron,
                         r'\1// \2  // [G2K: %s]\3' % motivo, src, flags=re.M)
            inf.cuenta('sentencias de la base G2K comentadas', len(lineas))
    for corto in ('SysUtils', 'Classes', 'ComObj', 'Windows', 'Forms', 'Dialogs', 'Math', 'StrUtils', 'DateUtils',
                  'Variants', 'Graphics', 'Controls', 'ShellAPI', 'Messages', 'Registry', 'IniFiles', 'DB'):
        src = reemplazo_en_codigo(src, r'(?<![\w.])%s\.(?=[A-Za-z_])' % corto, EQUIV_UNITS.get(corto, corto) + '.')
    for u in list(getattr(inf, 'units_convertidas', [])):
        if u.upper().startswith('UFRM'):
            base = u[4:]
            src = reemplazo_en_codigo(src, r'\bTFM%s\b' % base, 'TFRM' + base)
            src = reemplazo_en_codigo(src, r'(?<![\w.])FM%s\b' % base, 'FRM' + base)
    # Delphi 6 admitía un parámetro vacío al final de una llamada: F(a, )
    k = len(re.findall(r',\s*\)', _limpia_comentarios(src)))
    src = reemplazo_en_codigo(src, r',\s*\)', ')')
    if k:
        inf.cuenta('parámetros vacíos al final de llamadas', k)
    if PERFIL == 'maxfactu':
        src = fmain_a_fmmain(src, inf, nombre)   # en Merge13 FMain existe con la API de Merge
    src = aplica_equivalencias(src, inf, nombre)
    src = sql_actualizacion_fib(src, inf, nombre)
    src = execquery_nativo(src, inf, nombre)
    src = transaccion_escritura(src, inf, nombre)
    src = aux_nativo(src, inf, nombre)
    limpio = _limpia_comentarios(src)
    # Avisos de construcciones que requieren decisión humana
    avisos = [
        (r'\bDBHandle\b|\bTRHandle\b', 'handle nativo de FreeIB'),
        (r'\bEFIBError\b|\bSQLCode\b|\bIBErrorCode\b', 'excepción FreeIB -> EFDDBEngineException'),
        (r'\bFR_\w+|\bTfr[A-Z]\w+|\bfrReport\b', 'FastReport 2'),
        (r'\bFetchAll\b', 'FetchAll: en FireDAC usar FetchOptions / Q.FetchAll'),
        (r'\.Current\b', '.Current (FIBQuery)'),

        (r'\bBuscaRO\b|\bDMMain\.Busca\b', 'búsqueda del framework G2K'),
        (r'\bPlan\.\w+', 'Plan (FreeIB)'),
        (r'\bFIBEvents\b|\bRegisterEvents\b', 'eventos -> TFDEventAlerter'),
        (r'\.Transaction\.Active\s*:=', 'Transaction.Active := -> StartTransaction/Commit'),
        (r'\bCEMain\b|\bEPMain\b|\bG2KTableLoc\b|\bFSMain\b', 'referencia a componente G2K eliminado'),
    ]
    for p, txt in avisos:
        for m in re.finditer(p, limpio):
            linea = limpio.count('\n', 0, m.start()) + 1
            inf.revisar.append('%s:%d  %s' % (nombre, linea, txt))
            inf.cuenta('avisos en código')
    return src


def convierte_pas_dm(src, inf, nombre, campos_tipos, updates, bloqueos, ren):
    src = reescribe_uses(src, USES_DM, conservar=('UDMMain', 'UUtiles', 'UEntorno'))
    src = conversiones_comunes(src, inf, nombre, ren)
    # gnugettext: TranslateComponent registra el módulo para retraducirlo; al destruirlo y volver a crearlo
    # (AbreData/CierraData) queda una referencia colgando. En un módulo de datos basta con traducir sus textos.
    k = len(re.findall(r'\bTranslateComponent\s*\(\s*Self\s*\)', _limpia_comentarios(src)))
    if k:
        src = reemplazo_en_codigo(src, r'\bTranslateComponent\s*\(\s*Self\s*\)', 'DefaultInstance.TranslateProperties(Self)')
        inf.auto.append('%s: TranslateComponent(Self) -> DefaultInstance.TranslateProperties(Self) (módulo de datos)' % nombre)
    # tipos de campos persistentes según el DFM nuevo
    for campo, cls in campos_tipos.items():
        src = re.sub(r'(\b%s\s*:\s*)T\w*Field\b' % re.escape(campo), r'\g<1>' + cls, src)
    # declarar los TFDUpdateSQL generados tras el primer TFDQuery
    decl = ''.join('    %s: TFDUpdateSQL;\r\n' % u for u in updates)
    src = re.sub(r'(class\(TDataModule\)\s*\r?\n)', r'\1' + decl.replace('\\', '\\\\'), src, count=1)
    # control de concurrencia
    if bloqueos:
        lineas = []
        for ds, tablas in bloqueos.items():
            for t, c, modo in tablas:
                lineas.append("  TControlConcurrencia.Registra(%s, '%s', '%s', %s);" % (ds, t, c.replace(' ', ''), modo))
        bloque = '\r\n  // Control de concurrencia (antes BloqOpt/UPDATE ficticio de TFIBTableSet)\r\n' + \
                 '\r\n'.join(lineas) + '\r\n'
        m = re.search(r'(procedure\s+T\w+\.\w*Create\s*\(\s*Sender\s*:\s*TObject\s*\)\s*;.*?\bbegin\b)', src,
                      re.S | re.I)
        if m:
            src = src[:m.end()] + bloque + src[m.end():]
            inf.auto.append('%s: registro de concurrencia añadido en OnCreate.' % nombre)
        src = re.sub(r'(\bimplementation\b\s*(?:\{[^}]*\}\s*)*)(uses\b)', r'\1\2 UControlConcurrencia,', src,
                     count=1) if re.search(r'\bimplementation\b\s*(?:\{[^}]*\}\s*)*uses\b', src) else \
            re.sub(r'(\bimplementation\b)', r'\1\r\n\r\nuses UControlConcurrencia;', src, count=1)
    src = renombra_units(src, inf, nombre)
    src = asegura_uses_interface(src, inf, nombre)
    src = completa_uses(src, inf, nombre)
    src = quita_duplicados_uses(src)
    comprueba_api(src, inf.api_entorno, inf.api_dmmain, inf, nombre)
    return src


def miembros_clase(texto):
    iface = texto.split('implementation')[0]
    iface = _limpia_comentarios(iface)
    nombres = set(re.findall(r'(?:procedure|function|property)\s+(\w+)', iface))
    for g in re.findall(r'^\s+([\w, ]+)\s*:\s*[\w\.<>\[\] ]+;', iface, re.M):
        nombres |= {x.strip() for x in g.split(',') if x.strip()}
    return nombres


def avisa_miembros_base(src, inf, nombre, miembros_merge, miembros_mf, propios):
    faltan = collections.Counter()
    limpio = _limpia_comentarios(src)
    impl = limpio.split('implementation', 1)[-1]
    for nm in miembros_merge - miembros_mf - propios:
        if len(nm) < 3:
            continue
        k = len(re.findall(r'(?<![\w.])%s\b' % re.escape(nm), impl))
        if k:
            faltan[nm] = k
    for nm, k in faltan.most_common():
        inf.revisar.append('%s: "%s" (%d usos) es miembro de la base Merge (TFPEdit/TG2KForm) y no existe en '
                           'la base MaxFactu.' % (nombre, nm, k))
    inf.cuenta('miembros de base Merge sin equivalente', len(faltan))


def convierte_pas_frame(src, inf, nombre, form_cls, frame_cls, frame_unit, base_cls, dm_cls, dm_global,
                        ds_locales, principal_ds, principal_q, buscadores, ctx, ren, eliminados):
    import conv_dfm as _cd
    if _cd.SIN_TEECHART:
        graf = re.findall(r'^\s*(\w+)\s*:\s*T(?:DBChart|Chart)\s*;', src, flags=re.M)
        if graf:
            patron = r'\b(?:%s)\.(?:Series|Title|SeriesList|Legend|LeftAxis|BottomAxis|Foot|View3D|RefreshData|' \
                     r'Print|CopyToClipboard\w*|SaveToBitmapFile|UndoZoom|Axes|Walls|BackWall)\b' % '|'.join(graf)
            k = len(re.findall(r'^[ \t]*[^/\n]*%s[^\n]*;[ \t]*\r?$' % patron, src, flags=re.M))
            src = re.sub(r'^([ \t]*)([^/\n]*%s[^\n]*;)([ \t]*\r?)$' % patron,
                         r'\1// \2  // [TeeChart no instalado]\3', src, flags=re.M)
            inf.cuenta('sentencias de gráficos comentadas', k)
        uf = USES_FRAME.replace('VclTee.TeEngine, VclTee.Series, VclTee.TeeProcs, VclTee.Chart, VclTee.DBChart, ', '')
        src = re.sub(r'^\s*\w+\s*:\s*T\w*Series\s*;\s*\r?\n', '', src, flags=re.M)
        src = re.sub(r'\b(\w+)\s*:\s*TDBChart\b', r'\1: TPanel', src)
    else:
        uf = USES_FRAME
    src = reescribe_uses(src, uf, conservar=('UDMMain', 'UUtiles', 'UEntorno', dm_cls[1:] if False else
                                                     'U' + dm_cls[1:]))
    src = re.sub(r'\bunit\s+\w+\s*;', 'unit %s;' % frame_unit, src, count=1)
    src = re.sub(r'\b%s\b' % form_cls, frame_cls, src)
    src = re.sub(r'\b%s\s*=\s*class\s*\(\s*\w+\s*\)' % frame_cls, '%s = class(%s)' % (frame_cls, base_cls), src)
    src = re.sub(r'\b%s\b\s*:\s*%s\s*;' % (form_cls[1:], frame_cls), '%s: %s;' % (frame_cls[1:], frame_cls), src)
    src = re.sub(r'\bF' + form_cls[2:] + r'\b', frame_cls[1:], src)   # variable global FMxxx -> FRMxxx
    # la instancia del DM ya no es global: DM propio por frame (patrón MaxFactu)
    src = reemplazo_en_codigo(src, r'\b%s\.' % dm_global, 'DM.')
    # Merge crea un DM por formulario con AbreDataVarias(TDMxxx, Variable, Self): se sustituye por el DM del frame
    m = re.search(r'AbreDataVarias\s*\(\s*T\w+\s*,\s*(\w+)\s*,\s*\w+\s*\)\s*;', src)
    if m:
        var = m.group(1)
        src = src.replace(m.group(0), '// (DM creado en el constructor, patrón MaxFactu)')
        src = re.sub(r'^\s*CierraData\s*\(\s*%s\s*\)\s*;[^\n]*\n' % var, '', src, flags=re.M)
        src = re.sub(r'^\s*%s\s*:\s*%s\s*;\s*\r?\n' % (var, dm_cls), '', src, flags=re.M)
        src = reemplazo_en_codigo(src, r'\b%s\b' % var, 'DM', flags=re.I)
        inf.auto.append('%s: AbreDataVarias(%s) -> DM propio del frame.' % (nombre, var))
    # Escribir en el campo de un control solo tiene sentido en edición: TDBEdit.OnChange también salta al
    # cargar/navegar registros, y asignar el campo en ese momento da "Dataset not in edit or insert mode".
    lineas = src.split('\n')
    for i, l in enumerate(lineas):
        m = re.match(r'^(\s*)(\w+)\.Field\.(Value|As\w+)\s*:=\s*(.*;)\s*(\r?)$', l)
        if not m:
            continue
        sig = next((x for x in lineas[i + 1:] if x.strip()), '')
        if re.match(r'\s*else\b', sig, re.I):
            inf.revisar.append('%s:%d  %s.Field.%s := ... seguido de else: comprobar que el dataset esté en edición.'
                               % (nombre, i + 1, m.group(2), m.group(3)))
            continue
        lineas[i] = '%sif %s.Field.DataSet.State in dsEditModes then %s.Field.%s := %s%s' % (
            m.group(1), m.group(2), m.group(2), m.group(3), m.group(4), m.group(5))
        inf.cuenta('asignaciones a Field protegidas con dsEditModes')
    src = '\n'.join(lineas)
    # Propiedades propias de EditFind usadas en código -> el TBuscadorCampo del control
    mapa_bus = {'Accion': 'Accion', 'CondicionBusqueda': 'CondicionBusqueda', 'SalirSiNoExiste': 'SalirSiNoExiste',
                'AutoCambiarFoco': 'AutoCambiarFoco', 'Tabla_a_buscar': 'Tabla', 'CampoADevolver': 'CampoDevolver'}
    for b in buscadores:
        for met in ('SetBufferText', 'ClearBufferText'):
            src = reemplazo_en_codigo(src, r'\b%s\.%s\b' % (b['control'], met), 'B%s.%s' % (b['control'], met))
        for vieja, nueva in mapa_bus.items():
            patron = r'\b%s\.%s\b' % (b['control'], vieja)
            k = len(re.findall(patron, _limpia_comentarios(src)))
            if k:
                src = reemplazo_en_codigo(src, patron, 'B%s.%s' % (b['control'], nueva))
                inf.auto.append('%s: %s.%s -> B%s.%s (%d)' % (nombre, b['control'], vieja, b['control'], nueva, k))
        otras = re.findall(r'\b%s\.(Campos_Desplegar|CampoNum|CampoStr|Filtros|OrdenadoPor|Plan|'
                           r'Tabla_asociada|Estilo|BuscarNums|BuscarChar)\b' % b['control'], _limpia_comentarios(src))
        for o in sorted(set(otras)):
            inf.revisar.append('%s: %s.%s se usa en código; propiedad de EditFind2000 sin equivalente en '
                               'TBuscadorCampo.' % (nombre, b['control'], o))
    # DataSources del DM -> DataSources locales del frame
    if principal_ds:
        src = reemplazo_en_codigo(src, r'\bDM\.%s\b' % principal_ds, 'DSCabecera')
    for d in ds_locales:
        src = reemplazo_en_codigo(src, r'\bDM\.%s\b' % d, d)
    src = conversiones_comunes(src, inf, nombre, ren)
    # líneas que solo configuran componentes G2K eliminados -> se comentan
    elim_re = r'\b(%s)\b' % '|'.join(sorted(set(eliminados) | {'CEMain', 'EPMain', 'G2KTableLoc', 'FSMain', 'CEMainPMEdit'}))
    def comenta(mm):
        linea = mm.group(0)
        inf.cuenta('líneas G2K comentadas')
        return re.sub(r'^(\s*)', r'\1// [G2K eliminado] ', linea)
    src = re.sub(r'^[ \t]*[^/\n]*%s[^\n]*;[ \t]*\r?$' % elim_re, comenta, src, flags=re.M)
    # quitar declaraciones de componentes eliminados
    for comp in eliminados:
        src = re.sub(r'^\s*%s\s*:\s*\w+\s*;\s*\r?\n' % re.escape(comp), '', src, flags=re.M)
    for t in TIPOS_ELIMINAR:
        src = re.sub(r'^\s*\w+\s*:\s*%s\s*;\s*\r?\n' % t, '', src, flags=re.M)
    # DataSources locales
    decl_ds = ''.join('    %s: TDataSource;\r\n' % d for d in sorted(ds_locales))
    decl_ds += ''.join('    %s: %s;\r\n' % (nm, cl) for nm, cl in ctx.nuevos_campos
                       if not re.search(r'^\s*%s\s*:' % nm, src, re.M))
    for nm in ctx.combos_value:
        k = len(re.findall(r'\b%s\.Value\b' % nm, src))
        if k:
            src = reemplazo_en_codigo(src, r'\b%s\.Value\b' % nm, nm + '.Text')
            inf.revisar.append('%s: %s.Value -> %s.Text (%d); el combo guardaba Values, revisar.' % (nombre, nm, nm, k))
    decl_bus = ''.join('    B%s: TBuscadorCampo;\r\n' % b['control'] for b in buscadores)
    decl_puentes = ''.join('    procedure %s%s;\r\n' % (a['nombre'], a['firma']) for a in ctx.adaptadores)
    src = re.sub(r'(=\s*class\(%s\)\s*\r?\n)' % base_cls, lambda m: m.group(1) + decl_ds, src, count=1)
    # los métodos puente van al final de la sección published (antes del primer private/protected/public)
    m = re.search(r'=\s*class\(%s\).*?\n([ \t]*(?:private|protected|public)\b)' % base_cls, src, re.S)
    if m and decl_puentes:
        src = src[:m.start(1)] + decl_puentes + src[m.start(1):]
    # private: DM, buscadores, contenedor
    priv = ('    DM: %s;\r\n' % dm_cls) + decl_bus + '    FVentanaContenedor: TForm;\r\n'
    # Contrato de MaxFactu con sus frames: FMMain llama a Filtra(Filtro) al abrir desde el menú.
    # En Merge el equivalente es FiltraXxx(Filtro: string): se genera Filtra que lo llama.
    mf = re.search(r'^\s*procedure\s+(Filtra\w+)\s*\(\s*Filtro\s*:\s*string\s*\)\s*;', src, re.M | re.I)
    tiene_filtra = re.search(r'^\s*procedure\s+Filtra\s*\(', src, re.M | re.I)
    filtra_decl = filtra_impl = ''
    if mf and not tiene_filtra:
        filtra_decl = '    procedure Filtra(Filtro: string);  // contrato MaxFactu -> %s\r\n' % mf.group(1)
        filtra_impl = ('procedure %s.Filtra(Filtro: string);\r\nbegin\r\n'
                       '  // MaxFactu abre el mantenimiento con datos; en Merge dependía de "Datos abiertos"\r\n'
                       '  if Filtro <> \'\' then\r\n    %s(Filtro)\r\n'
                       '  else if not DM.%s.Active then\r\n    DM.%s.Open;\r\nend;\r\n\r\n'
                       % (frame_cls, mf.group(1), principal_q, principal_q))
        inf.auto.append('%s: generado Filtra(Filtro) -> %s (contrato de FMMain de MaxFactu)' % (nombre, mf.group(1)))
    pub = (filtra_decl + '    constructor Create(AOwner: TComponent); override;\r\n'
           '    destructor Destroy; override;\r\n'
           '    procedure CerrarVentana;\r\n'
           '    property VentanaContenedor: TForm read FVentanaContenedor write FVentanaContenedor;\r\n')
    m = re.search(r'=\s*class\(%s\).*?\bprivate\b[^\r\n]*\r?\n' % base_cls, src, re.S)
    if m:
        src = src[:m.end()] + priv + src[m.end():]
    # sección public nueva al final de la clase (en Delphi los campos deben ir antes que métodos/propiedades)
    m = re.search(r'=\s*class\(%s\).*?\r?\n(\s*end\s*;)' % base_cls, src, re.S)
    if m:
        src = src[:m.start(1)] + '  public\r\n' + pub + src[m.start(1):]
    # constructor / destructor que llaman a FormCreate / FormClose originales
    tiene_create = re.search(r'procedure\s+%s\.FormCreate\b' % frame_cls, src)
    tiene_close = re.search(r'procedure\s+%s\.FormClose\b' % frame_cls, src)
    tiene_destroy = re.search(r'procedure\s+%s\.FormDestroy\b' % frame_cls, src)
    tiene_show = re.search(r'procedure\s+%s\.FormShow\b' % frame_cls, src)
    tiene_activate = re.search(r'procedure\s+%s\.FormActivate\b' % frame_cls, src)
    asign = ''.join('  %s.DataSet := DM.%s;\r\n' % (d, q) for d, q in sorted(ds_locales.items()) if q)
    busc = ''
    for b in buscadores:
        campos = ', '.join("'%s'" % c for c in b['campos'])
        if b['db']:
            busc += ("  B{c} := TBuscadorCampo.Crea(Self, {c}, '{t}', '{f}', '{d}', [{cs}], '{fe}');\r\n"
                     .format(c=b['control'], t=b['tabla'], f=b['campo'], d=b['devolver'] or b['campo'],
                             cs=campos, fe=b['filtro']))
        else:
            busc += ("  B{c} := TBuscadorCampo.CreaLibre(Self, {c}, '{t}', '{d}', [{cs}], '{fe}');\r\n"
                     .format(c=b['control'], t=b['tabla'], d=b['devolver'], cs=campos, fe=b['filtro']))
    # eventos y propiedades de los EditFind -> buscador; otras asignaciones
    import vcl_props as vp
    extra = ''
    for b in buscadores:
        for p, v in (b.get('props') or {}).items():
            extra += '  B%s.%s := %s;\r\n' % (b['control'], p, v.replace('\n', ' '))
        if b.get('condicion'):
            extra += "  B%s.CondicionBusqueda := %s;\r\n" % (
                b['control'], ' + '.join("'" + s.replace("'", "''") + " '" for s in b['condicion']))
        for ev, metodo in ctx.buscadores_eventos.get(b['control'], []):
            real = ctx.firmas.get(metodo.lower())
            if real is None:
                inf.revisar.append('%s.%s = %s: método no encontrado; no se enlaza.' % (b['control'], ev, metodo))
            elif real != vp.normaliza_firma('(Sender: TObject)'):
                inf.revisar.append('%s.%s = %s: firma %s distinta de TNotifyEvent; no se enlaza.'
                                   % (b['control'], ev, metodo, real))
            else:
                extra += '  B%s.%s := %s;\r\n' % (b['control'], ev, metodo)
                inf.cuenta('eventos EditFind -> TBuscadorCampo')
    for linea in ctx.asignaciones:
        extra += linea + '\r\n'
    puentes = ''
    for a in ctx.adaptadores:
        puentes += 'procedure {F}.%s%s;\r\n' % (a['nombre'], a['firma'])
        if a['locales']:
            puentes += 'var\r\n' + '\r\n'.join(a['locales']) + '\r\n'
        puentes += 'begin\r\n  // Método puente generado por el conversor (evento de Merge con otra firma)\r\n'
        puentes += '\r\n'.join(a['cuerpo']) + '\r\nend;\r\n\r\n'
    puentes = puentes.replace('{', '{{').replace('}', '}}').replace('{{F}}', '{F}')
    extra = extra.replace('{', '{{').replace('}', '}}')
    puentes += filtra_impl.replace('{', '{{').replace('}', '}}')
    ctor = (puentes + 'constructor {F}.Create(AOwner: TComponent);\r\n'
            'begin\r\n'
            '  inherited;\r\n'
            '  if ModoPruebaCarga then\r\n'
            '    Exit;  // prueba de carga de DFM sin base de datos (UAuxMerge)\r\n'
            '  // Módulo de datos propio del frame (patrón MaxFactu: una instancia por pestaña)\r\n'
            '  DM := {D}.Create(Self);\r\n'
            '  DSCabecera.DataSet := DM.{Q};\r\n'
            '{A}'
            '{B}'
            + extra +
            '  CargaIniFRame(Self);\r\n'
            '  PCMain.ActivePageIndex := 0;\r\n'
            '{C}'
            '{S}'
            'end;\r\n\r\n'
            'destructor {F}.Destroy;\r\n'
            'var\r\n'
            '  Accion: TCloseAction;\r\n'
            'begin\r\n'
            '  if ModoPruebaCarga or (DM = nil) then\r\n'
            '  begin\r\n'
            '    inherited;  // frame sin inicializar (prueba de carga o fallo en el constructor)\r\n'
            '    Exit;\r\n'
            '  end;\r\n'
            '  Accion := caFree;\r\n'
            '{X}'
            '  GuardaFrame(Self);\r\n'
            '  DM.Free;\r\n'
            '  inherited;\r\n'
            'end;\r\n\r\n'
            'procedure {F}.CerrarVentana;\r\n'
            'begin\r\n'
            '  if Assigned(FVentanaContenedor) then\r\n'
            '    FVentanaContenedor.Close;\r\n'
            'end;\r\n\r\n').format(
        F=frame_cls, D=dm_cls, Q=principal_q, A=asign, B=busc,
        C='  FormCreate(Self);  // código original de Merge\r\n' if tiene_create else '',
        S='  FormShow(Self);    // en Merge se ejecutaba al mostrar el formulario\r\n' if tiene_show else '',
        X=('  FormClose(Self, Accion);\r\n' if tiene_close else '') +
          ('  FormDestroy(Self);\r\n' if tiene_destroy else ''))
    # el constructor va detrás del uses de la implementación (o del {$R *.dfm} si no hay uses)
    m = re.search(r'\bimplementation\b(?:\s|\{[^}]*\})*(uses\b(?:[^;{]|\{[^}]*\})*;)?', src, re.I)
    corte = m.end() if m else len(src)
    src = src[:corte] + '\r\n\r\n' + ctor + src[corte:]
    if tiene_activate:
        inf.revisar.append('%s: FormActivate se ejecutaba al activar la ventana; en frames no existe. '
                           'Decidir si se llama al cambiar de pestaña en FMMain.' % nombre)
    # Close; (cerrar formulario) -> CerrarVentana
    src = reemplazo_en_codigo(src, r'(?<![\w.])Close\s*;', 'CerrarVentana;')
    inf.revisar.append('%s: "Close;" sustituido por CerrarVentana; revisar los casos en que Close se refería '
                       'a un dataset dentro de un with.' % nombre)
    limpio = _limpia_comentarios(src)
    for p, txt in [(r'(?<![\w.])(Caption|BorderStyle|FormStyle|WindowState|ModalResult|ActiveControl)\s*:=',
                    'propiedad de TForm usada en un frame'),
                   (r'\bShowModal\b', 'ShowModal de otro formulario (correcto), revisar si es del propio'),
                   (r'\bSelf\.(Show|Hide|BringToFront)\b', 'método de TForm')]:
        for m in re.finditer(p, limpio):
            linea = limpio.count('\n', 0, m.start()) + 1
            inf.revisar.append('%s:%d  %s' % (nombre, linea, txt))
    src = renombra_units(src, inf, nombre)
    src = asegura_uses_interface(src, inf, nombre)
    src = completa_uses(src, inf, nombre)
    src = quita_duplicados_uses(src)
    comprueba_api(src, inf.api_entorno, inf.api_dmmain, inf, nombre)
    return src


USES_UNIT_IMPL = ['Data.DB', 'FireDAC.Stan.Intf', 'FireDAC.Stan.Param', 'FireDAC.Comp.Client', 'FireDAC.DApt',
                  'UAuxMerge']


def convierte_pas_unit(src, inf, nombre):
    """Unit sin formulario ni DFM (p.ej. UDameDato): mismas reglas de código, uses ajustados."""
    src = conversiones_comunes(src, inf, nombre)
    src = renombra_units(src, inf, nombre)
    limpio = _limpia_comentarios(src)
    iface = limpio.split('implementation')[0]
    necesita_iface = bool(re.search(r'\bTFD(Query|Transaction|Connection)\b|\bTDataSet\b|\bTField\b', iface))
    def añade(src, seccion, unidades):
        if seccion == 'interface':
            m = re.search(r'(\binterface\b(?:\s|\{[^}]*\})*)(\buses\b((?:[^;{]|\{[^}]*\})*);)?', src, re.S | re.I)
        else:
            m = re.search(r'(\bimplementation\b(?:\s|\{[^}]*\})*)(\buses\b((?:[^;{]|\{[^}]*\})*);)?', src, re.S | re.I)
        if not m:
            return src
        ya = {re.sub(r'\{[^}]*\}', '', x).strip().lower() for x in (m.group(3) or '').split(',')}
        faltan = [u for u in unidades if u.lower() not in ya]
        if not faltan:
            return src
        if m.group(2):
            return src[:m.end(3)] + ', ' + ', '.join(faltan) + src[m.end(3):]
        return src[:m.end(1)] + 'uses ' + ', '.join(faltan) + ';\r\n\r\n' + src[m.end(1):]
    if necesita_iface:
        src = añade(src, 'interface', USES_UNIT_IMPL)
    else:
        src = añade(src, 'implementation', USES_UNIT_IMPL)
    src = asegura_uses_interface(src, inf, nombre)
    src = completa_uses(src, inf, nombre)
    src = quita_duplicados_uses(src)
    comprueba_api(src, inf.api_entorno, inf.api_dmmain, inf, nombre)
    return src


# ----------------------------------------------------------------------------------------------
#  API FreeIB -> FireDAC nativo (sin class helpers)
# ----------------------------------------------------------------------------------------------

LEE_RESULTADO = re.compile(r"\b(Fields\s*\[|FieldByName\s*\(|FieldByName\s*\[|Eof\b|EOF\b|HayDatos\b|RecordCount\b|"
                           r"FN\s*\(|Current\b|IsEmpty\b|Next\b)", re.I)
SQL_DEVUELVE = re.compile(r"^\s*'?\s*(SELECT|WITH)\b", re.I)
SQL_NO_DEVUELVE = re.compile(r"^\s*'?\s*(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|GRANT|SET|COMMENT|"
                             r"RECREATE|DECLARE|UPDATE\s+OR\s+INSERT)\b", re.I)


def _primer_sql(texto):
    for lit in re.findall(r"'((?:[^']|'')*)'", texto):
        l = lit.strip()
        if re.match(r'(SELECT|WITH|INSERT|UPDATE|DELETE|MERGE|EXECUTE|ALTER|CREATE|DROP|GRANT|SET|RECREATE)\b', l, re.I):
            return l.upper()
    return ''


def execquery_nativo(src, inf, nombre):
    """ExecQuery -> Open (si la sentencia devuelve filas o después se leen campos) o ExecSQL.
    FreeHandle -> Close (cierra el cursor para que el siguiente Open vuelva a ejecutar).
    HayDatos -> (not IsEmpty)."""
    mask = _limpia_comentarios(src)
    mask = re.sub(r"'(?:[^']|'')*'", lambda m: "'" + 'x' * (len(m.group(0)) - 2) + "'", mask)
    pos_exec = [m.start() for m in re.finditer(r'(?<![\w])ExecQuery\b', mask)]
    if not pos_exec:
        return src
    trozos, ult = [], 0
    abiertos = ejecutados = dudosos = 0
    for i, p in enumerate(pos_exec):
        ini = pos_exec[i - 1] + 9 if i else max(0, p - 3000)
        ini = max(ini, p - 3000)
        # corte hacia atrás en el inicio de la rutina
        rut = [m.end() for m in re.finditer(r'^\s*(?:function|procedure)\b', mask[ini:p], re.M | re.I)]
        if rut:
            ini = ini + rut[-1]
        antes_real = src[ini:p]
        fin = pos_exec[i + 1] if i + 1 < len(pos_exec) else min(len(src), p + 3000)
        despues = mask[p + 9:fin]
        corte = re.search(r'\bFreeHandle\b|\bFree\s*;|\bClose\s*;|^\s*(?:function|procedure)\b', despues, re.M | re.I)
        tramo = despues[:corte.start()] if corte else despues[:1500]
        sql = _primer_sql(antes_real)
        if SQL_DEVUELVE.match(sql):
            verbo = 'Open'
        elif SQL_NO_DEVUELVE.match(sql):
            verbo = 'ExecSQL'
        elif LEE_RESULTADO.search(tramo):
            verbo = 'Open'   # EXECUTE PROCEDURE con retorno, o SQL en variable que luego se lee
        elif sql.startswith('EXECUTE'):
            verbo = 'ExecSQL'
        else:
            verbo = 'ExecSQL'
            dudosos += 1
            linea = src.count('\n', 0, p) + 1
            inf.revisar.append('%s:%d  ExecQuery -> ExecSQL (no se ve la SQL ni se leen campos después; '
                               'si devuelve filas, cambiar a Open)' % (nombre, linea))
        if verbo == 'Open':
            abiertos += 1
        else:
            ejecutados += 1
        trozos.append(src[ult:p]); trozos.append(verbo); ult = p + len('ExecQuery')
    trozos.append(src[ult:])
    src = ''.join(trozos)
    inf.cuenta('ExecQuery -> Open', abiertos)
    inf.cuenta('ExecQuery -> ExecSQL', ejecutados)
    n = len(re.findall(r'\bFreeHandle\b', _limpia_comentarios(src)))
    src = reemplazo_en_codigo(src, r'\bFreeHandle\b', 'Close')
    inf.cuenta('FreeHandle -> Close', n)
    src = reemplazo_en_codigo(src, r'\b([\w.]+)\.HayDatos\b', r'(not \1.IsEmpty)')
    src = reemplazo_en_codigo(src, r'(?<![\w.])HayDatos\b', '(not IsEmpty)')
    return src


def carga_equivalencias(ruta):
    """Fichero de texto editable:  origen => destino   (una por línea, # comentario)."""
    reglas = []
    import os
    if ruta and os.path.exists(ruta):
        for linea in open(ruta, encoding='utf-8'):
            linea = linea.split('#', 1)[0].strip()
            if '=>' in linea:
                a, b = [x.strip() for x in linea.split('=>', 1)]
                if a:
                    reglas.append((a, b))
    return reglas


def aplica_equivalencias(src, inf, nombre):
    """Aplica todas las equivalencias en una sola pasada (una sustitución no se vuelve a sustituir)."""
    reglas = getattr(inf, 'equivalencias', [])
    if not reglas:
        return src
    dic = {a: b for a, b in reglas}
    orden = sorted(dic, key=len, reverse=True)
    patron = r'(?<![\w])(' + '|'.join(re.escape(a) for a in orden) + r')(?!\w)'
    cuenta = collections.Counter()
    def r(m):
        cuenta[m.group(1)] += 1
        return dic[m.group(1)]
    src = reemplazo_en_codigo(src, patron, r)
    for a, k in cuenta.items():
        inf.auto.append('%s: %s -> %s (%d)' % (nombre, a, dic[a], k))
    return src


# Lo que no existe en MaxFactu y se aporta como funciones en UAuxMerge.pas (DMMain.X -> X)
AUX_DMMAIN_INDEXADOS = {'TituloEstado', 'TituloSituacionProduccion'}
AUX_DMMAIN = {'TituloEstado', 'TituloSituacionProduccion', 'TituloUnidadMedida', 'TituloPeriodoFacturacion',
              'FiltraRO', 'FiltraSQL', 'MinTercero', 'AbrirArchivo', 'DameDirectorioComunicaciones',
              'DameDirectorioCodCliPro'}


def aux_nativo(src, inf, nombre):
    for x in AUX_DMMAIN_INDEXADOS:
        src = reemplazo_sin_comentarios(src, r'\bDMMain\.%s\s*\[([^\]\[]+)\]' % x, r'%s(\1)' % x)
    for x in AUX_DMMAIN:
        src = reemplazo_en_codigo(src, r'\bDMMain\.%s\b' % x, x)
    # Entorno.XxxStr -> IntToStr(Entorno.Xxx)
    for x in ('Empresa', 'Ejercicio', 'Canal', 'Entrada'):
        src = reemplazo_en_codigo(src, r'\bEntorno\.%sStr\b' % x, 'IntToStr(Entorno.%s)' % x)
    # métodos propios de TFIBTableSet -> funciones de UAuxMerge
    src = reemplazo_sin_comentarios(src, r'\b([\w.]+)\.Ordenar\s*\(', r'Ordenar(\1, ')
    src = reemplazo_en_codigo(src, r'\b([\w.]+)\.OrdenadoPor\b', r'OrdenadoPor(\1)')
    src = reemplazo_sin_comentarios(src, r'\b([\w.]+)\.DameFiltroSelect\s*\(', r'DameFiltroSelect(\1, ')
    limpio = _limpia_comentarios(src)
    for m in re.finditer(r'(?<![\w.(])(Ordenar|OrdenadoPor|DameFiltroSelect)\b(?!\s*\(\s*[\w.]+\s*[,)])', limpio):
        linea = limpio.count('\n', 0, m.start()) + 1
        inf.revisar.append('%s:%d  %s dentro de un "with": añadir el dataset como primer parámetro' %
                           (nombre, linea, m.group(1)))
    return src


# Unidad de Delphi 13 que declara cada tipo que puede aparecer tras la conversión
UNIDAD_DE_TIPO = {}
for _u, _ts in {
    'Vcl.DBCtrls': 'TDBNavigator TDBEdit TDBCheckBox TDBComboBox TDBMemo TDBText TDBLookupComboBox TDBRadioGroup '
                   'TDBImage TDBRichEdit TNavigateBtn TDBLookupListBox',
    'Vcl.DBGrids': 'TDBGrid TColumn TDBGridOptions', 'Vcl.DBCGrids': 'TDBCtrlGrid',
    'Vcl.StdCtrls': 'TLabel TEdit TMemo TCheckBox TComboBox TButton TGroupBox TRadioButton TListBox TStaticText '
                    'TScrollBar TCustomEdit',
    'Vcl.ExtCtrls': 'TPanel TImage TBevel TShape TRadioGroup TSplitter TTimer TLabeledEdit TPaintBox TNotebook',
    'Vcl.ComCtrls': 'TPageControl TTabSheet TToolBar TToolButton TDateTimePicker TProgressBar TTreeView TListView '
                    'TStatusBar TUpDown TTrackBar TRichEdit TTabControl TTreeNode TListItem TMonthCalendar',
    'Vcl.Buttons': 'TBitBtn TSpeedButton', 'Vcl.ActnList': 'TActionList TAction', 'System.Actions': 'TContainedAction',
    'Vcl.Menus': 'TPopupMenu TMenuItem TMainMenu', 'Vcl.Grids': 'TStringGrid TGridDrawState TDrawGrid',
    'Vcl.Forms': 'TForm TFrame TScrollBox TCloseAction TFormClass', 'Vcl.Samples.Spin': 'TSpinEdit',
    'Vcl.Mask': 'TMaskEdit', 'Vcl.CheckLst': 'TCheckListBox', 'Vcl.ValEdit': 'TValueListEditor',
    'Vcl.ImgList': 'TImageList', 'Vcl.Controls': 'TWinControl TControl TMouseButton TDragState TKeyEvent',
    'Vcl.Dialogs': 'TOpenDialog TSaveDialog TFontDialog TPrinterSetupDialog', 'Vcl.ExtDlgs': 'TOpenPictureDialog',
    'Vcl.Graphics': 'TColor TBitmap TCanvas TFont', 'System.Classes': 'TComponent TStrings TStringList TShiftState',
    'Data.DB': 'TDataSource TDataSet TField TStringField TIntegerField TSmallintField TFloatField TCurrencyField '
               'TBCDField TFMTBCDField TDateTimeField TDateField TSQLTimeStampField TBlobField TMemoField '
               'TLargeintField TBooleanField TWideStringField TDataSetNotifyEvent TUpdateAction',
    'FireDAC.Comp.Client': 'TFDQuery TFDTransaction TFDUpdateSQL TFDConnection TFDMemTable TFDCommand TFDStoredProc',
    'FireDAC.Stan.Param': 'TFDParam TFDParams', 'FireDAC.Comp.DataSet': 'TFDDataSet',
    'FireDAC.Stan.Intf': 'TFDPhysMonitor', 'FireDAC.DApt': 'TFDDAptTableAdapter',
    'Vcl.OleCtrls': 'TOleControl', 'SHDocVw': 'TWebBrowser', 'Vcl.Samples.Gauges': 'TGauge',
}.items():
    for _t in _ts.split():
        UNIDAD_DE_TIPO[_t] = _u
# FireDAC necesita estas units para que los TFDQuery del DFM funcionen en tiempo de ejecución
FIREDAC_EXTRA = ['FireDAC.Stan.Intf', 'FireDAC.Stan.Option', 'FireDAC.Stan.Param', 'FireDAC.Stan.Error',
                 'FireDAC.DatS', 'FireDAC.Phys.Intf', 'FireDAC.DApt.Intf', 'FireDAC.Stan.Async', 'FireDAC.DApt',
                 'FireDAC.Comp.DataSet']


def asegura_uses_interface(src, inf, nombre):
    """Añade al uses de la interface las units que declaran los tipos usados en ella."""
    corte = re.search(r'\bimplementation\b', src, re.I)
    if not corte:
        return src
    iface = _limpia_comentarios(src[:corte.start()])
    faltan = []
    m = re.search(r'\binterface\b(?:\s|\{[^}]*\})*uses\b((?:[^;{]|\{[^}]*\})*);', src[:corte.start()], re.I | re.S)
    ya = {re.sub(r'\{[^}]*\}', '', x).strip().lower() for x in (m.group(1) if m else '').split(',')}
    for t in sorted(set(re.findall(r'\bT\w+\b', iface))):
        u = UNIDAD_DE_TIPO.get(t)
        if u and u.lower() not in ya and u not in faltan:
            faltan.append(u)
    if 'FireDAC.Comp.Client' in faltan or 'fireDAC.comp.client' in ya:
        faltan += [u for u in FIREDAC_EXTRA if u.lower() not in ya and u not in faltan]
    if not faltan:
        return src
    inf.auto.append('%s: uses de interface completado con %s' % (nombre, ', '.join(faltan)))
    if m:
        return src[:m.end(1)] + ', ' + ', '.join(faltan) + src[m.end(1):]
    mi = re.search(r'\binterface\b', src, re.I)
    return src[:mi.end()] + '\r\n\r\nuses\r\n  ' + ', '.join(faltan) + ';\r\n' + src[mi.end():]


# ----------------------------------------------------------------------------------------------
#  FMain (Merge) -> FMMain (MaxFactu)
# ----------------------------------------------------------------------------------------------

def _equiv_fmain():
    import os
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fmain_equivalencias.txt')
    d = {}
    if os.path.exists(ruta):
        for l in open(ruta, encoding='utf-8'):
            l = l.split('#', 1)[0].strip()
            if '=>' in l:
                a, b = [x.strip() for x in l.split('=>', 1)]
                d[a.lower()] = b
    return d


def fmain_a_fmmain(src, inf, nombre):
    """Toda referencia a FMain pasa a FMMain siguiendo las convenciones de MaxFactu:
    - FMain.EjecutaAccion(A, F)      -> FMMain.EjecutaAccionFiltro(FMMain.A, F, True)
    - FMain.MuestraAdunto(Tipo, Id)  -> MuestraAdjuntos(Id, Tipo, <título del registro>)   (UUtiles)
    - FMain.MuestraInfoTercero(T)    -> FMMain.EjecutaAccionFiltro(FMMain.ATerceros, ' TERCERO = ' + IntToStr(T), True)
    - FMain.X                        -> FMMain.<equivalencia de X> (fmain_equivalencias.txt)
    Los miembros usados se anotan para añadir a UFMMain.pas los que no existan."""
    import llamadas
    eq = _equiv_fmain()
    usados = getattr(inf, 'fmain_usados', None)
    if usados is None:
        usados = inf.fmain_usados = set()

    def miembro(x):
        x = x.strip()
        m = re.match(r'FMain\.(\w+)$', x, re.I)
        if m:
            nuevo = eq.get(m.group(1).lower(), m.group(1))
            usados.add(nuevo)
            return 'FMMain.' + nuevo
        return x

    def ejecuta(args, m):
        accion = miembro(args[0])
        filtro = args[1] if len(args) > 1 and args[1] else "''"
        inf.cuenta('FMain.EjecutaAccion -> FMMain.EjecutaAccionFiltro')
        return 'FMMain.EjecutaAccionFiltro(%s, %s, True)' % (accion, filtro)
    src = llamadas.reescribe(src, r'\bFMain\s*\.\s*EjecutaAccion\b', ejecuta)

    def adjunto(args, m):
        if len(args) < 2:
            return None
        inf.cuenta('FMain.MuestraAdunto -> MuestraAdjuntos')
        return 'MuestraAdjuntos(%s, %s, %s)' % (args[1], args[0], getattr(inf, 'titulo_adjunto', "''"))
    src = llamadas.reescribe(src, r'\bFMain\s*\.\s*MuestraAdunto\b', adjunto)

    def info_tercero(args, m):
        usados.add('ATerceros')
        inf.cuenta('FMain.MuestraInfoTercero -> Terceros filtrado')
        return "FMMain.EjecutaAccionFiltro(FMMain.ATerceros, ' TERCERO = ' + IntToStr(%s), True)" % args[0]
    src = llamadas.reescribe(src, r'\bFMain\s*\.\s*MuestraInfoTercero\b', info_tercero)

    def resto(m):
        nuevo = eq.get(m.group(1).lower(), m.group(1))
        usados.add(nuevo)
        return 'FMMain.' + nuevo
    src = reemplazo_en_codigo(src, r'\bFMain\s*\.\s*(\w+)', resto, flags=re.I)
    src = reemplazo_en_codigo(src, r'(?<![\w.])FMain\b', 'FMMain', flags=re.I)
    return src


# ----------------------------------------------------------------------------------------------
#  Merge13: el formulario de Merge sigue siendo un formulario (misma unit, clase y base)
# ----------------------------------------------------------------------------------------------

def _inserta_en_formcreate(src, form_cls, lineas, inf, nombre):
    """Inserta líneas al principio de FormCreate (tras 'inherited;'). Si no hay FormCreate, lo crea."""
    if not lineas:
        return src, False
    bloque = '  // --- merge2m13: inicialización de componentes sustituidos ---\r\n' + ''.join(
        '  ' + l.strip() + '\r\n' for l in lineas)
    m = re.search(r'procedure\s+%s\.FormCreate\s*\(\s*Sender\s*:\s*TObject\s*\)\s*;.*?\bbegin\b' % form_cls, src,
                  re.S | re.I)
    if m:
        resto = src[m.end():]
        mi = re.match(r'(\s*inherited\s*;)', resto, re.I)
        corte = m.end() + (mi.end() if mi else 0)
        # Si FormCreate crea el módulo de datos (AbreData/AbreDataVarias), la inicialización va detrás:
        # puede usar sus DataSources (p.ej. DMFamilias.DSQMFamilias.OnStateChange)
        fin_metodo = re.search(r'\n\s*end\s*;', resto)
        cuerpo = resto[:fin_metodo.start()] if fin_metodo else resto
        ab = None
        for ab in re.finditer(r'\bAbreData(?:Varias)?\s*\([^;]*\)\s*;[^\n]*\n', cuerpo, re.I):
            pass
        if ab is not None:
            corte = m.end() + ab.end()
            return src[:corte] + bloque + src[corte:], False
        return src[:corte] + '\r\n' + bloque + src[corte:], False
    impl = ('procedure %s.FormCreate(Sender: TObject);\r\nbegin\r\n  inherited;\r\n%send;\r\n\r\n' % (form_cls, bloque))
    src = re.sub(r'(\{\$R \*\.(?:dfm|DFM)\}\s*\r?\n(?:\s*uses\b(?:[^;{]|\{[^}]*\})*;)?)',
                 lambda mm: mm.group(1) + '\r\n\r\n' + impl, src, count=1, flags=re.I)
    src = re.sub(r'(%s\s*=\s*class\([^)]*\)\s*\r?\n)' % form_cls,
                 lambda mm: mm.group(1) + '    procedure FormCreate(Sender: TObject);\r\n', src, count=1)
    inf.auto.append('%s: creado FormCreate para inicializar los componentes sustituidos' % nombre)
    return src, True


def convierte_pas_form_m13(src, inf, nombre, form_cls, ctx, eliminados, registro):
    import vcl_props as vp
    src = conversiones_comunes(src, inf, nombre)
    # --- componentes eliminados: fuera sus campos; las sentencias que los usan se comentan
    for comp in eliminados:
        src = re.sub(r'^\s*%s\s*:\s*\w+\s*;[^\n]*\n' % re.escape(comp), '', src, flags=re.M)
    elim = sorted(set(eliminados) | {'CEMain', 'EPMain', 'G2KTableLoc', 'FSMain', 'CEMainPMEdit'})
    if elim:
        elim_re = r'\b(%s)\b' % '|'.join(map(re.escape, elim))
        def comenta(mm):
            inf.cuenta('líneas G2K comentadas')
            return re.sub(r'^(\s*)', r'\1// [G2K eliminado] ', mm.group(0))
        src = re.sub(r'^[ \t]*[^/\n]*%s[^\n]*;[ \t]*\r?$' % elim_re, comenta, src, flags=re.M | re.I)
    # --- navegador HY de Merge: EditaControl/InsertaControl (foco al editar/insertar) -> EnfocaControl (UFormGest)
    k = len(re.findall(r'\b\w+\.(?:EditaControl|InsertaControl)\s*:=', _limpia_comentarios(src), flags=re.I))
    if k:
        src = reemplazo_en_codigo(src, r'\b\w+\.(?:EditaControl|InsertaControl)\s*:=\s*([\w.]+)', r'EnfocaControl(\1)',
                                  flags=re.I)
        inf.cuenta('EditaControl/InsertaControl -> EnfocaControl', k)
    # --- asignar campos solo en edición (OnChange de TDBEdit salta también al navegar)
    lineas = src.split('\n')
    for i, l in enumerate(lineas):
        m = re.match(r'^(\s*)(\w+)\.Field\.(Value|As\w+)\s*:=\s*(.*;)\s*(\r?)$', l)
        if m and not re.match(r'\s*else\b', next((x for x in lineas[i + 1:] if x.strip()), ''), re.I):
            lineas[i] = '%sif %s.Field.DataSet.State in dsEditModes then %s.Field.%s := %s%s' % (
                m.group(1), m.group(2), m.group(2), m.group(3), m.group(4), m.group(5))
            inf.cuenta('asignaciones a Field protegidas con dsEditModes')
    src = '\n'.join(lineas)
    # --- EditFind: propiedades y métodos -> TBuscadorCampo
    mapa_bus = {'Accion': 'Accion', 'CondicionBusqueda': 'CondicionBusqueda', 'SalirSiNoExiste': 'SalirSiNoExiste',
                'AutoCambiarFoco': 'AutoCambiarFoco', 'Tabla_a_buscar': 'Tabla', 'CampoADevolver': 'CampoDevolver'}
    for b in ctx.buscadores:
        for met in ('SetBufferText', 'ClearBufferText'):
            src = reemplazo_en_codigo(src, r'\b%s\.%s\b' % (b['control'], met), 'B%s.%s' % (b['control'], met))
        for vieja, nueva in mapa_bus.items():
            src = reemplazo_en_codigo(src, r'\b%s\.%s\b' % (b['control'], vieja), 'B%s.%s' % (b['control'], nueva))
    for nm in ctx.combos_value:
        src = reemplazo_en_codigo(src, r'\b%s\.Value\b' % nm, nm + '.Text')
    # --- declaraciones nuevas: campos de componentes que ya no heredan, puentes y buscadores
    decl_pub = ''.join('    %s: %s;\r\n' % (nm, cl) for nm, cl in ctx.nuevos_campos
                       if not re.search(r'^\s*%s\s*:' % nm, src, re.M))
    src = re.sub(r'(%s\s*=\s*class\([^)]*\)\s*\r?\n)' % form_cls, lambda m: m.group(1) + decl_pub, src, count=1)
    decl_puentes = ''.join('    procedure %s%s;\r\n' % (a['nombre'], a['firma']) for a in ctx.adaptadores)
    if decl_puentes:
        m = re.search(r'%s\s*=\s*class\(.*?\n([ \t]*(?:private|protected|public)\b|[ \t]*end\s*;)' % form_cls, src, re.S)
        src = src[:m.start(1)] + decl_puentes + src[m.start(1):]
    decl_priv = ''.join('    B%s: TBuscadorCampo;\r\n' % b['control'] for b in ctx.buscadores)
    if decl_priv:
        m = re.search(r'%s\s*=\s*class\(.*?\n(\s*private\b[^\r\n]*\r?\n)' % form_cls, src, re.S)
        if m:
            src = src[:m.end(1)] + decl_priv + src[m.end(1):]
        else:
            m = re.search(r'%s\s*=\s*class\(.*?\r?\n(\s*(?:public|protected)\b|\s*end\s*;)' % form_cls, src, re.S)
            src = src[:m.start(1)] + '\r\n  private\r\n' + decl_priv + src[m.start(1):]
    # --- inicialización en FormCreate: buscadores, propiedades y eventos que antes tenía el componente
    ini = []
    for b in ctx.buscadores:
        campos = ', '.join("'%s'" % c for c in b['campos'])
        if b['db']:
            ini.append("B{c} := TBuscadorCampo.Crea(Self, {c}, '{t}', '{f}', '{d}', [{cs}], '{fe}');".format(
                c=b['control'], t=b['tabla'], f=b['campo'], d=b['devolver'] or b['campo'], cs=campos, fe=b['filtro']))
        else:
            ini.append("B{c} := TBuscadorCampo.CreaLibre(Self, {c}, '{t}', '{d}', [{cs}], '{fe}');".format(
                c=b['control'], t=b['tabla'], d=b['devolver'], cs=campos, fe=b['filtro']))
        for p, v in (b.get('props') or {}).items():
            ini.append('B%s.%s := %s;' % (b['control'], p, v.replace('\n', ' ')))
        for ev, metodo in ctx.buscadores_eventos.get(b['control'], []):
            if ctx.firmas.get(metodo.lower()) == vp.normaliza_firma('(Sender: TObject)'):
                ini.append('B%s.%s := %s;' % (b['control'], ev, metodo))
    ini += [l.strip() for l in ctx.asignaciones]
    src, creado = _inserta_en_formcreate(src, form_cls, ini, inf, nombre)
    ctx.formcreate_creado = creado
    # --- métodos puente
    if ctx.adaptadores:
        puentes = ''
        for a in ctx.adaptadores:
            puentes += 'procedure %s.%s%s;\r\n' % (form_cls, a['nombre'], a['firma'])
            if a['locales']:
                puentes += 'var\r\n' + '\r\n'.join(a['locales']) + '\r\n'
            puentes += 'begin\r\n' + '\r\n'.join(a['cuerpo']) + '\r\nend;\r\n\r\n'
        src = re.sub(r'(\{\$R \*\.(?:dfm|DFM)\}\s*\r?\n(?:\s*uses\b(?:[^;{]|\{[^}]*\})*;)?)',
                     lambda mm: mm.group(1) + '\r\n\r\n' + puentes, src, count=1, flags=re.I)
    # --- registro del módulo en el menú de Merge13 (idempotente)
    src = re.sub(r'\r?\n?\s*// merge2m13-registro.*?// merge2m13-fin\r?\n', '\r\n', src, flags=re.S)
    if registro:
        bloque = '  // merge2m13-registro (la acción de FMain abre este módulo)\r\n  %s\r\n  // merge2m13-fin\r\n' % registro
        if re.search(r'^initialization\b', src, re.M | re.I):
            src = re.sub(r'(^initialization\b[^\n]*\n)', lambda mm: mm.group(1) + bloque, src, count=1,
                         flags=re.M | re.I)
        else:
            src = re.sub(r'\bend\.\s*$', 'initialization\r\n' + bloque + '\r\nend.\r\n', src.rstrip())
        if 'UModulos' not in src:
            src = re.sub(r'(\bimplementation\b(?:\s|\{[^}]*\})*uses\b)', r'\1 UModulos,', src, count=1, flags=re.I) \
                if re.search(r'\bimplementation\b(?:\s|\{[^}]*\})*uses\b', src, re.I) else \
                re.sub(r'(\{\$R \*\.(?:dfm|DFM)\})', r'\1\r\n\r\nuses UModulos;', src, count=1, flags=re.I)
    if ctx.buscadores and 'UBuscadorCampo' not in src:
        src = re.sub(r'(\binterface\b(?:\s|\{[^}]*\})*uses\b)', r'\1 UBuscadorCampo,', src, count=1, flags=re.I)
    src = renombra_units(src, inf, nombre)
    src = asegura_uses_interface(src, inf, nombre)
    src = completa_uses(src, inf, nombre)
    src = quita_duplicados_uses(src)
    comprueba_api(src, inf.api_entorno, inf.api_dmmain, inf, nombre)
    return src


def _fin_sentencia(src, i):
    """Índice justo después del ';' que cierra la sentencia que empieza en i (respeta literales)."""
    j, n = i, len(src)
    while j < n:
        c = src[j]
        if c == "'":
            j += 1
            while j < n and not (src[j] == "'" and (j + 1 >= n or src[j + 1] != "'")):
                j += 2 if src[j] == "'" else 1
        elif c == ';':
            return j + 1
        j += 1
    return n


def sql_actualizacion_fib(src, inf, nombre):
    """InsertSQL/UpdateSQL/DeleteSQL/RefreshSQL de datasets FIB creados en código: FireDAC genera esa SQL
    automáticamente para consultas de una tabla (UpdateOptions), así que las asignaciones se comentan."""
    mask = _limpia_comentarios(src)
    mask = re.sub(r"'(?:[^']|'')*'", lambda m: "'" + 'x' * (len(m.group(0)) - 2) + "'", mask)
    trozos, pos, k = [], 0, 0
    for m in re.finditer(r'(?<![\w])((?:[\w.]+\.)?(?:InsertSQL|UpdateSQL|DeleteSQL|RefreshSQL)\.(?:Text\s*:=|Add\s*\(|Clear\b))', mask):
        if m.start() < pos:
            continue
        fin = _fin_sentencia(src, m.start())
        sentencia = src[m.start():fin]
        trozos.append(src[pos:m.start()])
        trozos.append('{ FireDAC genera esta SQL (UpdateOptions): ' + sentencia.replace('}', ')') + ' }')
        pos = fin
        k += 1
    trozos.append(src[pos:])
    if k:
        linea = src[:m.start()].count('\n') + 1 if False else 0
        inf.cuenta('SQL de actualización FIB en código -> generada por FireDAC', k)
        inf.revisar.append('%s: %d asignaciones InsertSQL/UpdateSQL/DeleteSQL/RefreshSQL comentadas (FireDAC las genera '
                           'si la consulta es de una tabla; si es una vista, revisar).' % (nombre, k))
    src = ''.join(trozos)
    # Transaction.InTransaction -> Active (en TFDConnection sí existe InTransaction)
    src = reemplazo_en_codigo(src, r'(?<![\w])((?![\w.]*(?:DataBase|Connection|DB)\b)[\w.]*Transaction\w*|TLocal\w*|TUpdate\w*)\.InTransaction\b',
                              r'\1.Active')
    return src


RTL_IDENT = {'CSIDL_': 'Winapi.ShlObj', 'SHGetSpecialFolderPath': 'Winapi.ShlObj', 'SHGetFolderPath': 'Winapi.ShlObj',
             'ShellExecute': 'Winapi.ShellAPI', 'IncludeTrailingPathDelimiter': 'System.SysUtils',
             'TRegistry': 'System.Win.Registry', 'TIniFile': 'System.IniFiles', 'TMemIniFile': 'System.IniFiles',
             'CreateOleObject': 'System.Win.ComObj', 'VarIsNull': 'System.Variants', 'Null': 'System.Variants',
             'TPath': 'System.IOUtils', 'TFile': 'System.IOUtils', 'TDirectory': 'System.IOUtils',
             'Clipboard': 'Vcl.Clipbrd', 'TJPEGImage': 'Vcl.Imaging.jpeg', 'TPngImage': 'Vcl.Imaging.pngimage',
             'TGIFImage': 'Vcl.Imaging.GIFImg', 'Printer': 'Vcl.Printers', 'Max': 'System.Math', 'Min': 'System.Math',
             'RoundTo': 'System.Math', 'SimpleRoundTo': 'System.Math', 'StartsText': 'System.StrUtils',
             'AnsiReplaceStr': 'System.StrUtils', 'IfThen': 'System.StrUtils', 'DaysBetween': 'System.DateUtils',
             'IncMonth': 'System.SysUtils', 'StartOfTheMonth': 'System.DateUtils', 'EndOfTheMonth': 'System.DateUtils',
             'YearOf': 'System.DateUtils', 'MonthOf': 'System.DateUtils', 'DayOf': 'System.DateUtils'}
_IDX_PROYECTO = None


def indice_proyecto(dir_proyecto):
    """identificador -> [units] con lo que declaran las interfaces de las units del proyecto Merge13."""
    global _IDX_PROYECTO
    if _IDX_PROYECTO is None:
        import glob, os
        _IDX_PROYECTO = collections.defaultdict(list)
        for p in glob.glob(os.path.join(dir_proyecto, '**', '*.pas'), recursive=True):
            if '_dcu' in p or '__history' in p or 'jedi' in p.lower():
                continue
            u = os.path.basename(p)[:-4]
            for ident in identificadores_interface(p):
                _IDX_PROYECTO[ident.lower()].append(u)
    return _IDX_PROYECTO


def completa_uses(src, inf, nombre):
    """Añade al uses de la implementación las units del proyecto (y de la RTL) que declaran identificadores que el
    fichero usa y que no tiene accesibles."""
    proy = getattr(inf, 'dir_proyecto', None)
    if not proy:
        return src
    idx = indice_proyecto(proy)
    limpio = _limpia_comentarios(src)
    limpio_sin_lit = re.sub(r"'(?:[^']|'')*'", "''", limpio)
    usadas = {u.lower() for u in [x.split('.')[-1] for x in re.findall(r'[\w.]+', ' '.join(
        m.group(1) for m in re.finditer(r'\buses\b(.*?);', limpio, re.S | re.I)))]}
    usadas |= {x.lower() for m in re.finditer(r'\buses\b(.*?);', limpio, re.S | re.I)
               for x in re.findall(r'[\w.]+', m.group(1))}
    propia = nombre[:-4].lower() if nombre.lower().endswith('.pas') else nombre.lower()
    locales = {x.lower() for x in re.findall(r'\b(?:procedure|function|constructor)\s+(?:\w+\.)?(\w+)', limpio, re.I)}
    locales |= {x.lower() for x in re.findall(r'^\s*(\w+)\s*[:=]', limpio, re.M)}
    anadir = []
    for ident in sorted(set(re.findall(r'\b([A-Za-z_]\w*)\b', limpio_sin_lit))):
        k = ident.lower()
        if k in locales:
            continue
        cands = [u for u in idx.get(k, []) if u.lower() != propia]
        if cands and not any(c.lower() in usadas for c in cands):
            u = cands[0]
            if u.lower() not in [x.lower() for x in anadir]:
                anadir.append(u)
                inf.auto.append('%s: uses %s añadida (declara %s)' % (nombre, u, ident))
        for pref, u in RTL_IDENT.items():
            if (ident == pref or (pref.endswith('_') and ident.startswith(pref))) and u.lower() not in usadas and \
                    u not in anadir:
                anadir.append(u)
    if not anadir:
        return src
    m = re.search(r'(\bimplementation\b(?:\s|\{[^}]*\})*)(uses\b((?:[^;{]|\{[^}]*\})*);)?', src, re.I | re.S)
    if m and m.group(2):
        return src[:m.end(3)] + ', ' + ', '.join(anadir) + src[m.end(3):]
    return src[:m.end(1)] + 'uses ' + ', '.join(anadir) + ';\r\n\r\n' + src[m.end(1):]



def transaccion_escritura(src, inf, nombre):
    """FreeIB AutoTrans: las consultas creadas en código que escriben (ExecSQL) confirmaban solas.
    En FireDAC la conexión usa por defecto TLocal (solo lectura): se les asigna DMMain.TUpdate (confirma sola)."""
    lineas = src.split('\n')
    k = 0
    i = 0
    while i < len(lineas):
        m = re.match(r'^(\s*)((?:\w+\.)?)Connection\s*:=\s*DMMain\.(?:DataBase|DB)\s*;', lineas[i])
        if m:
            bloque = []
            for l in lineas[i + 1:i + 60]:
                bloque.append(l)
                if re.search(r'\bFree\s*;|\bFreeAndNil\b|^\s*end\s*;\s*$', l):
                    break
            texto = _limpia_comentarios('\n'.join(bloque))
            if re.search(r'\bExecSQL\b', texto) and not re.search(r'\bTransaction\s*:=', texto) and \
                    not re.search(r'\bTransaction\s*:=', lineas[i - 1] if i else ''):
                lineas.insert(i + 1, '%s%sTransaction := DMMain.TUpdate;  // FreeIB AutoTrans: escribe y confirma sola'
                              % (m.group(1), m.group(2)))
                k += 1
        i += 1
    if k:
        inf.cuenta('consultas de escritura con TUpdate (AutoTrans)', k)
    return '\n'.join(lineas)
