# -*- coding: utf-8 -*-
"""Reescritura de llamadas Pascal con sus argumentos (aunque ocupen varias líneas)."""
import re


def _argumentos(src, i):
    """src[i] == '(' -> (lista de argumentos, índice tras el ')')"""
    nivel, j, ini, args = 0, i, i + 1, []
    while j < len(src):
        c = src[j]
        if c == "'":
            j += 1
            while j < len(src) and not (src[j] == "'" and (j + 1 >= len(src) or src[j + 1] != "'")):
                j += 2 if src[j] == "'" else 1
        elif c == '(':
            nivel += 1
        elif c == ')':
            nivel -= 1
            if nivel == 0:
                args.append(src[ini:j])
                return [a.strip() for a in args], j + 1
        elif c == ',' and nivel == 1:
            args.append(src[ini:j])
            ini = j + 1
        j += 1
    return None, i


def reescribe(src, patron, fn):
    """Busca patron (regex que termina justo antes del '(') y sustituye la llamada completa por fn(args).
    fn devuelve el texto nuevo o None para dejarla igual. Respeta comentarios y literales."""
    out, pos = [], 0
    mascara = re.sub(r"\{[^}]*\}|\(\*.*?\*\)|//[^\n]*|'(?:[^']|'')*'", lambda m: ' ' * len(m.group(0)), src,
                     flags=re.S)
    for m in re.finditer(patron + r'\s*(?=\()', mascara, re.I):
        if m.start() < pos:
            continue
        args, fin = _argumentos(src, m.end())
        if args is None:
            continue
        nuevo = fn(args, m)
        if nuevo is None:
            continue
        out.append(src[pos:m.start()])
        out.append(nuevo)
        pos = fin
    out.append(src[pos:])
    return ''.join(out)
