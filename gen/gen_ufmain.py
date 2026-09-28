# -*- coding: utf-8 -*-
"""Genera UFMain.dfm/.pas de Merge13: visual de MaxFactu (FMMain) + las 715 acciones de Merge (FMain)."""
import sys, re, json, collections
sys.path.insert(0, '/home/claude/conv')
import dfmparser as dp

MF = '/home/claude/mf2/maxfactu/UFMMain.dfm'
MERGE = '/home/claude/Merge/UFMain.dfm'
DEST = sys.argv[1]

r = dp.parse(open(MF, encoding='latin-1').read())
r.name, r.cls = 'FMain', 'TFMain'
QUITAR = {'BTVoz', 'BTIniciarVoz', 'ComboBox1', 'TimerVoz', 'FDSPrompt', 'FDScript1', 'Memo1'}
def poda(n):
    n.children = [c for c in n.children if c.name not in QUITAR]
    for c in n.children:
        poda(c)
poda(r)
r.find('ALMain').children = []
r.find('ALAuxiliares').children = []
pm = r.find('PMAuxiliares')
pm.children = [c for c in pm.children if c.name == 'Ayuda1']
r.set('Caption', "'FMain'")

# Acciones de Merge
m = dp.parse(open(MERGE, encoding='latin-1').read())
acciones = []
for n in m.walk():
    if n.cls in ('TAction', 'TLFCategoryAction') and n.parent is not None and n.parent.cls in ('TLFActionList', 'TActionList', 'TActionManager'):
        a = dp.Node('object', n.name, 'TAction')
        for p in ('Category', 'Caption', 'Hint', 'ShortCut'):
            if n.get(p):
                a.set(p, n.get(p))
        acciones.append(a)
r.find('ALMain').children = acciones
open(DEST + '/UFMain.dfm', 'w', encoding='latin-1').write(dp.dumps(r).replace('\r\n', '\n'))

# declaraciones de campos (todo componente con nombre)
campos = []
for n in r.walk():
    if n is r:
        continue
    campos.append('    %s: %s;' % (n.name, n.cls))
json.dump({'campos': campos, 'acciones': [a.name for a in acciones],
           'eventos': sorted({v[0].strip() for n in r.walk() for p, v in n.props if p.startswith('On')})},
          open('/tmp/ufmain_info.json', 'w'))
print(len(acciones), 'acciones de Merge;', len(campos), 'campos')

# ------------------------------------------------------------------ UFMain.pas
met = json.load(open('/tmp/fmmain_metodos.json'))
def M(n):
    return met[n].replace('TFMMain', 'TFMain').replace('FMMain', 'FMain')

form_create = '''procedure TFMain.FormCreate(Sender: TObject);
var
  StileName: string;
begin
  CambiandoEstilo := False;
  if IsAnotherInstanceRunning then
    CloseOtherInstance;
  Log('FMain.FormCreate');
  FiltroAccion := '';
  ComponentesPunto := TList.Create;
  with Entorno do
  begin
    NombrePrograma := 'Merge';
    // Conexion
    BaseDeDatos := LeeDatoIni('Conexion', 'BaseDeDatos', '');
    CBBaseDatos.Text := LeeDatoIni('Conexion', 'BaseDeDatos', '');
    UsuarioBD := LeeDatoIni('Conexion', 'UsuarioBD', '');
    EUsuarioBD.Text := UsuarioBD;
    ClaveBD := LeeDatoIni('Conexion', 'ClaveBD', '');
    if (ClaveBD = '') then
      ClaveBD := LeeDatoIni('Conexion', 'ClaveBDSinCodificar', '')
    else
      ClaveBD := DescodificaClave(Entorno.ClaveBD);
    EClaveBD.Text := ClaveBD;
    RolBD := LeeDatoIni('Conexion', 'RolBD', '');
    ERolBD.Text := RolBD;
    VersionFB := LeeDatoIni('Conexion', 'VersionFB', '');
    CBVersionFB.Text := VersionFB;
    // Sesion
    Usuario := LeeDatoIni('Sesion', 'Usuario', '');
    EUsuario.Text := Usuario;
    EClave.Text := '';
    // Entorno
    Idioma := LeeDatoIni('Entorno', 'Idioma', '');
    Estilo := LeeDatoIni('Entorno', 'Estilo', '');
    Moneda := LeeDatoIni('Entorno', 'Moneda', '');
    FM := TFormManager.Create;
  end;
  Self.Caption := Entorno.NombrePrograma;
  CBEstilo.Items.Clear;
  for StileName in TStyleManager.StyleNames do
    CBEstilo.Items.Add(StileName);
  if Entorno.Estilo > '' then
    CBEstilo.Text := Entorno.Estilo;
  PanelAbierto := -1;
  // Módulos de Merge ya convertidos: su acción del menú abre el formulario (UModulos)
  AsignaModulos(Self);
end;
'''

actualiza = M('ActualizaMenu')
i = actualiza.index('    // Creo paneles de menu')
j = actualiza.index('  SplitViewMenu.Open;')
nuevo_menu = '''    // Creo paneles de menu: una categoría por panel, en el orden de las acciones.
    // Solo se muestran las acciones de los módulos ya convertidos (tienen OnExecute).
    Categorias := TStringList.Create;
    try
      for i := 0 to ALMain.ActionCount - 1 do
        if Assigned(ALMain.Actions[i].OnExecute) and (Categorias.IndexOf(ALMain.Actions[i].Category) < 0) then
          Categorias.Add(ALMain.Actions[i].Category);
      for aGroupIndex := 0 to Categorias.Count - 1 do
      begin
        CP := TCategoryPanel(CPGMenu.CreatePanel(CPGMenu.Owner));
        CP.Caption := Categorias[aGroupIndex];
        CP.Name := 'CP' + NombreValido(Categorias[aGroupIndex]);
        CP.Tag := aGroupIndex + 1;
        CP.ClientHeight := 0;
        CP.OnExpand := CategoryPanelExpand;
        BG := TButtonGroup.Create(CP.Owner);
        BG.Parent := CP;
        BG.Name := 'BG' + NombreValido(Categorias[aGroupIndex]);
        BG.Tag := aGroupIndex + 1;
        BG.Align := alClient;
        BG.ButtonHeight := 32;
        BG.ButtonOptions := [gboFullSize, gboShowCaptions];
        BG.BorderStyle := bsNone;
        BG.Images := IM16;
        BG.OnMouseDown := BGMouseDown;
        for i := 0 to ALMain.ActionCount - 1 do
          if Assigned(ALMain.Actions[i].OnExecute) and (ALMain.Actions[i].Category = Categorias[aGroupIndex]) then
            with BG.Items.Add do
            begin
              Action := ALMain.Actions[i];
              ImageIndex := TAction(ALMain.Actions[i]).ImageIndex;
            end;
        CP.ClientHeight := (BG.Items.Count * BG.ButtonHeight) + 2;
        CP.Collapsed := True;
      end;
    finally
      Categorias.Free;
    end;
  end;

'''
actualiza = actualiza[:i] + nuevo_menu + actualiza[j:]
actualiza = actualiza.replace('  i, MaxGroupIndex, aGroupIndex: Integer;', '  i, aGroupIndex: Integer;\n  Categorias: TStringList;')

bmenu = '''procedure TFMain.BMenuClick(Sender: TObject);
begin
  if SplitViewMenu.Opened then
    SplitViewMenu.Close
  else
    SplitViewMenu.Open;
  FMain.FormResize(FMain);
end;
'''
form_show = M('FormShow').replace("'Versión MAXFACTU : ' + Entorno.VersionMaxFactu + ' Fecha: ' + Entorno.FechaVersionMaxFactu",
                                  "'Merge (Delphi 13)'")

nuevos = '''function NombreValido(const S: string): string;
var
  C: Char;
begin
  Result := '';
  for C := Low(Char) to Low(Char) do ;
  for var k := 1 to Length(S) do
    if CharInSet(S[k], ['A'..'Z', 'a'..'z', '0'..'9', '_']) then
      Result := Result + S[k];
end;

procedure TFMain.EjecutaAccion(Accion: TAction; Filtro: string = '');
begin
  // Igual que en Merge: el formulario lee FiltroAccion al abrirse
  if Accion = nil then
    Exit;
  FiltroAccion := Filtro;
  Accion.Execute;
end;

procedure TFMain.EjecutaAccionFiltro(Accion: TAction; Filtro: string = ''; Ventana: Boolean = False);
begin
  // Estilo MaxFactu: filtro + abrir en ventana (True) o pestaña (False)
  if Accion = nil then
    Exit;
  FiltroAccion := Filtro;
  MostrarEnVentana := Ventana;
  try
    Accion.Execute;
  finally
    FiltroAccion := '';
    MostrarEnVentana := False;
  end;
end;

function TFMain.AbrirEnVentana(Sender: TObject): Boolean;
begin
  // Clic en el icono del menú -> ventana; en el nombre -> pestaña (igual que MaxFactu)
  Result := MostrarEnVentana or EnlaceModal;
  if (Sender is TAction) and (TAction(Sender).ActionComponent is TButtonGroup) then
    Result := Result or TButtonGroup(TAction(Sender).ActionComponent).Items[0].GetVentana;
end;

procedure TFMain.AddComponentePunto(Componente: TComponent);
begin
  if ComponentesPunto.IndexOf(Componente) = -1 then
    ComponentesPunto.Add(Componente);
end;

procedure TFMain.DelComponentePunto(Componente: TComponent);
begin
  ComponentesPunto.Remove(Componente);
end;

'''

extra_pub = '''    // ---- API de FMain de Merge ----
    FiltroAccion: string;
    MostrarEnVentana: Boolean;
    EnlaceDatos: Variant;
    EnlaceModal: Boolean;
    EnlaceInstancias: Boolean;
    EnlaceCrea: Boolean;
    sourcecall: Boolean;
    sourcecallTer: Boolean;
    autproveedor, autcliente, autacreedor, autagente: Boolean;
    ComponentesPunto: TList;
    PanelAbierto: Integer;
    procedure EjecutaAccion(Accion: TAction; Filtro: string = '');
    procedure EjecutaAccionFiltro(Accion: TAction; Filtro: string = ''; Ventana: Boolean = False);
    function AbrirEnVentana(Sender: TObject): Boolean;
    procedure AddComponentePunto(Componente: TComponent);
    procedure DelComponentePunto(Componente: TComponent);
    procedure ActualizaMenu;
    procedure TWinControlMouseEnter(Sender: TObject);
    procedure TWinControlMouseLeave(Sender: TObject);
    procedure TWinControlMouseUp(Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer);
    function IsAnotherInstanceRunning: Boolean;
    procedure CloseOtherInstance;
    procedure DateTimePickerKeyDown(Sender: TObject; var Key: Word; Shift: TShiftState);
    procedure DTPCloseUp(Sender: TObject);
    procedure DateTimePickerEnter(Sender: TObject);
'''
info = json.load(open('/tmp/ufmain_info.json'))
eventos_decl = {
 'FormCreate': 'procedure FormCreate(Sender: TObject);', 'FormClose': 'procedure FormClose(Sender: TObject; var Action: TCloseAction);',
 'FormResize': 'procedure FormResize(Sender: TObject);', 'FormShow': 'procedure FormShow(Sender: TObject);',
 'PCMainMouseDown': 'procedure PCMainMouseDown(Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer);',
 'EClaveKeyPress': 'procedure EClaveKeyPress(Sender: TObject; var Key: Char);'}
decl_ev = '\n'.join('    ' + eventos_decl.get(e, 'procedure %s(Sender: TObject);' % e) for e in info['eventos'])
pas = '''unit UFMain;

// Formulario principal de Merge en Delphi 13.
// Visual y funcionamiento de MaxFactu (menú lateral por categorías, pestañas / ventanas, panel de sistema)
// con la API de FMain de Merge (acciones con los mismos nombres, EjecutaAccion, FiltroAccion, Enlace*...).
// Las 715 acciones de Merge están en ALMain; el menú solo muestra las de los módulos ya convertidos.

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, System.DateUtils,
  Vcl.Graphics, Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.ExtCtrls, Vcl.WinXCtrls, Vcl.StdCtrls, Vcl.ComCtrls,
  Vcl.ButtonGroup, Vcl.Menus, Vcl.ActnList, Vcl.ActnMan, Vcl.PlatformDefaultStyleActnCtrls, System.Actions,
  System.ImageList, Vcl.ImgList, Vcl.Themes, Vcl.Styles, Vcl.ToolWin, Vcl.CategoryButtons, Vcl.Imaging.pngimage,
  Vcl.BaseImageCollection, Vcl.ImageCollection, Vcl.VirtualImageList, UFormManager, UCustomProperties,
  Vcl.DBCtrls, Vcl.Mask, Data.DB, UDateTimePickerHelper, System.UITypes, frxClass,
  FireDAC.Stan.Intf, FireDAC.Stan.Option, FireDAC.Stan.Error, FireDAC.Comp.Client, FireDAC.Comp.Script, FireDAC.UI.Intf,
  FireDAC.Stan.Async, FireDAC.Comp.ScriptCommands, FireDAC.Stan.Util;

type
  TGrpButtonItemHelper = class helper for Vcl.ButtonGroup.TGrpButtonItem
  private
    function GetCustomProperties: TCustomProperties;
  public
    procedure SetVentana(const Value: Boolean);
    function GetVentana: Boolean;
    property CustomProperties: TCustomProperties read GetCustomProperties;
    property Ventana: Boolean read GetVentana write SetVentana;
  end;

  TFMain = class(TForm)
%s
%s
    procedure BGMouseDown(Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer);
    procedure CategoryPanelExpand(Sender: TObject);
    procedure MenuItemClick(Sender: TObject);
  private
    procedure WMUser(var Msg: TMessage); message WM_USER + 1;
    function MuestraLogin: TModalResult;
    procedure CrearMenuVentanas;
    procedure CerrarTodasLasVentanas;
  public
%s  end;

var
  FMain: TFMain;
  FM: TFormManager;
  CambiandoEstilo: Boolean;
  FCustomProperties: TCustomProperties;

implementation

{$R *.dfm}

uses
  UEntorno, UDMMain, UUtiles, ULog, UFMLogin, UFMAcerca, UModulos, gnugettext, UMensajesDeError;

%s
%s
%s
%s
%s
end.
''' % ('\n'.join(info['campos']), decl_ev, extra_pub, nuevos, form_create, actualiza, bmenu, form_show)
resto = ['FormClose', 'FormResize', 'WMUser', 'MuestraLogin', 'PCMainMouseDown', 'BAuxiliaresClick', 'BConectarClick',
         'BModificarEntornoClick', 'BSesionClick', 'BSistemaClick', 'BVentanasClick', 'CrearMenuVentanas',
         'CerrarTodasLasVentanas', 'MenuItemClick', 'CBBaseDatosChange', 'CBEjercicioChange', 'CBEmpresaChange',
         'CBEstiloChange', 'CBIdiomaChange', 'TWinControlMouseEnter', 'TWinControlMouseLeave', 'TWinControlMouseUp',
         'CategoryPanelExpand', 'EClaveKeyPress', 'Acercade1Click', 'BGMouseDown', 'GetCustomProperties', 'SetVentana',
         'GetVentana', 'DateTimePickerKeyDown', 'DTPCloseUp', 'DateTimePickerEnter', 'IsAnotherInstanceRunning',
         'CloseOtherInstance']
cuerpos = '\n'.join(M(n) for n in resto)
# la búsqueda de otra instancia no debe encontrar la propia ventana principal
cuerpos = cuerpos.replace('(WindowHandle <> 0) and (WindowHandle <> Application.Handle)',
                          '(WindowHandle <> 0) and (WindowHandle <> Application.Handle) and (WindowHandle <> Self.Handle)')
pas = pas.replace('\nend.\n', '\n' + cuerpos + '\nend.\n')
open(DEST + '/UFMain.pas', 'w', encoding='utf-8-sig').write(pas)
print('UFMain.pas', len(pas.splitlines()), 'líneas')
