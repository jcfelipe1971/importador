# -*- coding: utf-8 -*-
"""Conversión de DFM Merge (Delphi 6 / FreeIB / LF / HY) -> patrón MaxFactu (Delphi 13 / FireDAC / VCL)."""
import re
import dfmparser as dp
import vcl_props as vp
from tipos import tabla_de

DATASETS_RW = {'TFIBTableSet', 'TFIBDataSet'}
DATASETS_RO = {'TFIBDataSetRO', 'TFIBTableSetRO', 'TFIBDataSetRW', 'TFIBInfoSet'}
QUERIES = {'THYFIBQuery', 'TFIBQuery'}
TRANS = {'THYTransaction', 'TFIBTransaction'}


def params_fib_a_fd(line):
    """?old_CAMPO -> :OLD_CAMPO ; ?CAMPO -> :CAMPO (solo dentro de SQL)."""
    line = re.sub(r'\?old_(\w+)', lambda m: ':OLD_' + m.group(1), line, flags=re.I)
    return re.sub(r'(?<![\w?])\?(?=[A-Za-z_])', ':', line)


class Informe:
    def __init__(self):
        self.auto = []      # conversiones automáticas
        self.revisar = []   # pendientes manuales
        self.quitados = []  # componentes/propiedades eliminados
        self.bloqueantes = []  # impiden cargar el DFM en Delphi 13
        self.contadores = {}

    def cuenta(self, k, n=1):
        self.contadores[k] = self.contadores.get(k, 0) + n


# ----------------------------------------------------------------------------------------------
#  MÓDULO DE DATOS
# ----------------------------------------------------------------------------------------------

def _sql(node, prop):
    return [params_fib_a_fd(l) for l in node.strings(prop)]


EVENTOS_FDQUERY = {'BeforeOpen', 'AfterOpen', 'BeforeClose', 'AfterClose', 'BeforeInsert', 'AfterInsert',
                   'BeforeEdit', 'AfterEdit', 'BeforePost', 'AfterPost', 'BeforeCancel', 'AfterCancel',
                   'BeforeDelete', 'AfterDelete', 'BeforeScroll', 'AfterScroll', 'BeforeRefresh', 'AfterRefresh',
                   'OnCalcFields', 'OnDeleteError', 'OnEditError', 'OnNewRecord', 'OnPostError', 'OnFilterRecord',
                   'OnUpdateRecord', 'OnUpdateError', 'OnReconcileError', 'BeforeApplyUpdates',
                   'AfterApplyUpdates', 'BeforeExecute', 'AfterExecute', 'BeforeGetRecord', 'AfterGetRecord',
                   'OnError', 'OnMasterSetValues'}


def conexion_principal():
    import conv_pas
    return 'DMMain.DataBase' if conv_pas.PERFIL == 'merge13' else 'DMMain.DB'


def convierte_transaccion(n, inf):
    params = ' '.join(s.strip().lower() for s in n.strings('TRParams.Strings'))
    new = dp.Node(n.kind, n.name, 'TFDTransaction', n.order)
    new.set('Options.Isolation', 'xiReadCommitted' if 'read_commit' in params else 'xiSnapshot')
    if re.search(r'\bread\b', params):
        new.set('Options.ReadOnly', 'True')
    if 'nowait' in params:
        inf.revisar.append('%s: TRParams incluye "nowait". FireDAC espera por defecto; '
                           'si se necesita, añadir Options.Params (nowait) o LockWait.' % n.name)
    db = n.getv('DefaultDatabase') or ''
    new.set('Connection', conexion_principal() if 'DMMain' in db or not db else db.replace('DataBase', 'DB'))
    for p in ('Left', 'Top'):
        if n.get(p):
            new.set(p, n.get(p))
    inf.cuenta('THYTransaction -> TFDTransaction')
    return new


def pon_paramdata(q, sql, tipos, inf):
    """FireDAC no crea los parámetros al cargar el DFM: hay que guardarlos (ParamData), como hace el IDE."""
    bd = getattr(tipos, 'bd', None)
    texto = '\n'.join(sql or [])
    if bd is not None:
        params = bd.parametros(texto)
    else:
        params, vistos = [], set()
        for n in re.findall(r"(?<![\w:]):(\w+)", re.sub(r"'(?:[^']|'')*'", "''", texto)):
            if n.upper() not in vistos:
                vistos.add(n.upper()); params.append((n.upper(), None))
    if not params:
        return
    lineas = ['<']
    for i, (nombre, ft) in enumerate(params):
        lineas += ['  item', "    Name = '%s'" % nombre]
        if ft:
            lineas.append('    DataType = %s' % ft)
        lineas += ['    ParamType = ptInput', '  end' + ('>' if i == len(params) - 1 else '')]
    q.set('ParamData', lineas)
    inf.cuenta('consultas con ParamData (parámetros guardados en el DFM)')


def convierte_campos(n, new, tabla, tipos, inf, sql=None):
    bd = getattr(tipos, 'bd', None)
    meta = bd.describe('\n'.join(sql)) if (bd is not None and sql) else {}
    for c in n.children:
        if not c.cls.endswith('Field'):
            new.children.append(c)
            continue
        fn = (c.getv('FieldName') or "''").strip("'")
        calc = (c.getv('FieldKind') or '') in ('fkCalculated', 'fkLookup') or \
            (c.getv('Calculated') or '').lower() == 'true'
        if fn.upper() in meta and not calc and bd.clase(meta[fn.upper()]):
            cls, origen = bd.clase(meta[fn.upper()]), 'BD'
            tipos.stats['tipo real de la base de datos'] += 1
        elif meta and not calc and fn.upper() not in meta:
            cls, origen = tipos.resuelve(tabla, fn, c.cls, c.getv('BlobType'))
            inf.revisar.append('Campo %s: %s no es una columna de la consulta de %s (¿campo sobrante en Merge?).'
                               % (c.name, fn, n.name))
        else:
            cls, origen = tipos.resuelve(tabla, fn, c.cls, c.getv('BlobType'))
        f = dp.Node(c.kind, c.name, cls, c.order)
        for pname, vals in c.props:
            if pname == 'BlobType' and cls in ('TMemoField',):
                f.props.append([pname, vals])
            elif pname == 'Size' and cls not in ('TStringField', 'TWideStringField', 'TMemoField', 'TBlobField',
                                                  'TFixedCharField'):
                continue
            elif pname in ('DisplayLabel', 'FieldName', 'Size', 'OnChange', 'OnValidate', 'OnGetText',
                           'OnSetText', 'DisplayFormat', 'EditMask', 'Visible', 'DisplayWidth', 'Required',
                           'ReadOnly', 'Alignment', 'EditFormat', 'Calculated', 'FieldKind', 'Lookup',
                           'LookupDataSet', 'LookupKeyFields', 'LookupResultField', 'KeyFields', 'BlobType',
                           'currency', 'Currency', 'DefaultExpression', 'Index', 'Precision'):
                f.props.append([pname, vals])
            else:
                inf.quitados.append('%s.%s (propiedad de campo)' % (c.name, pname))
        if origen == 'BD' and cls == 'TStringField' and meta[fn.upper()][3]:
            f.set('Size', str(meta[fn.upper()][3]))
        if c.getv('FieldKind') not in ('fkCalculated', 'fkLookup') and not f.get('Origin'):
            f.set('Origin', dp.quote(fn))
        # orden: Origin detrás de FieldName (como el IDE)
        new.children.append(f)
        inf.cuenta('campos persistentes')
        inf.cuenta('tipo de campo: ' + origen)
        if origen in ('ambiguo', 'defecto') and cls != c.cls.replace('TFIB', 'T'):
            inf.revisar.append('Campo %s (%s.%s): tipo %s -> %s asignado por %s; verificar con verifica_tipos.sql'
                               % (c.name, tabla, fn, c.cls, cls, origen))


def convierte_dataset(n, root, tipos, inf, updates):
    tabla = tabla_de(n.strings('SelectSQL.Strings')) or (n.getv('TableName') or "''").strip("'").strip()
    q = dp.Node(n.kind, n.name, 'TFDQuery', n.order)
    # eventos estándar TDataSet
    for pname, vals in n.props:
        if pname in EVENTOS_FDQUERY:
            q.props.append([pname, vals])
        elif pname.startswith(('After', 'Before', 'On')):
            inf.revisar.append('%s.%s = %s: evento propio de %s que TFDQuery no tiene; el método queda sin '
                               'enganchar.' % (n.name, pname, '\n'.join(vals).strip(), n.cls))
    if n.get('Database'):
        db = n.getv('Database')
        q.set('Connection', conexion_principal() if 'DMMain' in db else db)
    if n.get('Transaction'):
        q.set('Transaction', n.get('Transaction'))
    if n.get('UpdateTransaction'):
        q.set('UpdateTransaction', n.get('UpdateTransaction'))
    if n.get('DataSource'):
        q.set('MasterSource', n.get('DataSource'))
        inf.auto.append('%s: DataSource (maestro FIB) -> MasterSource (parámetros por nombre).' % n.name)
    sel = _sql(n, 'SelectSQL.Strings')
    if sel:
        q.set_strings('SQL.Strings', sel)
        pon_paramdata(q, sel, tipos, inf)
    if (n.getv('CachedUpdates') or '').lower() == 'true':
        q.set('CachedUpdates', 'True')
    if (n.getv('UniDirectional') or '').lower() == 'true':
        q.set('FetchOptions.Unidirectional', 'True')

    rw = n.cls in DATASETS_RW
    if rw:
        ins, upd, dele, ref = (_sql(n, p) for p in ('InsertSQL.Strings', 'UpdateSQL.Strings',
                                                     'DeleteSQL.Strings', 'RefreshSQL.Strings'))
        if ins or upd or dele:
            un = dp.Node('object', 'FDU' + n.name, 'TFDUpdateSQL')
            un.set('Connection', conexion_principal())
            if ins: un.set_strings('InsertSQL.Strings', ins)
            if upd: un.set_strings('ModifySQL.Strings', upd)
            if dele: un.set_strings('DeleteSQL.Strings', dele)
            if ref: un.set_strings('FetchRowSQL.Strings', ref)
            left = int((n.getv('Left') or '0')) + 90
            un.set('Left', str(left)); un.set('Top', n.getv('Top') or '0')
            updates.append(un)
            q.set('UpdateObject', un.name)
            inf.cuenta('TFDUpdateSQL generados')
        else:
            q.set('UpdateOptions.ReadOnly', 'True') if n.cls == 'TFIBDataSet' and not ins else None
        claves = [s.strip() for s in n.strings('ClavesPrimarias.Strings') if s.strip()]
        if claves:
            q.set('UpdateOptions.KeyFields', dp.quote(';'.join(claves)))
        tn = (n.getv('TableName') or "''").strip("'").strip()
        if tn:
            q.set('UpdateOptions.UpdateTableName', dp.quote(tn))
        acc = n.getv('AccionesInhibidas') or ''
        if 'Borrar' in acc: q.set('UpdateOptions.EnableDelete', 'False')
        if 'Insertar' in acc: q.set('UpdateOptions.EnableInsert', 'False')
        if 'Modificar' in acc: q.set('UpdateOptions.EnableUpdate', 'False')
        if (n.getv('BloqOpt') or '').lower() == 'true':
            tablas = [s.strip() for s in n.strings('TablasBloqueo.Strings') if s.strip()]
            campos = [s.strip() for s in n.strings('CamposBloqueo.Strings')]
            inf.revisar.append('%s: BloqOpt=True -> registrar en TControlConcurrencia (UControlConcurrencia.pas) '
                               'tablas %s' % (n.name, tablas))
            n._bloqueo = [(t, cc, 'cmSelectWithLock') for t, cc in zip(tablas, campos)]
        elif claves and 'NoControlarConcurrencia' not in (n.getv('Opciones') or '') and tn:
            n._bloqueo = [(tn, ','.join(claves), 'cmUpdate')]
            inf.auto.append('%s: control de concurrencia por UPDATE ficticio -> TControlConcurrencia.' % n.name)
        if (n.getv('AutoCommit') or 'False').lower() != 'true' and n.get('UpdateTransaction'):
            inf.revisar.append('%s: AutoCommit=False en Merge; en FireDAC la UpdateTransaction confirma sola. '
                               'Revisar si el código hace Commit manual.' % n.name)
    else:
        q.set('UpdateOptions.ReadOnly', 'True')
    q.set('Left', n.getv('Left') or '0'); q.set('Top', n.getv('Top') or '0')
    convierte_campos(n, q, tabla, tipos, inf, sel)
    ignorados = {'BufferChunks', 'UsaNulls', 'UpdateRecordTypes', 'Plan.Strings', 'AutoTrans', 'Opciones',
                 'AutoSQLdeVistas', 'ComprobarTabla', 'Mensajes', 'AutoCommit', 'AutoCalcFields',
                 'Documentacion.Strings', 'CamposNoComparables.Strings', 'Regenerar', 'Active'}
    for pname, _ in n.props:
        if pname in ignorados:
            continue
    inf.cuenta('%s -> TFDQuery' % n.cls)
    return q


def convierte_query(n, inf):
    q = dp.Node(n.kind, n.name, 'TFDQuery', n.order)
    q.set('Connection', conexion_principal())
    if n.get('Transaction'):
        q.set('Transaction', n.get('Transaction'))
    s = _sql(n, 'SQL.Strings')
    if s:
        q.set_strings('SQL.Strings', s)
        pon_paramdata(q, s, None, inf)
    q.set('Left', n.getv('Left') or '0'); q.set('Top', n.getv('Top') or '0')
    inf.cuenta('%s -> TFDQuery' % n.cls)
    return q


def convierte_dm(root, tipos, inf):
    new = dp.Node(root.kind, root.name, root.cls)
    for pname, vals in root.props:
        if pname in ('OnCreate', 'OnDestroy', 'Height', 'Width'):
            new.props.append([pname, vals])
    updates = []
    bloqueos = {}
    for c in root.children:
        if c.cls in TRANS:
            new.children.append(convierte_transaccion(c, inf))
        elif c.cls in DATASETS_RW or c.cls in DATASETS_RO:
            new.children.append(convierte_dataset(c, root, tipos, inf, updates))
            if getattr(c, '_bloqueo', None):
                bloqueos[c.name] = c._bloqueo
        elif c.cls in QUERIES:
            new.children.append(convierte_query(c, inf))
        elif c.cls == 'TDataSource':
            new.children.append(c)
        elif c.cls.startswith(('Tfr', 'THYReport')):
            inf.quitados.append('%s: %s (FastReport 2) -> usar TfrxDBDataset/TfrxReport' % (c.name, c.cls))
            inf.revisar.append('%s (%s): informe FR2, migrar a FastReport actual.' % (c.name, c.cls))
        elif c.cls in ESTANDAR_D13 or c.cls in VCL_OK:
            new.children.append(c)
        else:
            new.children.append(c)
            inf.bloqueantes.append('%s: clase %s no existe en Delphi 13 y no tiene regla de conversión '
                                   '(componente propio a portar o sustituir).' % (c.name, c.cls))
    new.children.extend(updates)
    return new, bloqueos


# ----------------------------------------------------------------------------------------------
#  FORMULARIO -> FRAME
# ----------------------------------------------------------------------------------------------

COMUNES = {'Left', 'Top', 'Width', 'Height', 'Align', 'Anchors', 'Visible', 'Enabled', 'Hint', 'ShowHint',
           'ParentShowHint', 'TabOrder', 'TabStop', 'Tag', 'Color', 'ParentColor', 'Font.Charset', 'Font.Color',
           'Font.Height', 'Font.Name', 'Font.Style', 'ParentFont', 'PopupMenu', 'Constraints.MinHeight',
           'Constraints.MinWidth', 'Constraints.MaxHeight', 'Constraints.MaxWidth', 'Cursor', 'HelpContext',
           'BiDiMode', 'ParentBiDiMode', 'DoubleBuffered', 'Margins.Left', 'Margins.Top', 'Margins.Right',
           'Margins.Bottom', 'AlignWithMargins', 'DesignSize'}
EVENTOS = re.compile(r'^On[A-Z]')

MAPA = {
    'TLFLabel': ('TLabel', {'Caption', 'Alignment', 'AutoSize', 'FocusControl', 'Layout', 'WordWrap', 'Transparent'}),
    'TLFEdit': ('TEdit', {'Text', 'ReadOnly', 'AutoSize', 'CharCase', 'MaxLength', 'PasswordChar', 'Alignment'}),
    'TLFDbedit': ('TDBEdit', {'DataField', 'DataSource', 'ReadOnly', 'CharCase', 'MaxLength', 'AutoSize'}),
    'TLFDBMemo': ('TDBMemo', {'DataField', 'DataSource', 'ReadOnly', 'ScrollBars', 'BevelInner', 'WordWrap'}),
    'TLFMemo': ('TMemo', {'Lines.Strings', 'ReadOnly', 'ScrollBars', 'WordWrap'}),
    'TLFDBCheckBox': ('TDBCheckBox', {'DataField', 'DataSource', 'Caption', 'ValueChecked', 'ValueUnchecked',
                                      'Alignment', 'ReadOnly'}),
    'TLFCheckBox': ('TCheckBox', {'Caption', 'Checked', 'Alignment', 'State'}),
    'TFlatCheckBox': ('TCheckBox', {'Caption', 'Checked', 'Alignment'}),
    'TLFComboBox': ('TComboBox', {'Items.Strings', 'ItemIndex', 'Style', 'Text', 'ItemHeight', 'Sorted'}),
    'TLFPanel': ('TPanel', {'Caption', 'BevelOuter', 'BevelInner', 'BorderStyle', 'BevelWidth'}),
    'TFlatPanel': ('TPanel', {'Caption'}),
    'TLFPageControl': ('TPageControl', {'ActivePage', 'TabIndex', 'TabPosition', 'OwnerDraw', 'MultiLine',
                                        'Images', 'Style', 'TabHeight', 'TabWidth'}),
    'TTabSheet': ('TTabSheet', {'Caption', 'ImageIndex', 'TabVisible', 'PageIndex'}),
    'TLFToolBar': ('TToolBar', {'AutoSize', 'ButtonWidth', 'ButtonHeight', 'Caption', 'DisabledImages',
                                'EdgeBorders', 'EdgeInner', 'EdgeOuter', 'Flat', 'HotImages', 'Images', 'List',
                                'ShowCaptions', 'Wrapable'}),
    'TLFDBCtrlGrid': ('TDBCtrlGrid', {'DataSource', 'AllowDelete', 'AllowInsert', 'ColCount', 'RowCount',
                                      'PanelHeight', 'PanelWidth', 'SelectedColor', 'Orientation'}),
    'TLFDBDateEdit': ('TDBEdit', {'DataField', 'DataSource', 'ReadOnly'}),
    'TLFDateEdit': ('TDateTimePicker', {'Date', 'Time', 'Kind', 'ShowCheckbox', 'Checked'}),
    'THYGRightEdit': ('TEdit', {'Text', 'ReadOnly'}),
    'TDBComboBoxValue': ('TDBComboBox', {'DataField', 'DataSource', 'Items.Strings', 'Style', 'ItemHeight'}),
    'TLFDBEditFind2000': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly'}),
    'TDBEditFind2000': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly'}),
    'TLFEditFind2000': ('TEdit', {'Text', 'CharCase'}),
    'THYTDBGrid': ('TDBGrid', {'DataSource', 'Columns', 'Options', 'ReadOnly', 'TitleFont.Charset',
                               'TitleFont.Color', 'TitleFont.Height', 'TitleFont.Name', 'TitleFont.Style'}),
    'TDBGridFind2000': ('TDBGrid', {'DataSource', 'Columns', 'Options', 'ReadOnly', 'TitleFont.Charset',
                                    'TitleFont.Color', 'TitleFont.Height', 'TitleFont.Name', 'TitleFont.Style'}),
    'TLFActionList': ('TActionList', {'Images', 'State'}),
    'TLFCategoryAction': ('TAction', {'Caption', 'Category', 'ImageIndex', 'Hint', 'Visible', 'Enabled'}),
    'TLFDatasetAction': ('TAction', {'Caption', 'Category', 'ImageIndex', 'Hint', 'ShortCut', 'Visible',
                                     'Enabled'}),
    'THYMNavigator': ('TDBNavigator', {'DataSource', 'Flat', 'Hints.Strings'}),
    # --- variantes de EditFind: TDBEdit/TEdit + TBuscadorCampo ---
    'TLFFibDBEditFind': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly'}),
    'TFIBDBEditfind': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly'}),
    'TEditFind2000': ('TEdit', {'Text', 'CharCase'}),
    'TFIBHYGEditFind': ('TEdit', {'Text', 'CharCase'}),
    # --- ediciones ---
    'THYDBEdit': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly', 'MaxLength'}),
    'TLFDBEdit': ('TDBEdit', {'DataField', 'DataSource', 'CharCase', 'ReadOnly', 'MaxLength'}),
    'TDBDateTimePicker': ('TDBEdit', {'DataField', 'DataSource', 'ReadOnly'}),
    'TDBSpinEdit': ('TDBEdit', {'DataField', 'DataSource', 'ReadOnly'}),
    'TDBDateEdit': ('TDBEdit', {'DataField', 'DataSource', 'ReadOnly'}),
    'TDateEdit': ('TDateTimePicker', {'Date', 'Time', 'Kind', 'ShowCheckbox', 'Checked'}),
    'TCurrencyEdit': ('TEdit', {'Text', 'ReadOnly', 'MaxLength'}),
    'TRightMaskEdit': ('TEdit', {'Text', 'ReadOnly', 'MaxLength'}),
    'TDirectoryEdit': ('TEdit', {'Text', 'ReadOnly'}),
    'TLFHYDBDescription': ('TEdit', {'Text'}),
    'THYDBDescripcion': ('TEdit', {'Text'}),
    # --- combos con Items/Values ---
    'TLFDBComboBoxValue': ('TDBComboBox', {'DataField', 'DataSource', 'Items.Strings', 'Style', 'ItemHeight',
                                           'DropDownCount'}),
    'TRxDBComboBox': ('TDBComboBox', {'DataField', 'DataSource', 'Items.Strings', 'Style', 'ItemHeight',
                                      'DropDownCount'}),
    'TRxDBLookupCombo': ('TDBLookupComboBox', {'DataField', 'DataSource', 'DropDownRows', 'KeyField', 'ListField',
                                               'ListSource'}),
    # --- rejillas, botones, contenedores, acciones ---
    'TNsDBGrid': ('TDBGrid', {'DataSource', 'Columns', 'Options', 'ReadOnly', 'TitleFont.Charset', 'TitleFont.Color',
                              'TitleFont.Height', 'TitleFont.Name', 'TitleFont.Style'}),
    'TFIBHYGGridFind': ('TDBGrid', {'DataSource', 'Columns', 'Options', 'ReadOnly', 'TitleFont.Charset',
                                    'TitleFont.Color', 'TitleFont.Height', 'TitleFont.Name', 'TitleFont.Style'}),
    'TNoScrollLFDBCtrlGrid': ('TDBCtrlGrid', {'DataSource', 'AllowDelete', 'AllowInsert', 'ColCount', 'RowCount',
                                              'PanelHeight', 'PanelWidth', 'PanelBorder', 'SelectedColor',
                                              'Orientation'}),
    'TFlatButton': ('TBitBtn', {'Caption', 'Glyph.Data', 'NumGlyphs', 'Layout', 'Spacing', 'Margin', 'ModalResult',
                                'Default', 'Cancel'}),
    'TFlatGroupBox': ('TGroupBox', {'Caption'}),
    'TLFToolButton': ('TToolButton', {'Action', 'ImageIndex', 'Style', 'Caption'}),
    'TLFNoSaveAction': ('TAction', {'Caption', 'Category', 'ImageIndex', 'Hint', 'ShortCut', 'Visible', 'Enabled'}),
}

# Propiedades que cambian de nombre al cambiar de clase
PROP_RENOMBRA = {
    ('TRxDBLookupCombo', 'LookupField'): 'KeyField', ('TRxDBLookupCombo', 'LookupDisplay'): 'ListField',
    ('TRxDBLookupCombo', 'LookupSource'): 'ListSource', ('TRxDBLookupCombo', 'DropDownCount'): 'DropDownRows',
    ('TRxDBComboBox', 'DropDownCount'): 'DropDownCount',
}

# Clases que existen en Delphi 13 (VCL, TeeChart, FastReport actual, Indy, ADO, dbExpress, Office): se dejan igual
ESTANDAR_D13 = {
    'TDBText', 'TProgressBar', 'TRadioButton', 'TSpinEdit', 'TStringGrid', 'TDBRichEdit', 'TTreeView', 'TImageList',
    'TUpDown', 'TListBox', 'TTabControl', 'TListView', 'TValueListEditor', 'TAnimate', 'TOpenPictureDialog',
    'TStatusBar', 'TTrackBar', 'TRichEdit', 'TMainMenu', 'TLabeledEdit', 'TSaveDialog', 'TOpenDialog',
    'TMonthCalendar', 'TCheckListBox', 'TPrinterSetupDialog', 'TFontDialog', 'TStaticText', 'TMaskEdit',
    'TShellTreeView', 'TWebBrowser', 'TRichEditBold', 'TRichEditItalic', 'TRichEditUnderline', 'TRichEditBullets',
    'TRichEditAlignLeft', 'TRichEditAlignRight', 'TRichEditAlignCenter', 'TDBChart', 'TChart', 'TBarSeries',
    'THorizBarSeries', 'TLineSeries', 'TPieSeries', 'TAreaSeries', 'TADOQuery', 'TADOConnection', 'TADOTable',
    'TClientDataSet', 'TSQLConnection', 'TSQLQuery', 'TSQLDataSet', 'THTTPRIO', 'TExcelApplication',
    'TExcelWorkbook', 'TExcelWorksheet', 'TIdSSLIOHandlerSocketOpenSSL', 'TIdPOP3', 'TIdMessage', 'TIdSMTP',
    'TIdFTP', 'TIdNNTP', 'TIdHTTP', 'TfrxDBDataset', 'TfrxUserDataSet', 'TfrxReport', 'TfrxRTFExport',
    'TfrxRichObject', 'TfrxOLEObject', 'TfrxHTMLExport', 'TfrxCSVExport', 'TfrxCheckBoxObject',
    'TfrxBarCodeObject', 'TfrxChartObject', 'TfrxCrossObject', 'TfrxDialogControls', 'TfrxDotMatrixExport',
    'TfrxPDFExport', 'TfrxXLSExport', 'TfrxXMLExport', 'TAbZipper', 'TAbZipBrowser'}


# Clases VCL estándar que se dejan tal cual
VCL_OK = {'TMenuItem', 'TAction', 'TToolButton', 'TSpeedButton', 'TBitBtn', 'TButton', 'TSplitter', 'TTimer',
          'TPopupMenu', 'TDBLookupComboBox', 'TDataSource', 'TImage', 'TDBImage', 'TGroupBox', 'TScrollBox',
          'TLabel', 'TEdit', 'TDBEdit', 'TPanel', 'TDBNavigator', 'TDBGrid', 'TDBChart', 'TBarSeries',
          'TLineSeries', 'TPieSeries', 'TChart', 'TImageList', 'TMainMenu', 'TShape', 'TBevel', 'TRadioGroup',
          'TDBRadioGroup', 'TCheckBox', 'TComboBox', 'TMemo', 'TDBMemo', 'TOpenDialog', 'TSaveDialog'}
# Componentes del framework G2K sin equivalente visual: se eliminan (su función la da la base MaxFactu)
ELIMINAR = {'TControlEdit': 'navegación/edición por teclado (base TFRMMantenimientoSimple)',
            'TPopUpTeclas': 'atajos de teclado (acciones con ShortCut)',
            'THYMEditPanel': 'botones buscar/rango (EFiltrar + filtros de columna de la base)',
            'TG2KTBLoc': 'localizador (EFiltrar de la base)',
            'TLFFibFormStorage': 'UUtilGuardaConfiguracion (CargaIniFRame/GuardaFrame)',
            'TFormStorage': 'UUtilGuardaConfiguracion'}
# Componentes propios de Merge sin equivalente: se eliminan del DFM (su función la da el framework nuevo)
ELIMINAR.update({
    'TEntornoFind2000': 'filtro de entorno de los EditFind (ya lo aplica TBuscadorCampo con FiltroEntorno)',
    'TTeclas': 'teclas de navegación (base MaxFactu)', 'TLFManager': 'gestor de estilos LF (estilos VCL)',
    'TFormPlacement': 'UUtilGuardaConfiguracion', 'TfrxFIBHYComponents': 'FastReport: usar TfrxFDComponents',
    'TfrDBDataSet': 'FastReport 2', 'TfrHYReport': 'FastReport 2', 'TfrUserDataset': 'FastReport 2',
    'THYReportSource': 'FastReport 2 (HY)', 'THYReportMailSource': 'FastReport 2 (HY)', 'THYReport': 'FastReport 2 (HY)',
    'THYReportMail': 'FastReport 2 (HY)', 'TfrReport': 'FastReport 2', 'TfrChartObject': 'FastReport 2',
})

# nombres heredados Merge (TFPEdit) -> MaxFactu (TFRMMantenimientoSimple)
HEREDADOS = {'PMain': 'PNLMain', 'TBMain': 'TBMain', 'NavMain': 'NavMain', 'PCMain': 'PCMain',
             'TSFicha': 'TSFicha', 'TSTabla': 'TSTabla', 'DBGMain': 'DBGMain', 'PEdit': 'SBFicha',
             'ALMain': 'Acciones'}
HEREDADOS_ELIMINAR = {'EPMain', 'CEMain', 'CEMainPMEdit', 'G2KTableLoc', 'FSMain', 'TSepNav', 'TBActions',
                      'CEDetalle', 'CEDetallePMEdit'}

BASES_MERGE = {}


def carga_bases_merge(dir_merge, nombres=('UFPEditSinNavegador', 'UFPEditSimple', 'UFPEdit', 'UFPEditDetalle')):
    import os
    for nb in nombres:
        ruta = os.path.join(dir_merge, nb + '.dfm')
        if not os.path.exists(ruta):
            continue
        root = dp.parse(open(ruta, encoding='latin-1').read())
        for n in root.walk():
            if n is root:
                continue
            prev = BASES_MERGE.get(n.name)
            if prev is not None and n.kind == 'inherited':
                propias = {p for p, _ in n.props}
                n.props = [list(p) for p in prev.props if p[0] not in propias] + n.props
                n.cls = prev.cls
            BASES_MERGE[n.name] = n


# Evento de Merge -> evento VCL equivalente (misma firma)
EVENTOS_RENOMBRA = {
    ('TLFDBCheckBox', 'OnChange'): 'OnClick', ('TLFCheckBox', 'OnChange'): 'OnClick',
    ('TFlatCheckBox', 'OnChange'): 'OnClick',
    ('THYMNavigator', 'OnClickAfterAdjust'): 'OnClick',
    ('TLFDateEdit', 'OnButtonClick'): 'OnDropDown',
}
EDITFIND = {'TLFDBEditFind2000', 'TDBEditFind2000', 'TLFEditFind2000', 'TLFFibDBEditFind', 'TFIBDBEditfind',
            'TEditFind2000', 'TFIBHYGEditFind'}
EVENTOS_BUSCADOR = {'OnVerificacion', 'OnBusqueda', 'OnExiste', 'OnNoExiste'}
# Propiedades de EditFind que pasan al TBuscadorCampo
PROPS_BUSCADOR = {'CondicionBusqueda', 'SalirSiNoExiste', 'AutoCambiarFoco'}


def nombres_firma(firma):
    """'(Sender: TObject; var Key: Word)' -> 'Sender, Key'"""
    nombres = []
    for grupo in [g.strip() for g in firma.strip().strip('()').split(';') if g.strip()]:
        izq = grupo.split(':')[0]
        for m in ('var ', 'const ', 'out '):
            if izq.strip().lower().startswith(m):
                izq = izq.strip()[len(m):]
        nombres += [x.strip() for x in izq.split(',') if x.strip()]
    return ', '.join(nombres)


def firmas_pas(src, cls):
    """Métodos declarados en la clase del formulario de Merge: nombre -> firma normalizada."""
    m = re.search(r'\b%s\s*=\s*class\b(.*?)\n\s*end\s*;' % cls, src, re.S | re.I)
    out = {}
    if not m:
        return out
    for mm in re.finditer(r'\bprocedure\s+(\w+)\s*(\([^)]*\))?\s*;', m.group(1), re.I):
        out[mm.group(1).lower()] = vp.normaliza_firma(mm.group(2) or '()')
    return out


def enlaza_evento(ctx, inf, control, cls_dest, evento, metodo):
    """Devuelve el nombre del método a enlazar, o None si la firma no encaja."""
    esperada = vp.firma(cls_dest, evento)
    real = ctx.firmas.get(metodo.lower())
    if real is None:
        inf.revisar.append('%s.%s = %s: el método no está declarado en el formulario (¿venía de la base Merge?); '
                           'no se enlaza.' % (control, evento, metodo))
        return None
    if esperada is None or vp.normaliza_firma(esperada) == real:
        return metodo
    inf.revisar.append('%s.%s = %s: la firma %s no coincide con la de %s.%s %s; no se enlaza.'
                       % (control, evento, metodo, real, cls_dest, evento, esperada))
    return None


TECLA_FILTROS = {'obEmpresa': 0, 'obEjercicio': 1, 'obCanal': 2, 'obSerie': 3}


def filtro_entorno(filtros):
    f = ['0', '0', '0', '0']
    otros = []
    for t in re.findall(r'ob\w+', filtros or ''):
        if t in TECLA_FILTROS:
            f[TECLA_FILTROS[t]] = '1'
        else:
            otros.append(t)
    return ''.join(f), otros


class Contexto:
    def __init__(self, dm_nombre, dm_root):
        self.dm = dm_nombre              # 'DMProveedores'
        self.dm_root = dm_root
        self.datasources = {}            # DSxxx -> dataset en DM
        for c in dm_root.children:
            if c.cls == 'TDataSource':
                self.datasources[c.name] = (c.getv('DataSet') or '').strip()
        self.ds_usados = {}              # nombre local -> dataset
        self.buscadores = []             # config de EditFind2000
        self.buscadores_eventos = {}     # control -> [(evento, método)]
        self.eventos_nav = []
        self.principal = None
        self.firmas = {}             # métodos del formulario Merge
        self.adaptadores = []        # métodos puente generados
        self.asignaciones = []       # líneas a añadir en el constructor
        self.tipos = None            # diccionario de tipos (para datasets dentro del formulario)
        self.updates = []            # TFDUpdateSQL generados para datasets del formulario
        self.bloqueos = {}
        self.nuevos_campos = []      # componentes heredados en Merge que pasan a ser propios del frame
        self.combos_value = []       # combos con Values (su .Value pasa a .Text)


def ref_datasource(val, ctx, inf):
    """DMProveedores.DSProveedores -> DS local en el frame (patrón MaxFactu)."""
    v = val.strip()
    if MODO_M13:
        return v   # en Merge13 el formulario usa el DataSource del DM como en Merge
    if v.startswith(ctx.dm + '.'):
        ds = v.split('.', 1)[1]
        local = 'DSCabecera' if ds == ctx.principal else ds
        if local != 'DSCabecera':
            ctx.ds_usados[local] = ctx.datasources.get(ds, '')
        return local
    return v


def convierte_control(n, ctx, inf, parent_heredado):
    """Devuelve nodo convertido o None si se elimina."""
    cls = n.cls
    if cls in ELIMINAR:
        inf.quitados.append('%s: %s -> %s' % (n.name, cls, ELIMINAR[cls]))
        inf.cuenta('componentes G2K eliminados')
        return None
    if cls.startswith(('Tfr', 'THYReport')):
        inf.quitados.append('%s: %s (FastReport 2)' % (n.name, cls))
        inf.revisar.append('%s: informe FastReport 2 a migrar.' % n.name)
        return None
    destino, permitidas = MAPA.get(cls, (cls, None))
    new = dp.Node(n.kind, n.name, destino, n.order)
    eventos = {}                 # evento destino -> [métodos]
    for pname, vals in n.props:
        v = '\n'.join(vals).strip()
        if pname in ('DataSource', 'ListSource', 'MasterSource'):
            v = ref_datasource(v, ctx, inf)
            vals = [v]
        if (cls, pname) in PROP_RENOMBRA:
            inf.auto.append('%s.%s -> %s' % (n.name, pname, PROP_RENOMBRA[(cls, pname)]))
            pname = PROP_RENOMBRA[(cls, pname)]
        if vp.es_evento(pname):
            destino_ev = EVENTOS_RENOMBRA.get((cls, pname), pname)
            if cls in EDITFIND and pname in EVENTOS_BUSCADOR:
                ctx.buscadores_eventos.setdefault(n.name, []).append((pname, v))
                continue
            if cls == 'THYMNavigator' and pname == 'OnClickBefore':
                eventos.setdefault('BeforeAction', []).append(('adaptar_continua', v))
                continue
            if cls == 'THYMNavigator' and pname == 'OnChangeState':
                ds = ref_datasource((n.getv('DataSource') or '').strip(), ctx, inf) or 'DSCabecera'
                ctx.asignaciones.append('  %s.OnStateChange := %s;  // antes %s.OnChangeState' % (ds, v, n.name))
                inf.auto.append('%s.OnChangeState -> %s.OnStateChange (en el constructor)' % (n.name, ds))
                continue
            admitido = vp.admite(destino, destino_ev)
            if admitido is False:
                inf.revisar.append('%s.%s = %s: %s no tiene ese evento en Delphi 13; el método queda sin enganchar.'
                                   % (n.name, pname, v, destino))
                inf.cuenta('eventos sin equivalente')
                continue
            if destino_ev != pname:
                inf.auto.append('%s.%s -> %s' % (n.name, pname, destino_ev))
                inf.cuenta('eventos renombrados')
            eventos.setdefault(destino_ev, []).append(('directo', v))
            continue
        if pname in COMUNES or (permitidas is not None and pname in permitidas) or permitidas is None:
            if vp.admite(destino, pname) is False:
                inf.quitados.append('%s.%s (%s no la tiene)' % (n.name, pname, destino))
                continue
            new.props.append([pname, vals])
        else:
            inf.quitados.append('%s.%s (%s)' % (n.name, pname, cls))
    # enlazar eventos: directo si hay un método y la firma encaja; si no, método puente
    for ev, fuentes in eventos.items():
        if len(fuentes) == 1 and fuentes[0][0] == 'directo':
            m = enlaza_evento(ctx, inf, n.name, destino, ev, fuentes[0][1])
            if m:
                new.props.append([ev, [m]])
            continue
        nombre = '%s%sPuente' % (n.name, ev[2:] if ev.startswith('On') else ev)
        firma = vp.firma(destino, ev) or '(Sender: TObject)'
        cuerpo, locales = [], []
        for tipo, metodo in fuentes:
            real = ctx.firmas.get(metodo.lower())
            if real is None:
                inf.revisar.append('%s.%s: método %s no encontrado en el formulario.' % (n.name, ev, metodo))
                continue
            if tipo == 'adaptar_continua':
                locales = ['  Continua: Boolean;']
                cuerpo += ['  Continua := True;', '  %s(Sender, Button, Continua);' % metodo,
                           '  if not Continua then', '    Abort;']
            else:
                if real != vp.normaliza_firma(firma):
                    inf.revisar.append('%s.%s: %s tiene firma %s, distinta de %s; no se incluye en el puente.'
                                       % (n.name, ev, metodo, real, firma))
                    continue
                cuerpo.append('  %s(%s);' % (metodo, nombres_firma(firma)))
        if cuerpo:
            ctx.adaptadores.append({'nombre': nombre, 'firma': firma, 'cuerpo': cuerpo, 'locales': locales})
            new.props.append([ev, [nombre]])
            inf.auto.append('%s.%s -> método puente %s (%s)' % (n.name, ev, nombre,
                                                                  ', '.join(m for _, m in fuentes)))
            inf.cuenta('métodos puente generados')
    if cls in ('TLFDBComboBoxValue', 'TRxDBComboBox', 'TDBComboBoxValue'):
        ctx.combos_value.append(n.name)
    if cls in ('TLFDBComboBoxValue', 'TRxDBComboBox', 'TDBComboBoxValue') and n.get('Values.Strings'):
        inf.revisar.append('%s (%s): tenía Items (texto) y Values (valor guardado). TDBComboBox guarda el texto; '
                           'hay que decidir si guardar el valor (Values: %s).' % (n.name, cls, n.strings('Values.Strings')))
    if cls in ('TLFHYDBDescription', 'THYDBDescripcion'):
        new.set('ReadOnly', 'True'); new.set('TabStop', 'False')
        inf.revisar.append('%s: descripción calculada (%s.%s) pendiente; hoy queda como TEdit de solo lectura.'
                           % (n.name, (n.getv('Tabla_a_buscar') or '').strip("'"),
                              (n.getv('Campo_Descripcion') or '').strip("'")))
    if cls in ('TCurrencyEdit', 'TRightMaskEdit'):
        new.set('Alignment', 'taRightJustify')
    if destino == 'TAction' and new.get('Category'):
        # Merge: 'Categoria;Subcategoria' (submenús). MaxFactu crea un botón por categoría y le pone la
        # categoría como Name: tiene que ser un identificador válido -> se usa la categoría principal.
        cat_txt = ''.join(new.strings('Category') or []) if False else None
        valor = new.getv('Category')
        texto = ''.join(re.findall(r"'((?:[^']|'')*)'", valor)).replace("''", "'")
        for num in re.findall(r'#(\d+)', valor):
            pass
        principal = re.split(r'[;"]', texto)[0].strip()
        import unicodedata
        ident = ''.join(ch for ch in unicodedata.normalize('NFKD', principal) if ch.isascii())
        ident = re.sub(r'\W', '', ident)
        if ident and not ident[0].isdigit() and ident != texto:
            new.set('Category', dp.quote(ident))
            inf.auto.append('%s.Category: %s -> %s (MaxFactu usa la categoría como nombre de botón)'
                            % (n.name, texto, ident))
            inf.cuenta('categorías de acciones simplificadas')
    if cls == 'THYGRightEdit':
        new.set('Alignment', 'taRightJustify')
    if cls in EDITFIND:
        fe, otros = filtro_entorno(n.getv('Filtros'))
        campos = n.strings('Campos_Desplegar.Strings') or [s for s in ((n.getv('CampoNum') or "''").strip("'"),
                                                                        (n.getv('CampoStr') or "''").strip("'")) if s]
        ctx.buscadores.append({
            'control': n.name,
            'tabla': (n.getv('Tabla_a_buscar') or "''").strip("'").strip(),
            'campo': (n.getv('DataField') or "''").strip("'"),
            'devolver': (n.getv('CampoADevolver') or n.getv('CampoNum') or "''").strip("'"),
            'campos': campos,
            'filtro': fe,
            'otros': otros,
            'accion': (n.getv('Accion') or ''),
            'props': {p: n.getv(p) for p in PROPS_BUSCADOR if n.get(p) is not None},
            'condicion': [s for s in n.strings('CondicionBusqueda.Strings')] if n.get('CondicionBusqueda.Strings') else None,
            'db': MAPA[cls][0] == 'TDBEdit',
        })
        if otros:
            inf.revisar.append('%s: filtros %s sin equivalente en FiltroEntorno (pasar como SubConsulta).'
                               % (n.name, otros))
        if (n.getv('Accion') or ''):
            inf.revisar.append('%s: Accion=%s (alta rápida desde el buscador) pendiente de enganchar.'
                               % (n.name, n.getv('Accion')))
        inf.cuenta('EditFind2000 -> TDBEdit + TBuscadorCampo')
    if cls in MAPA:
        inf.cuenta('%s -> %s' % (cls, destino))
    elif n.kind == 'inline':
        inf.revisar.append('%s: frame de Merge (%s) incrustado; hay que convertir también su unidad.' % (n.name, cls))
    elif cls not in VCL_OK and cls not in ESTANDAR_D13 and cls not in vp.CLASES:
        inf.bloqueantes.append('%s: clase %s no existe en Delphi 13 y no tiene regla de conversión '
                               '(componente propio a portar o sustituir).' % (n.name, cls))
        inf.cuenta('BLOQUEANTES: clases sin regla')
    for c in n.children:
        r = convierte_nodo(c, ctx, inf)
        if r is not None:
            new.children.append(r)
    return new


SIN_TEECHART = False   # --sin-teechart: TeeChart VCL no instalado en Delphi 13
MODO_M13 = False       # destino Merge13: el formulario sigue siendo formulario con las bases de Merge13
BASE_M13 = {}          # componentes de las bases de Merge13 (UFPEdit*...): nombre -> clase


def convierte_nodo(n, ctx, inf):
    if MODO_M13 and n.kind == 'inherited':
        if n.name in HEREDADOS_ELIMINAR:
            inf.quitados.append('%s (heredado de la base G2K de Merge)' % n.name)
            return None
        if n.name in BASE_M13:
            new = convierte_control(n, ctx, inf, True)
            new.cls = BASE_M13[n.name]
            new.props = [p for p in new.props if vp.admite(new.cls, p[0]) is not False]
            return new
    if SIN_TEECHART and n.cls in ('TDBChart', 'TChart'):
        p = dp.Node('object' if n.kind == 'inherited' else n.kind, n.name, 'TPanel', n.order)
        for k in ('Left', 'Top', 'Width', 'Height', 'Align', 'Anchors', 'TabOrder', 'Visible'):
            if n.get(k):
                p.set(k, n.get(k))
        p.set('Caption', dp.quote('Gráfico pendiente (TeeChart no instalado)'))
        inf.revisar.append('%s: gráfico TeeChart sustituido por un TPanel (TeeChart VCL no está en las librerías).'
                           % n.name)
        inf.cuenta('gráficos TeeChart sustituidos')
        return p
    if SIN_TEECHART and n.cls.endswith('Series'):
        return None
    if n.cls in TRANS:
        return convierte_transaccion(n, inf)
    if n.cls in DATASETS_RW or n.cls in DATASETS_RO:
        q = convierte_dataset(n, None, ctx.tipos, inf, ctx.updates)
        if getattr(n, '_bloqueo', None):
            ctx.bloqueos[n.name] = n._bloqueo
        return q
    if n.cls in QUERIES:
        return convierte_query(n, inf)
    if n.kind == 'inherited':
        if n.name in HEREDADOS_ELIMINAR:
            inf.quitados.append('%s (heredado de la base G2K)' % n.name)
            # sus hijos propios sí hay que conservarlos (p.ej. acciones en ALMain)
            return None
        if n.name in HEREDADOS:
            target = HEREDADOS[n.name]
            new = convierte_control(n, ctx, inf, True)
            new.name = target
            base_cls = {'PNLMain': 'TPanel', 'TBMain': 'TToolBar', 'NavMain': 'TDBNavigator', 'PCMain': 'TPageControl',
                        'TSFicha': 'TTabSheet', 'TSTabla': 'TTabSheet', 'DBGMain': 'TDBGrid', 'SBFicha': 'TScrollBox',
                        'Acciones': 'TActionList'}[target]
            new.cls = base_cls
            # en la base MaxFactu estas propiedades ya vienen definidas
            for p in ('Left', 'Top', 'Width', 'Height', 'Align', 'DataSource', 'Caption', 'BevelOuter', 'Images',
                      'TabOrder', 'Font.Charset', 'Font.Color', 'Font.Height', 'Font.Name', 'Font.Style',
                      'ParentFont', 'Color', 'Flat', 'Hints.Strings', 'Enabled', 'Options', 'ReadOnly'):
                new.delete(p)
            return new
        # heredado de la base Merge que no existe en la base MaxFactu -> objeto propio,
        # completando las propiedades que venían de la base (UFPEdit/UFPEditSimple/UFPEditSinNavegador)
        base = BASES_MERGE.get(n.name)
        if base is not None:
            propias = {p for p, _ in n.props}
            n.props = [list(p) for p in base.props if p[0] not in propias] + n.props
            n.cls = base.cls if n.cls == base.cls else n.cls
        n.kind = 'object'
        ctx.nuevos_campos.append((n.name, MAPA.get(n.cls, (n.cls,))[0]))
        inf.revisar.append('%s: era heredado de la base Merge; ahora es componente propio del frame.' % n.name)
    return convierte_control(n, ctx, inf, False)


def convierte_form(root, ctx, inf, frame_name, frame_cls):
    # localizar datasource principal (el del NavMain o DBGMain)
    nav = root.find('NavMain') or root.find('DBGMain')
    principal = None
    for cand in (root.find('NavMain'), root.find('DBGMain')):
        if cand and cand.get('DataSource'):
            principal = cand.getv('DataSource').split('.')[-1]
            break
    ctx.principal = principal
    new = dp.Node('inherited', frame_name, frame_cls)
    for p in ('Width', 'Height'):
        if root.get(p):
            new.set(p, root.get(p))
    quitadas = [p for p, _ in root.props if p not in ('Width', 'Height')]
    inf.quitados.append('Propiedades de TForm raíz: ' + ', '.join(quitadas))
    for c in root.children:
        r = convierte_nodo(c, ctx, inf)
        if r is not None:
            new.children.append(r)
    # rescatar hijos de heredados eliminados (acciones de ALMain ya cubiertas; TBActions -> botones de Acciones)
    for c in root.children:
        if c.kind == 'inherited' and c.name in HEREDADOS_ELIMINAR and c.name not in ('CEMainPMEdit', 'TBActions'):
            for h in c.children:
                if h.cls in ('TToolButton',):
                    inf.quitados.append('%s (botón de %s; las acciones se muestran con CargaAcciones)' % (h.name, c.name))
                    continue
                r = convierte_nodo(h, ctx, inf)
                if r is not None:
                    new.children.append(r)
    # Adjuntos (patrón MaxFactu): cada acción de categoría 'Adjuntos' tiene su opción en PMConfigurar
    acc = next((c for c in new.children if c.name == 'Acciones'), None)
    adj = [a for a in (acc.children if acc else []) if (a.getv('Category') or '').strip("'") == 'Adjuntos']
    if adj:
        pm = next((c for c in new.children if c.name == 'PMConfigurar'), None)
        if pm is None:
            pm = dp.Node('inherited', 'PMConfigurar', 'TPopupMenu')
            new.children.append(pm)
        for a in adj:
            mi = dp.Node('object', 'MI' + a.name, 'TMenuItem')
            mi.set('Action', a.name)
            pm.children.append(mi)
            ctx.nuevos_campos.append((mi.name, 'TMenuItem'))
        inf.auto.append('PMConfigurar: añadidas %d opciones de adjuntos (%s)' % (len(adj), ', '.join(a.name for a in adj)))
    # TFDUpdateSQL de los datasets que estaban en el propio formulario
    new.children.extend(ctx.updates)
    # datasources locales del frame (patrón MaxFactu)
    top = 20
    for ds in sorted(ctx.ds_usados):
        d = dp.Node('object', ds, 'TDataSource')
        d.set('Left', '600'); d.set('Top', str(top)); top += 48
        new.children.append(d)
    return new


def carga_bases_m13(dir_proyecto):
    """Componentes de las bases de ventana de Merge13 (lo que un formulario convertido hereda)."""
    import os
    for u in ('UFPEditSinNavegador', 'UFPEditSimple', 'UFPEdit', 'UFPEditDetalle'):
        ruta = os.path.join(dir_proyecto, u + '.dfm')
        if os.path.exists(ruta):
            r = dp.parse(open(ruta, encoding='latin-1', errors='replace').read().lstrip('\ufeff'))
            for n in r.walk():
                if n is not r:
                    BASE_M13[n.name] = n.cls


def convierte_form_m13(root, ctx, inf):
    """Formulario de Merge -> formulario de Merge13 (mismo nombre, misma clase, misma base)."""
    new = dp.Node('inherited' if root.kind == 'inherited' else 'object', root.name, root.cls)
    for pname, vals in root.props:
        if vp.es_evento(pname):
            m = enlaza_evento(ctx, inf, root.name, 'TForm', pname, '\n'.join(vals).strip())
            if m:
                new.props.append([pname, [m]])
        elif vp.admite('TForm', pname):
            new.props.append([pname, vals])
        else:
            inf.quitados.append('%s.%s (TForm no la tiene)' % (root.name, pname))
    for c in root.children:
        r = convierte_nodo(c, ctx, inf)
        if r is not None:
            new.children.append(r)
    new.children.extend(ctx.updates)
    return new
