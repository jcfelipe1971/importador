# -*- coding: utf-8 -*-
"""Propiedades y eventos PUBLICADOS de las clases VCL de Delphi 13 que genera el conversor,
con la firma de cada evento. Lo que no esté aquí no se escribe en el DFM."""

_BASE = {'Left', 'Top', 'Width', 'Height', 'Align', 'AlignWithMargins', 'Anchors', 'BiDiMode', 'Constraints',
         'Cursor', 'CustomHint', 'Enabled', 'Font', 'Hint', 'HelpContext', 'HelpKeyword', 'HelpType', 'Margins',
         'ParentBiDiMode', 'ParentCustomHint', 'ParentFont', 'ParentShowHint', 'PopupMenu', 'ShowHint',
         'StyleElements', 'StyleName', 'Tag', 'Touch', 'Visible', 'DragCursor', 'DragKind', 'DragMode',
         'ExplicitLeft', 'ExplicitTop', 'ExplicitWidth', 'ExplicitHeight'}
_WIN = _BASE | {'Color', 'ParentColor', 'TabOrder', 'TabStop', 'DoubleBuffered', 'ParentDoubleBuffered', 'DesignSize',
                'ImeMode', 'ImeName'}
_BEVEL = {'BevelEdges', 'BevelInner', 'BevelKind', 'BevelOuter', 'BevelWidth'}
_EV_MOUSE = {'OnClick', 'OnContextPopup', 'OnDblClick', 'OnDragDrop', 'OnDragOver', 'OnEndDock', 'OnEndDrag',
             'OnGesture', 'OnMouseActivate', 'OnMouseDown', 'OnMouseEnter', 'OnMouseLeave', 'OnMouseMove',
             'OnMouseUp', 'OnStartDock', 'OnStartDrag'}
_EV_FOCO = {'OnEnter', 'OnExit'}
_EV_TECLA = {'OnKeyDown', 'OnKeyPress', 'OnKeyUp'}
_EV_WIN = _EV_MOUSE | _EV_FOCO | _EV_TECLA

CLASES = {
    'TLabel': (_BASE | {'Alignment', 'AutoSize', 'Caption', 'Color', 'EllipsisPosition', 'FocusControl',
                        'GlowSize', 'Layout', 'ParentColor', 'ShowAccelChar', 'Transparent', 'WordWrap'}, _EV_MOUSE),
    'TEdit': (_WIN | _BEVEL | {'Alignment', 'AutoSelect', 'AutoSize', 'BorderStyle', 'CharCase', 'HideSelection',
                               'MaxLength', 'NumbersOnly', 'OEMConvert', 'PasswordChar', 'ReadOnly', 'Text',
                               'TextHint'}, _EV_WIN | {'OnChange'}),
    'TDBEdit': (_WIN | _BEVEL | {'AutoSelect', 'AutoSize', 'BorderStyle', 'CharCase', 'DataField', 'DataSource',
                                 'HideSelection', 'MaxLength', 'OEMConvert', 'PasswordChar', 'ReadOnly'},
                _EV_WIN | {'OnChange'}),
    'TMemo': (_WIN | _BEVEL | {'Alignment', 'BorderStyle', 'HideSelection', 'Lines', 'MaxLength', 'OEMConvert',
                               'ReadOnly', 'ScrollBars', 'WantReturns', 'WantTabs', 'WordWrap'}, _EV_WIN | {'OnChange'}),
    'TDBMemo': (_WIN | _BEVEL | {'Alignment', 'AutoDisplay', 'BorderStyle', 'DataField', 'DataSource',
                                 'HideSelection', 'MaxLength', 'OEMConvert', 'ReadOnly', 'ScrollBars', 'WantReturns',
                                 'WantTabs', 'WordWrap'}, _EV_WIN | {'OnChange'}),
    'TCheckBox': (_WIN | {'Action', 'Alignment', 'AllowGrayed', 'Caption', 'Checked', 'State', 'WordWrap'}, _EV_WIN),
    'TDBCheckBox': (_WIN | {'Alignment', 'AllowGrayed', 'Caption', 'DataField', 'DataSource', 'ReadOnly',
                            'ValueChecked', 'ValueUnchecked', 'WordWrap'}, _EV_WIN),
    'TComboBox': (_WIN | _BEVEL | {'AutoComplete', 'AutoCloseUp', 'AutoDropDown', 'CharCase', 'DropDownCount',
                                   'ExtendedUI', 'ItemHeight', 'ItemIndex', 'Items', 'MaxLength', 'Sorted', 'Style',
                                   'Text', 'TextHint'},
                  _EV_WIN | {'OnChange', 'OnCloseUp', 'OnDrawItem', 'OnDropDown', 'OnMeasureItem', 'OnSelect'}),
    'TDBComboBox': (_WIN | _BEVEL | {'AutoComplete', 'AutoDropDown', 'CharCase', 'DataField', 'DataSource',
                                     'DropDownCount', 'ItemHeight', 'Items', 'ReadOnly', 'Sorted', 'Style'},
                    _EV_WIN | {'OnChange', 'OnCloseUp', 'OnDrawItem', 'OnDropDown', 'OnMeasureItem', 'OnSelect'}),
    'TDBLookupComboBox': (_WIN | _BEVEL | {'DataField', 'DataSource', 'DropDownAlign', 'DropDownRows',
                                           'DropDownWidth', 'KeyField', 'ListField', 'ListFieldIndex', 'ListSource',
                                           'NullValueKey', 'ReadOnly'},
                          _EV_WIN | {'OnCloseUp', 'OnDropDown'}),
    'TPanel': (_WIN | _BEVEL | {'Alignment', 'BorderStyle', 'BorderWidth', 'Caption', 'DockSite', 'FullRepaint',
                                'Locked', 'Padding', 'ParentBackground', 'ShowCaption', 'UseDockManager',
                                'VerticalAlignment', 'AutoSize'},
               _EV_MOUSE | _EV_FOCO | {'OnCanResize', 'OnConstrainedResize', 'OnDockDrop', 'OnDockOver',
                                       'OnGetSiteInfo', 'OnResize', 'OnUnDock'}),
    'TScrollBox': (_WIN | _BEVEL | {'AutoScroll', 'AutoSize', 'BorderStyle', 'HorzScrollBar', 'VertScrollBar',
                                    'Padding', 'ParentBackground'},
                   _EV_MOUSE | _EV_FOCO | {'OnCanResize', 'OnConstrainedResize', 'OnMouseWheel',
                                           'OnMouseWheelDown', 'OnMouseWheelUp', 'OnResize'}),
    'TGroupBox': (_WIN | {'Caption', 'Padding', 'ParentBackground'}, _EV_MOUSE | _EV_FOCO),
    'TRadioGroup': (_WIN | {'Caption', 'Columns', 'ItemIndex', 'Items', 'ParentBackground', 'WordWrap'},
                    _EV_MOUSE | _EV_FOCO),
    'TDBRadioGroup': (_WIN | {'Caption', 'Columns', 'DataField', 'DataSource', 'Items', 'ParentBackground',
                              'ReadOnly', 'Values', 'WordWrap'}, _EV_MOUSE | _EV_FOCO | {'OnChange'}),
    'TPageControl': (_WIN | {'ActivePage', 'HotTrack', 'Images', 'MultiLine', 'OwnerDraw', 'RaggedRight',
                             'ScrollOpposite', 'Style', 'TabHeight', 'TabIndex', 'TabPosition', 'TabWidth'},
                     _EV_MOUSE | _EV_FOCO | {'OnChange', 'OnChanging', 'OnDrawTab', 'OnGetImageIndex',
                                             'OnResize'}),
    'TTabSheet': (_BASE | {'Caption', 'DoubleBuffered', 'Highlighted', 'ImageIndex', 'PageIndex', 'ParentDoubleBuffered',
                           'TabVisible', 'DesignSize', 'Padding'},
                  (_EV_MOUSE - {'OnClick', 'OnDblClick'}) | _EV_FOCO | {'OnShow', 'OnHide', 'OnResize'}),
    'TToolBar': (_WIN | {'AutoSize', 'ButtonHeight', 'ButtonWidth', 'Caption', 'DisabledImages', 'DrawingStyle',
                         'EdgeBorders', 'EdgeInner', 'EdgeOuter', 'Flat', 'HotImages', 'Images', 'Indent', 'List',
                         'Menu', 'ShowCaptions', 'Transparent', 'Wrapable', 'ParentBackground'},
                 _EV_MOUSE | {'OnResize'}),
    'TToolButton': (_BASE | {'Action', 'AllowAllUp', 'AutoSize', 'Caption', 'Down', 'DropdownMenu', 'Grouped',
                             'ImageIndex', 'ImageName', 'Indeterminate', 'Marked', 'MenuItem', 'Style', 'Wrap'},
                    _EV_MOUSE),
    'TDBNavigator': (_WIN | {'ConfirmDelete', 'DataSource', 'Flat', 'Hints', 'Kind', 'VisibleButtons'},
                     _EV_MOUSE | _EV_FOCO | {'BeforeAction', 'OnResize'}),
    'TDBGrid': (_WIN | {'BorderStyle', 'Columns', 'DataSource', 'DefaultDrawing', 'DrawingStyle', 'FixedColor',
                        'GradientEndColor', 'GradientStartColor', 'Options', 'ParentBackground', 'ReadOnly',
                        'TitleFont'},
                _EV_WIN | {'OnCellClick', 'OnColEnter', 'OnColExit', 'OnColumnMoved', 'OnDrawColumnCell',
                           'OnDrawDataCell', 'OnEditButtonClick', 'OnTitleClick'}),
    'TDBCtrlGrid': (_WIN | {'AllowDelete', 'AllowInsert', 'ColCount', 'DataSource', 'Orientation', 'PanelBorder',
                            'PanelHeight', 'PanelWidth', 'RowCount', 'SelectedColor', 'ShowFocus'},
                    _EV_WIN | {'OnPaintPanel'}),
    'TDateTimePicker': (_WIN | _BEVEL | {'CalAlignment', 'Checked', 'Date', 'DateFormat', 'DateMode', 'Format',
                                         'Kind', 'MaxDate', 'MinDate', 'ParseInput', 'ShowCheckbox', 'Time'},
                        _EV_WIN | {'OnChange', 'OnCloseUp', 'OnDropDown', 'OnUserInput'}),
    'TActionList': ({'Images', 'State', 'Left', 'Top'}, {'OnChange', 'OnExecute', 'OnStateChange', 'OnUpdate'}),
    'TAction': ({'AutoCheck', 'Caption', 'Category', 'Checked', 'Enabled', 'GroupIndex', 'HelpContext',
                 'HelpKeyword', 'HelpType', 'Hint', 'ImageIndex', 'ImageName', 'SecondaryShortCuts', 'ShortCut',
                 'Visible'}, {'OnExecute', 'OnHint', 'OnUpdate'}),
    'TSpeedButton': (_BASE | {'Action', 'AllowAllUp', 'Caption', 'Down', 'Flat', 'Glyph', 'GroupIndex',
                              'ImageIndex', 'ImageName', 'Images', 'Layout', 'Margin', 'NumGlyphs', 'ParentColor',
                              'Spacing', 'Transparent'}, _EV_MOUSE),
    'TBitBtn': (_WIN | {'Action', 'Cancel', 'Caption', 'Default', 'Glyph', 'ImageIndex', 'ImageName', 'Images',
                        'Kind', 'Layout', 'Margin', 'ModalResult', 'NumGlyphs', 'Spacing', 'Style', 'WordWrap'},
                _EV_WIN),
    'TButton': (_WIN | {'Action', 'Cancel', 'Caption', 'CommandLinkHint', 'Default', 'ElevationRequired',
                        'ImageAlignment', 'ImageIndex', 'ImageName', 'Images', 'ModalResult', 'Style', 'WordWrap'},
                _EV_WIN),
    'TMenuItem': ({'Action', 'AutoCheck', 'AutoHotkeys', 'AutoLineReduction', 'Bitmap', 'Break', 'Caption', 'Checked',
                   'Default', 'Enabled', 'GroupIndex', 'HelpContext', 'Hint', 'ImageIndex', 'ImageName',
                   'RadioItem', 'ShortCut', 'SubMenuImages', 'Visible'},
                  {'OnAdvancedDrawItem', 'OnClick', 'OnDrawItem', 'OnMeasureItem'}),
    'TPopupMenu': ({'Alignment', 'AutoHotkeys', 'AutoLineReduction', 'AutoPopup', 'BiDiMode', 'HelpContext',
                    'Images', 'MenuAnimation', 'OwnerDraw', 'ParentBiDiMode', 'TrackButton', 'Left', 'Top'},
                   {'OnChange', 'OnClose', 'OnPopup'}),
    'TTimer': ({'Enabled', 'Interval', 'Left', 'Top'}, {'OnTimer'}),
    'TSplitter': (_BASE | {'AutoSnap', 'Beveled', 'Color', 'MinSize', 'ParentColor', 'ResizeStyle'},
                  {'OnCanResize', 'OnMoved', 'OnPaint'}),
    'TDataSource': ({'AutoEdit', 'DataSet', 'Enabled', 'Left', 'Top'}, {'OnDataChange', 'OnStateChange',
                                                                        'OnUpdateData'}),
    'TImage': (_BASE | {'AutoSize', 'Center', 'IncrementalDisplay', 'Picture', 'Proportional', 'Stretch',
                        'Transparent'}, _EV_MOUSE | {'OnProgress'}),
    'TDBImage': (_WIN | {'AutoDisplay', 'BorderStyle', 'Center', 'DataField', 'DataSource', 'Proportional',
                         'QuickDraw', 'ReadOnly', 'Stretch'}, _EV_WIN),
    'TBevel': (_BASE | {'Shape', 'Style'}, set()),
    'TForm': ({'Left', 'Top', 'Width', 'Height', 'ClientWidth', 'ClientHeight', 'Caption', 'Color', 'Font', 'BorderIcons',
               'BorderStyle', 'BorderWidth', 'FormStyle', 'KeyPreview', 'Menu', 'Position', 'WindowState', 'Visible',
               'PixelsPerInch', 'TextHeight', 'Scaled', 'AutoScroll', 'AutoSize', 'Constraints', 'Icon', 'HelpFile',
               'HelpContext', 'Hint', 'ShowHint', 'ParentFont', 'PopupMenu', 'Padding', 'DoubleBuffered', 'AlphaBlend',
               'AlphaBlendValue', 'Tag', 'StyleElements', 'Align', 'Anchors', 'DefaultMonitor', 'ScreenSnap',
               'SnapBuffer', 'TransparentColor', 'TransparentColorValue', 'UseDockManager', 'DockSite', 'DragKind',
               'DragMode', 'Enabled', 'HorzScrollBar', 'VertScrollBar', 'ExplicitWidth', 'ExplicitHeight',
               'ExplicitLeft', 'ExplicitTop', 'DesignSize'},
              _EV_WIN | {'OnActivate', 'OnClose', 'OnCloseQuery', 'OnCreate', 'OnDestroy', 'OnDeactivate', 'OnHide',
                         'OnShow', 'OnResize', 'OnPaint', 'OnCanResize', 'OnMouseWheel'}),
    'TDBText': (_BASE | {'Alignment', 'AutoSize', 'Color', 'DataField', 'DataSource', 'ParentColor', 'Transparent',
                         'WordWrap'}, _EV_MOUSE),
    'TRadioButton': (_WIN | {'Action', 'Alignment', 'Caption', 'Checked', 'WordWrap'}, _EV_WIN),
    'TShape': (_BASE | {'Brush', 'Pen', 'Shape'}, _EV_MOUSE),
}

# Sub-propiedades escritas como Prop.Sub = ... o colecciones
COMPUESTAS = {'Font', 'Margins', 'Constraints', 'TitleFont', 'Padding', 'HorzScrollBar', 'VertScrollBar', 'Glyph',
              'Picture', 'Items', 'Lines', 'Hints', 'Brush', 'Pen', 'Touch', 'Columns', 'Bitmap', 'Values',
              'SecondaryShortCuts', 'CustomHint'}

N = '(Sender: TObject)'
FIRMAS = {
    'OnClick': N, 'OnDblClick': N, 'OnChange': N, 'OnEnter': N, 'OnExit': N, 'OnResize': N, 'OnShow': N,
    'OnHide': N, 'OnTimer': N, 'OnExecute': N, 'OnUpdate': N, 'OnPopup': N, 'OnDropDown': N, 'OnCloseUp': N,
    'OnSelect': N, 'OnMouseEnter': N, 'OnMouseLeave': N, 'OnColEnter': N, 'OnColExit': N, 'OnEditButtonClick': N,
    'OnStateChange': N, 'OnMoved': N, 'OnUpdateData': N, 'OnClose': N,
    'OnKeyDown': '(Sender: TObject; var Key: Word; Shift: TShiftState)',
    'OnKeyUp': '(Sender: TObject; var Key: Word; Shift: TShiftState)',
    'OnKeyPress': '(Sender: TObject; var Key: Char)',
    'OnMouseDown': '(Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer)',
    'OnMouseUp': '(Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer)',
    'OnMouseMove': '(Sender: TObject; Shift: TShiftState; X, Y: Integer)',
    'OnDragDrop': '(Sender, Source: TObject; X, Y: Integer)',
    'OnDragOver': '(Sender, Source: TObject; X, Y: Integer; State: TDragState; var Accept: Boolean)',
    'OnContextPopup': '(Sender: TObject; MousePos: TPoint; var Handled: Boolean)',
    'OnChanging': '(Sender: TObject; var AllowChange: Boolean)',
    'OnCellClick': '(Column: TColumn)', 'OnTitleClick': '(Column: TColumn)',
    'OnDrawColumnCell': '(Sender: TObject; const Rect: TRect; DataCol: Integer; Column: TColumn; State: TGridDrawState)',
    'OnDataChange': '(Sender: TObject; Field: TField)',
    'OnPaintPanel': '(DBCtrlGrid: TDBCtrlGrid; Index: Integer)',
    'OnDrawTab': '(Control: TCustomTabControl; TabIndex: Integer; const Rect: TRect; Active: Boolean)',
    'OnCanResize': '(Sender: TObject; var NewWidth, NewHeight: Integer; var Resize: Boolean)',
    'OnActivate': N, 'OnCreate': N, 'OnDestroy': N, 'OnDeactivate': N, 'OnPaint': N,
    'OnClose': '(Sender: TObject; var Action: TCloseAction)',
    'OnCloseQuery': '(Sender: TObject; var CanClose: Boolean)',
}
# en TDBNavigator OnClick y BeforeAction llevan el botón
FIRMAS_CLASE = {
    ('TDBNavigator', 'OnClick'): '(Sender: TObject; Button: TNavigateBtn)',
    ('TDBNavigator', 'BeforeAction'): '(Sender: TObject; Button: TNavigateBtn)',
}


def firma(cls, evento):
    return FIRMAS_CLASE.get((cls, evento)) or FIRMAS.get(evento)


def normaliza_firma(params):
    """'(Sender: TObject; var Key: Word)' -> [('', 'tobject'), ('var', 'word')]"""
    params = (params or '').strip()
    if params.startswith('('):
        params = params[1:]
    if params.endswith(')'):
        params = params[:-1]
    out = []
    for grupo in [g.strip() for g in params.split(';') if g.strip()]:
        if ':' not in grupo:
            continue
        nombres, tipo = grupo.rsplit(':', 1)
        tipo = tipo.split('=')[0].strip().lower()
        mod = ''
        nombres = nombres.strip()
        for m in ('var ', 'const ', 'out '):
            if nombres.lower().startswith(m):
                mod, nombres = m.strip(), nombres[len(m):]
        for _ in nombres.split(','):
            out.append((mod, tipo))
    return out


def admite(cls, prop):
    if cls not in CLASES:
        return None            # clase no catalogada (TeeChart...): no se filtra
    props, eventos = CLASES[cls]
    if prop in eventos or prop in props:
        return True
    raiz = prop.split('.')[0]
    if raiz in COMPUESTAS and (raiz in props or raiz in ('Items', 'Lines', 'Hints', 'Values', 'Columns')):
        return raiz in props
    return False


def es_evento(prop):
    return prop.startswith('On') or prop in ('BeforeAction', 'AfterAction')
