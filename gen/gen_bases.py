# -*- coding: utf-8 -*-
"""Bases de formulario de Merge13 (nombres de Merge) a partir de las bases de frames de MaxFactu (visual y rejillas)."""
import sys, re
sys.path.insert(0, '/home/claude/conv')
import dfmparser as dp
MF = '/home/claude/mf2/maxfactu/'
DEST = sys.argv[1]

def lee(f):
    return open(MF + f, encoding='utf-8-sig', errors='replace').read().replace('\r\n', '\n')

def escribe(f, t):
    open(DEST + '/' + f, 'w', encoding='utf-8-sig').write(t)

REN = [(r'\bPNLMain\b', 'PMain'), (r'\bSBFicha\b', 'PEdit'), (r'\bAcciones\b', 'ALMain'), (r'\bPStatus\b', 'TBActions'),
       (r'\bToolButton2\b', 'TSepFiltro'), (r'\bPNLDetalle\b', 'PDetalle'), (r'\bDBGDetalle\b', 'DBGFDetalle'),
       (r'\bTFRMMantenimientoDetalle\b', 'TFPEditDetalle'), (r'\bTFRMMantenimientoSimple\b', 'TFPEdit'),
       (r'\bTFRMNavegador\b', 'TFPEditSimple'), (r'\bTFRMSimple\b', 'TFPEditSinNavegador'),
       (r'\bFRMMantenimientoDetalle\b', 'FPEditDetalle'), (r'\bFRMMantenimientoSimple\b', 'FPEdit'),
       (r'\bUFRMMantenimientoSimple\b', 'UFPEdit'), (r'\bUFRMNavegador\b', 'UFPEditSimple'),
       (r'\bUFRMSimple\b', 'UFPEditSinNavegador'), (r'\bUFRMMantenimientoDetalle\b', 'UFPEditDetalle')]

def renombra(t):
    for a, b in REN:
        t = re.sub(a, b, t)
    return t

def quita_frame(t):
    """Quita el mecanismo OnCreate/OnDestroy propio de los frames (un TForm ya los tiene)."""
    t = re.sub(r'\n\s*fOnCreate: TNotifyEvent;', '', t)
    t = re.sub(r'\n\s*fOnDestroy: TNotifyEvent;', '', t)
    t = re.sub(r'\n\s*property OnCreate: TNotifyEvent read fOnCreate write fOnCreate;', '', t)
    t = re.sub(r'\n\s*property OnDestroy: TNotifyEvent read fOnDestroy write fOnDestroy;', '', t)
    t = re.sub(r'\n\s*if Assigned\(fOnCreate\) then\s*\n?\s*fOnCreate\(Self\);', '', t)
    t = re.sub(r'\n\s*if Assigned\(fOnDestroy\) then\s*\n?\s*fOnDestroy\(Self\);', '', t)
    return t

# ------------------------------------------------------------ TFPEditSinNavegador
escribe('UFPEditSinNavegador.pas', '''unit UFPEditSinNavegador;

// Base de todas las ventanas de Merge13 (en Merge: TFPEditSinNavegador).
// Estilo MaxFactu: barra superior (TBMain), panel principal (PMain) y barra inferior de acciones (TBActions)
// con un botón por categoría de las acciones de ALMain. Se puede mostrar en ventana o dentro de una pestaña.

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, System.Generics.Collections,
  Vcl.Graphics, Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.ToolWin, Vcl.ComCtrls, Vcl.ExtCtrls, Vcl.StdCtrls,
  Vcl.Menus, System.Actions, Vcl.ActnList;

type
  TFPEditSinNavegador = class(TForm)
    PMain: TPanel;
    TBMain: TToolBar;
    TBActions: TPanel;
    ALMain: TActionList;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure FormShow(Sender: TObject);
    procedure FormKeyUp(Sender: TObject; var Key: Word; Shift: TShiftState);
  private
    FAccionesCargadas: Boolean;
  protected
    function ExisteBTCategoria(Nombre: string): TButton;
    procedure BTClick(Sender: TObject);
  public
    SalirConEscapeHabilitado: Boolean;
    procedure SalirConEscape(Habilitado: Boolean = True);
    procedure CargaAcciones;
  end;

var
  FPEditSinNavegador: TFPEditSinNavegador;

implementation

{$R *.dfm}

uses UUtilGuardaConfiguracion;

procedure TFPEditSinNavegador.FormCreate(Sender: TObject);
begin
  SalirConEscapeHabilitado := False;
end;

procedure TFPEditSinNavegador.FormShow(Sender: TObject);
begin
  if not FAccionesCargadas then
  begin
    FAccionesCargadas := True;
    CargaAcciones;
    CargaIniFormulario(Self);
  end;
end;

procedure TFPEditSinNavegador.FormClose(Sender: TObject; var Action: TCloseAction);
begin
  GuardaFormulario(Self);
  Action := caFree;
end;

procedure TFPEditSinNavegador.FormKeyUp(Sender: TObject; var Key: Word; Shift: TShiftState);
begin
  if (Key = VK_ESCAPE) and SalirConEscapeHabilitado then
    Close;
end;

procedure TFPEditSinNavegador.SalirConEscape(Habilitado: Boolean);
begin
  SalirConEscapeHabilitado := Habilitado;
end;

function TFPEditSinNavegador.ExisteBTCategoria(Nombre: string): TButton;
begin
  Result := nil;
  for var i := 0 to TBActions.ControlCount - 1 do
    if (TBActions.Controls[i] is TButton) and (TBActions.Controls[i].Name = Nombre) then
      Result := TBActions.Controls[i] as TButton;
end;

procedure TFPEditSinNavegador.BTClick(Sender: TObject);
begin
  (Sender as TButton).PopupMenu.Popup((Sender as TButton).ClientToScreen(Point(0, (Sender as TButton).Height)).X,
    (Sender as TButton).ClientToScreen(Point(0, (Sender as TButton).Height)).Y);
end;

procedure TFPEditSinNavegador.CargaAcciones;
// Igual que MaxFactu: un botón por categoría de acción en la barra inferior, con sus acciones en un menú
var
  BT: TButton;
  CategoryMenu, ListadosPopup: TPopupMenu;
  MenuItem, SubMenuItem: TMenuItem;
  Categoria, NombreBT: string;
  i, j: Integer;
  ListaEditar: TList<TMenuItem>;
begin
  CategoryMenu := nil;
  ListadosPopup := nil;
  ListaEditar := TList<TMenuItem>.Create;
  try
    for i := 0 to ALMain.ActionCount - 1 do
    begin
      Categoria := ALMain.Actions[i].Category;
      if Categoria = '' then
        Continue;
      if Categoria = 'Editar' then
      begin
        SubMenuItem := TMenuItem.Create(Self);
        SubMenuItem.Action := ALMain.Actions[i];
        ListaEditar.Add(SubMenuItem);
        Continue;
      end;
      NombreBT := 'BT';
      for var k := 1 to Length(Categoria) do
        if CharInSet(Categoria[k], ['A'..'Z', 'a'..'z', '0'..'9', '_']) then
          NombreBT := NombreBT + Categoria[k];
      BT := ExisteBTCategoria(NombreBT);
      if BT = nil then
      begin
        CategoryMenu := TPopupMenu.Create(Self);
        if Categoria = 'Listados' then
          ListadosPopup := CategoryMenu;
        MenuItem := TMenuItem.Create(CategoryMenu);
        MenuItem.Action := ALMain.Actions[i];
        CategoryMenu.Items.Add(MenuItem);
        BT := TButton.Create(Self);
        BT.Name := NombreBT;
        BT.Caption := Categoria + '  ' + #$25BC;
        BT.Parent := TBActions;
        BT.Align := alLeft;
        BT.AlignWithMargins := True;
        BT.Width := Canvas.TextWidth(BT.Caption) + 24;
        BT.PopupMenu := CategoryMenu;
        BT.OnClick := BTClick;
      end
      else
      begin
        MenuItem := TMenuItem.Create(BT.PopupMenu);
        MenuItem.Action := ALMain.Actions[i];
        BT.PopupMenu.Items.Add(MenuItem);
      end;
    end;
    if Assigned(ListadosPopup) and (ListaEditar.Count > 0) then
    begin
      MenuItem := TMenuItem.Create(ListadosPopup);
      MenuItem.Caption := 'Editar Listados';
      ListadosPopup.Items.Add(MenuItem);
      for j := 0 to ListaEditar.Count - 1 do
        MenuItem.Add(ListaEditar[j]);
    end;
    TBActions.Visible := TBActions.ControlCount > 0;
  finally
    ListaEditar.Free;
  end;
end;

end.
''')
escribe('UFPEditSinNavegador.dfm', '''object FPEditSinNavegador: TFPEditSinNavegador
  Left = 0
  Top = 0
  Caption = 'FPEditSinNavegador'
  ClientHeight = 480
  ClientWidth = 780
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -12
  Font.Name = 'Segoe UI'
  Font.Style = []
  KeyPreview = True
  Position = poDefaultPosOnly
  OnClose = FormClose
  OnCreate = FormCreate
  OnKeyUp = FormKeyUp
  OnShow = FormShow
  TextHeight = 15
  object TBMain: TToolBar
    Left = 0
    Top = 0
    Width = 780
    Height = 29
    TabOrder = 0
  end
  object PMain: TPanel
    Left = 0
    Top = 29
    Width = 780
    Height = 420
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 1
  end
  object TBActions: TPanel
    Left = 0
    Top = 449
    Width = 780
    Height = 31
    Align = alBottom
    BevelOuter = bvNone
    TabOrder = 2
  end
  object ALMain: TActionList
    Left = 704
    Top = 40
  end
end
''')

# ------------------------------------------------------------ TFPEditSimple (navegador)
escribe('UFPEditSimple.pas', '''unit UFPEditSimple;

// Ventana con navegador de datos (en Merge: TFPEditSimple). Estilo MaxFactu: TDBNavigator en la barra superior.

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, UFPEditSinNavegador, Vcl.ToolWin, Vcl.ComCtrls, Vcl.ExtCtrls, Vcl.DBCtrls,
  Data.DB, Vcl.Buttons, Vcl.StdCtrls, System.Actions, Vcl.ActnList;

type
  TFPEditSimple = class(TFPEditSinNavegador)
    NavMain: TDBNavigator;
    TSepNav: TToolButton;
    TSepTerc: TToolButton;
    TbuttComp: TToolButton;
    procedure FormCreate(Sender: TObject);
    procedure FormActivate(Sender: TObject);
    procedure FormShow(Sender: TObject);
  end;

var
  FPEditSimple: TFPEditSimple;

implementation

{$R *.dfm}

procedure TFPEditSimple.FormCreate(Sender: TObject);
begin
  inherited;
  NavMain.Hints.Text := 'Primero' + sLineBreak + 'Anterior' + sLineBreak + 'Siguiente' + sLineBreak + 'Último' +
    sLineBreak + 'Insertar' + sLineBreak + 'Eliminar' + sLineBreak + 'Editar' + sLineBreak + 'Guardar' + sLineBreak +
    'Cancelar' + sLineBreak + 'Refrescar' + sLineBreak + 'Aplicar Cambios' + sLineBreak + 'Cancelar Cambios';
end;

procedure TFPEditSimple.FormActivate(Sender: TObject);
begin
  // en Merge activaba el navegador G2K de la ventana activa; el TDBNavigator no lo necesita
end;

procedure TFPEditSimple.FormShow(Sender: TObject);
begin
  inherited;
end;

end.
''')
escribe('UFPEditSimple.dfm', '''inherited FPEditSimple: TFPEditSimple
  Caption = 'FPEditSimple'
  OnActivate = FormActivate
  inherited TBMain: TToolBar
    object NavMain: TDBNavigator
      Left = 0
      Top = 0
      Width = 230
      Height = 22
      ParentShowHint = False
      ShowHint = True
      TabOrder = 0
    end
    object TSepNav: TToolButton
      Left = 230
      Top = 0
      Width = 8
      Style = tbsSeparator
    end
    object TSepTerc: TToolButton
      Left = 238
      Top = 0
      Width = 8
      Style = tbsSeparator
      Visible = False
    end
    object TbuttComp: TToolButton
      Left = 246
      Top = 0
      Visible = False
    end
  end
end
''')

# ------------------------------------------------------------ TFPEdit (rejillas de MaxFactu)
t = renombra(quita_frame(lee('UFRMMantenimientoSimple.pas')))
t = t.replace('unit UFPEdit;', '''unit UFPEdit;

// Mantenimiento con tabla y ficha (en Merge: TFPEdit). Es la base TFRMMantenimientoSimple de MaxFactu pasada a
// formulario: rejilla con filtros por columna, orden por título, totales, columnas fijas y configuración guardada.''', 1)
# CargaAcciones / ExisteBTCategoria / BTClick ya están en TFPEditSinNavegador
for nombre in ('CargaAcciones', 'ExisteBTCategoria', 'BTClick'):
    t = re.sub(r'\n\s*(?:procedure|function) %s[^;]*(?:\([^)]*\))?[^;]*;' % nombre, '', t, count=1)
    t = re.sub(r'\n(?:procedure|function) TFPEdit\.%s\b.*?\nend;\n' % nombre, '\n', t, count=1, flags=re.S)
t = re.sub(r'\n\s*CargaAcciones;', '', t)
t = re.sub(r'\n\s*TBActions: TPanel;', '', t)
t = re.sub(r'\n\s*ALMain: TActionList;', '', t)
t = t.replace('constructor Create(AOwner: TComponent); override;', 'constructor Create(AOwner: TComponent); override;')
escribe('UFPEdit.pas', t)
d = dp.parse(renombra(open(MF + 'UFRMMantenimientoSimple.dfm', encoding='latin-1').read()))
d.kind = 'inherited'
d.children = [c for c in d.children if c.name not in ('TBActions', 'ALMain')]
for n in d.walk():
    if n.cls == 'TDBGrid' or n.cls == 'TDBNavigator':
        n.delete('DataSource')
open(DEST + '/UFPEdit.dfm', 'w', encoding='latin-1').write(dp.dumps(d).replace('\r\n', '\n'))

# ------------------------------------------------------------ TFPEditDetalle
t = renombra(quita_frame(lee('UFRMMantenimientoDetalle.pas')))
escribe('UFPEditDetalle.pas', t)
d = dp.parse(renombra(open(MF + 'UFRMMantenimientoDetalle.dfm', encoding='latin-1').read()))
for n in d.walk():
    if n.cls in ('TDBGrid', 'TDBNavigator') and n.getv('DataSource') in ('DSCabecera',):
        n.delete('DataSource')
open(DEST + '/UFPEditDetalle.dfm', 'w', encoding='latin-1').write(dp.dumps(d).replace('\r\n', '\n'))
print('bases generadas')
