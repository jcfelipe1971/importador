# -*- coding: utf-8 -*-
"""Tipos reales de las columnas de cada consulta, leídos de la base de datos Firebird (o de la caché).
La clase de campo FireDAC para cada tipo de Firebird se aprende de los DFM de MaxFactu (lo que genera FireDAC
de verdad con vuestra conexión: dialecto 1, WIN1252)."""
import re, os, json, hashlib, collections

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache_tipos_bd.json')
# Reglas FireDAC por defecto (si MaxFactu no tiene ejemplos de ese tipo)
DEFECTO = {('500', False): 'TSmallintField', ('496', False): 'TIntegerField', ('580', False): 'TLargeintField',
           ('480', False): 'TFloatField', ('482', False): 'TSingleField', ('510', False): 'TSQLTimeStampField',
           ('570', False): 'TDateField', ('560', False): 'TTimeField', ('448', False): 'TStringField',
           ('452', False): 'TStringField', ('520', False): 'TBlobField', ('520m', False): 'TMemoField',
           ('500', True): 'TBCDField', ('496', True): 'TBCDField', ('580', True): 'TFMTBCDField',
           ('32752', False): 'TFMTBCDField', ('32764', False): 'TBooleanField'}


def _sql_preparable(sql):
    """:PARAM -> ? (fuera de literales) para poder preparar la sentencia."""
    partes = re.split(r"('(?:[^']|'')*')", sql)
    return ''.join(p if p.startswith("'") else re.sub(r'(?<![\w:]):\w+', '?', p) for p in partes)


def clave(meta):
    tipo, sub, escala = str(meta[0]), meta[1], meta[2]
    if tipo == '520' and sub == 1:
        tipo = '520m'
    return (tipo, escala < 0)


class TiposBD:
    def __init__(self, cadena=None, usuario='SYSDBA', clave_bd='masterkey', libreria=None):
        self.cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
        self.con = None
        self.errores = []
        if cadena:
            from firebird.driver import connect, driver_config
            if libreria:
                driver_config.fb_client_library.value = libreria
            self.con = connect(cadena, user=usuario, password=clave_bd, charset='WIN1252')
        self.mapa = collections.defaultdict(collections.Counter)

    def describe(self, sql):
        """{ALIAS: (tipo, subtipo, escala, longitud)} de las columnas de salida de la consulta."""
        sql = sql.strip()
        if not sql:
            return {}
        k = hashlib.md5(sql.encode('utf-8')).hexdigest()
        if k in self.cache:
            return {a: tuple(v) for a, v in self.cache[k].items()}
        if self.con is None:
            return {}
        cur = self.con.cursor()
        try:
            st = cur.prepare(_sql_preparable(sql))
            res = {m.alias.upper(): (int(m.datatype), m.subtype, m.scale, m.length) for m in st._out_desc}
            st.free()
        except Exception as e:
            self.errores.append('%s -> %s' % (sql[:80], str(e).split('\n')[0]))
            res = {}
        finally:
            cur.close()
        self.cache[k] = res
        return res

    def parametros(self, sql):
        """[(NOMBRE, tipo_ft)] de los parámetros de entrada de la consulta, en orden de aparición."""
        sql = sql.strip()
        nombres = []
        partes = re.split(r"('(?:[^']|'')*')", sql)
        for p in partes:
            if not p.startswith("'"):
                for n in re.findall(r'(?<![\w:]):(\w+)', p):
                    nombres.append(n.upper())
        if not nombres:
            return []
        k = 'in:' + hashlib.md5(sql.encode('utf-8')).hexdigest()
        tipos = self.cache.get(k)
        if tipos is None and self.con is not None:
            cur = self.con.cursor()
            try:
                st = cur.prepare(_sql_preparable(sql))
                tipos = [[int(m.datatype), m.scale] for m in st._in_desc] if st._in_desc else []
                st.free()
            except Exception:
                tipos = []
            finally:
                cur.close()
            self.cache[k] = tipos
        tipos = tipos or []
        ft = {500: 'ftSmallint', 496: 'ftInteger', 580: 'ftLargeint', 480: 'ftFloat', 482: 'ftFloat',
              448: 'ftString', 452: 'ftFixedChar', 510: 'ftTimeStamp', 570: 'ftDate', 560: 'ftTime',
              520: 'ftBlob', 32764: 'ftBoolean'}
        vistos, out = set(), []
        for i, n in enumerate(nombres):
            t = None
            if i < len(tipos):
                cod, esc = tipos[i]
                t = 'ftCurrency' if cod in (500, 496, 580) and esc < 0 else ft.get(cod)
            if n not in vistos:
                vistos.add(n)
                out.append((n, t))
        return out

    def guarda(self):
        json.dump(self.cache, open(CACHE, 'w', encoding='utf-8'))

    def cierra(self):
        self.guarda()
        if self.con is not None:
            self.con.close()

    def aprende_de_maxfactu(self, dir_mf):
        """Qué clase de campo usa MaxFactu (FireDAC) para cada tipo de Firebird."""
        import glob
        import dfmparser as dp
        for f in glob.glob(os.path.join(dir_mf, '*.dfm')):
            r = dp.parse(open(f, encoding='latin-1').read())
            if not r:
                continue
            for n in r.walk():
                if n.cls != 'TFDQuery':
                    continue
                d = self.describe('\n'.join(n.strings('SQL.Strings')))
                for c in n.children:
                    fn = (c.getv('FieldName') or "''").strip("'").upper()
                    if c.cls.endswith('Field') and fn in d and (c.getv('FieldKind') or '') == '':
                        self.mapa[clave(d[fn])][c.cls] += 1

    def clase(self, meta):
        k = clave(meta)
        if self.mapa.get(k):
            return self.mapa[k].most_common(1)[0][0]
        return DEFECTO.get(k)
