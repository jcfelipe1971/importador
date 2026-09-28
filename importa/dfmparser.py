# -*- coding: utf-8 -*-
"""Parser/serializador mínimo de DFM en formato texto (Delphi)."""
import re

HDR = re.compile(r'^(\s*)(object|inherited|inline)\s+(\w+)\s*:\s*(\w+)(\s*\[\d+\])?\s*$')
END = re.compile(r'^\s*end\s*$')
PROP = re.compile(r'^(\s*)([\w\.]+)\s*=\s?(.*)$')


def _balance(text):
    """Devuelve el saldo de ( < { fuera de literales."""
    b = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "'":
            i += 1
            while i < n:
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        i += 2
                        continue
                    break
                i += 1
        elif c in '(<{':
            b += 1
        elif c in ')>}':
            b -= 1
        i += 1
    return b


class Node:
    def __init__(self, kind, name, cls, order=''):
        self.kind, self.name, self.cls, self.order = kind, name, cls, order
        self.props = []      # lista de [nombre, [lineas_valor]]
        self.children = []
        self.parent = None

    # utilidades
    def get(self, pname):
        for p in self.props:
            if p[0] == pname:
                return p[1]
        return None

    def getv(self, pname):
        v = self.get(pname)
        return None if v is None else '\n'.join(v).strip()

    def set(self, pname, lines):
        if isinstance(lines, str):
            lines = [lines]
        for p in self.props:
            if p[0] == pname:
                p[1] = lines
                return
        self.props.append([pname, lines])

    def delete(self, pname):
        self.props = [p for p in self.props if p[0] != pname]

    def strings(self, pname):
        """Lee una propiedad TStrings -> lista de str."""
        v = self.get(pname)
        if v is None:
            return []
        txt = '\n'.join(v)
        out, cur = [], None
        for m in re.finditer(r"('(?:[^']|'')*')|(#\d+)|(\+)|(\n)", txt):
            if m.group(1) or m.group(2):
                s = m.group(1)[1:-1].replace("''", "'") if m.group(1) else chr(int(m.group(2)[1:]))
                cur = (cur or '') + s
            elif m.group(4):
                # salto de línea: si la línea anterior no terminaba en '+', cerramos item
                pass
        # reconstrucción más fiable línea a línea
        out = []
        acc = None
        for line in v:
            l = line.strip()
            if l in ('(', ')', ''):
                continue
            if l.startswith('('):
                l = l[1:].strip()
            cont = l.endswith('+')
            if cont:
                l = l[:-1].strip()
            if l.endswith(')') and not cont:
                l = l[:-1].strip()
            s = ''.join(
                (m.group(1)[1:-1].replace("''", "'") if m.group(1) else chr(int(m.group(2)[1:])))
                for m in re.finditer(r"('(?:[^']|'')*')|(#\d+)", l))
            acc = (acc or '') + s
            if not cont:
                out.append(acc)
                acc = None
        if acc is not None:
            out.append(acc)
        return out

    def set_strings(self, pname, items):
        self.set(pname, strings_to_dfm(items))

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, name):
        for n in self.walk():
            if n.name == name:
                return n
        return None


def quote(s):
    out = []
    buf = ''
    for ch in s:
        if ord(ch) > 127 or ord(ch) < 32:
            if buf:
                out.append("'" + buf.replace("'", "''") + "'")
                buf = ''
            out.append('#%d' % ord(ch))
        else:
            buf += ch
    if buf or not out:
        out.append("'" + buf.replace("'", "''") + "'")
    return ''.join(out)


def _trozos(s, n=64):
    return [s[i:i + n] for i in range(0, len(s), n)] or ['']


def strings_to_dfm(items):
    """Igual que el IDE: los elementos largos se parten en trozos de 64 caracteres unidos con +."""
    if not items:
        return ['(', "  '')"]
    lines = ['(']
    for i, it in enumerate(items):
        cierre = ')' if i == len(items) - 1 else ''
        if len(it) <= 64:
            lines.append('  ' + quote(it) + cierre)
        else:
            lines.append('  ')
            tr = _trozos(it)
            for j, t in enumerate(tr):
                lines.append('    ' + quote(t) + (' +' if j < len(tr) - 1 else cierre))
    return lines


def parse(text):
    text = text.lstrip('\ufeff').lstrip('\xef\xbb\xbf')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    root = None
    stack = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = HDR.match(line)
        if m:
            node = Node(m.group(2), m.group(3), m.group(4), (m.group(5) or '').strip())
            if stack:
                node.parent = stack[-1]
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
            i += 1
            continue
        if END.match(line) and stack:
            stack.pop()
            i += 1
            continue
        m = PROP.match(line)
        if m and stack:
            base = len(m.group(1))
            vals = [m.group(3)]
            bal = _balance(m.group(3))
            cont = m.group(3).rstrip().endswith('+') or m.group(3).strip() == ''
            i += 1
            while (bal > 0 or cont) and i < len(lines):
                l = lines[i]
                vals.append(l[base:] if l[:base].strip() == '' else l.strip())
                bal += _balance(l)
                cont = l.rstrip().endswith('+') and bal == 0
                i += 1
            stack[-1].props.append([m.group(2), vals])
            continue
        i += 1
    return root


def dump(node, level=0):
    ind = '  ' * level
    out = ['%s%s %s: %s%s' % (ind, node.kind, node.name, node.cls, (' ' + node.order) if node.order else '')]
    for pname, vals in node.props:
        out.append('%s  %s = %s' % (ind, pname, vals[0]))
        for v in vals[1:]:
            out.append(ind + '  ' + v)
    for c in node.children:
        out.extend(dump(c, level + 1))
    out.append(ind + 'end')
    return out


def dumps(node):
    return '\r\n'.join(dump(node)) + '\r\n'
