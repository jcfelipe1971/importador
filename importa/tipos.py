# -*- coding: utf-8 -*-
"""Diccionario de tipos de campo aprendido de los DFM de MaxFactu (FireDAC real)."""
import re, glob, os, collections, json
import dfmparser as dp

FROM = re.compile(r'\bFROM\s+([A-Z0-9_$]+)', re.I)


def tabla_de(sql_lines):
    m = FROM.search(' '.join(sql_lines))
    return m.group(1).upper() if m else ''


def aprende(dir_maxfactu):
    por_tabla = {}
    por_campo = collections.defaultdict(collections.Counter)
    tamanos = {}
    for f in glob.glob(os.path.join(dir_maxfactu, '*.dfm')):
        root = dp.parse(open(f, encoding='latin-1').read())
        if not root:
            continue
        for n in root.walk():
            if n.cls not in ('TFDQuery', 'TFDMemTable', 'TFDStoredProc'):
                continue
            tabla = tabla_de(n.strings('SQL.Strings'))
            for c in n.children:
                if not c.cls.endswith('Field'):
                    continue
                fn = (c.getv('FieldName') or "''").strip("'").upper()
                if not fn:
                    continue
                if tabla:
                    por_tabla[(tabla, fn)] = c.cls
                por_campo[fn][c.cls] += 1
    return por_tabla, por_campo


# Reglas por defecto cuando MaxFactu no conoce el campo (BD en dialecto 1, WIN1252)
DEFECTO = {
    'TFIBStringField': 'TStringField',
    'TStringField': 'TStringField',
    'TIntegerField': 'TIntegerField',
    'TSmallintField': 'TSmallintField',
    'TFloatField': 'TFloatField',
    'TDateTimeField': 'TSQLTimeStampField',
    'TDateField': 'TSQLTimeStampField',
    'TBCDField': 'TBCDField',
    'TLargeintField': 'TLargeintField',
    'TBlobField': 'TBlobField',
    'TMemoField': 'TMemoField',
}

CLAVES_SMALLINT = {'EMPRESA', 'EJERCICIO', 'CANAL'}


class Tipos:
    def __init__(self, dir_maxfactu):
        self.por_tabla, self.por_campo = aprende(dir_maxfactu)
        self.stats = collections.Counter()

    def resuelve(self, tabla, campo, cls_merge, blobtype=None):
        campo = campo.upper()
        if (tabla, campo) in self.por_tabla:
            self.stats['tabla+campo (MaxFactu)'] += 1
            return self.por_tabla[(tabla, campo)], 'MaxFactu'
        cands = self.por_campo.get(campo)
        if cands and len(cands) == 1:
            self.stats['campo (MaxFactu)'] += 1
            return next(iter(cands)), 'MaxFactu'
        if campo in CLAVES_SMALLINT and cls_merge == 'TIntegerField':
            self.stats['regla'] += 1
            return 'TSmallintField', 'regla'
        if cls_merge == 'TBlobField' and blobtype and 'ftMemo' in blobtype:
            self.stats['regla'] += 1
            return 'TMemoField', 'regla'
        if cands:
            # ambiguo: tomar el más frecuente pero marcar para revisar
            self.stats['ambiguo'] += 1
            return cands.most_common(1)[0][0], 'ambiguo'
        self.stats['por defecto'] += 1
        return DEFECTO.get(cls_merge, cls_merge), 'defecto'
