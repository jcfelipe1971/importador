unit UBuscadorCampo;

// Sustituto de TLFDBEditFind2000 / TLFEditFind2000 de Merge sobre controles VCL estándar (TDBEdit / TEdit).
// Reproduce el comportamiento de Merge:
//   - F3 o doble clic abren el buscador de MaxFactu (TFMBuscar).
//   - Al salir del control se comprueba que el código existe en la tabla (como TFIBDBEditFind.DoExit):
//       existe    -> OnExiste
//       no existe -> OnNoExiste y se abre el buscador (salvo SalirSiNoExiste = True)
//   - Los eventos de Merge se conservan con la misma firma (TNotifyEvent) y Sender = el control de edición:
//       OnVerificacion (antes de comprobar), OnBusqueda (antes de abrir el buscador), OnExiste, OnNoExiste.
//   - CondicionBusqueda: condición SQL adicional, como la propiedad de Merge.
// Los eventos OnKeyDown / OnDblClick / OnExit que ya tuviera el control se siguen ejecutando.

interface

uses
  System.SysUtils, System.Classes, System.Variants, Winapi.Windows, Winapi.Messages, Vcl.Controls, Vcl.StdCtrls,
  Vcl.DBCtrls, Vcl.Forms, Data.DB, FireDAC.Stan.Param, FireDAC.Comp.Client;

type
  TBuscadorCampo = class(TComponent)
  private
    FEdit: TCustomEdit;
    FTabla: string;
    FCampo: string;
    FCampoDevolver: string;
    FCampos: TArray<string>;
    FFiltroEntorno: string;
    FCondicionBusqueda: string;
    FSalirSiNoExiste: Boolean;
    FAutoCambiarFoco: Boolean;
    FOldKeyDown: TKeyEvent;
    FOldDblClick: TNotifyEvent;
    FOldExit: TNotifyEvent;
    FOnVerificacion: TNotifyEvent;
    FOnBusqueda: TNotifyEvent;
    FOnExiste: TNotifyEvent;
    FOnNoExiste: TNotifyEvent;
    FOnSeleccion: TNotifyEvent;
    FAccion: TBasicAction;
    FValidando: Boolean;
    procedure KeyDownEdit(Sender: TObject; var Key: Word; Shift: TShiftState);
    procedure DblClickEdit(Sender: TObject);
    procedure ExitEdit(Sender: TObject);
    procedure Engancha;
    function Condiciones: string;
    function BuscarEnDataSet(DS: TDataSource): Boolean;
    function BuscarLibre: Boolean;
    procedure Dispara(Evento: TNotifyEvent);
  protected
    procedure Notification(AComponent: TComponent; Operation: TOperation); override;
  public
    class function Crea(AOwner: TComponent; AEdit: TDBEdit; const Tabla, Campo, CampoDevolver: string;
      const Campos: array of string; const FiltroEntorno: string; const Condicion: string = ''): TBuscadorCampo;
    class function CreaLibre(AOwner: TComponent; AEdit: TEdit; const Tabla, CampoDevolver: string;
      const Campos: array of string; const FiltroEntorno: string; const Condicion: string = ''): TBuscadorCampo;
    function Buscar: Boolean;
    function Existe: Boolean;
    // Métodos de EditFind2000 de Merge
    procedure SetBufferText(const Texto: string);
    procedure ClearBufferText;
    property Edit: TCustomEdit read FEdit;
    property Tabla: string read FTabla write FTabla;
    property CampoDevolver: string read FCampoDevolver write FCampoDevolver;
    property CondicionBusqueda: string read FCondicionBusqueda write FCondicionBusqueda;
    property SalirSiNoExiste: Boolean read FSalirSiNoExiste write FSalirSiNoExiste;
    property AutoCambiarFoco: Boolean read FAutoCambiarFoco write FAutoCambiarFoco;
    // Acción de alta rápida (Accion de EditFind2000): se ejecuta si el código no existe y no se elige ninguno
    property Accion: TBasicAction read FAccion write FAccion;
    property OnVerificacion: TNotifyEvent read FOnVerificacion write FOnVerificacion;
    property OnBusqueda: TNotifyEvent read FOnBusqueda write FOnBusqueda;
    property OnExiste: TNotifyEvent read FOnExiste write FOnExiste;
    property OnNoExiste: TNotifyEvent read FOnNoExiste write FOnNoExiste;
    property OnSeleccion: TNotifyEvent read FOnSeleccion write FOnSeleccion;
  end;

implementation

uses UFMBuscar, UEntorno, UDMMain;

type
  TEditAccess = class(TCustomEdit);

function CopiaCampos(const Campos: array of string): TArray<string>;
var
  i: Integer;
begin
  SetLength(Result, Length(Campos));
  for i := 0 to High(Campos) do
    Result[i] := Campos[i];
end;

{ TBuscadorCampo }

class function TBuscadorCampo.Crea(AOwner: TComponent; AEdit: TDBEdit; const Tabla, Campo, CampoDevolver: string;
  const Campos: array of string; const FiltroEntorno: string; const Condicion: string): TBuscadorCampo;
begin
  Result := TBuscadorCampo.Create(AOwner);
  Result.FEdit := AEdit;
  Result.FTabla := Trim(Tabla);
  Result.FCampo := Campo;
  Result.FCampoDevolver := CampoDevolver;
  Result.FCampos := CopiaCampos(Campos);
  Result.FFiltroEntorno := FiltroEntorno;
  Result.FCondicionBusqueda := Condicion;
  Result.Engancha;
end;

class function TBuscadorCampo.CreaLibre(AOwner: TComponent; AEdit: TEdit; const Tabla, CampoDevolver: string;
  const Campos: array of string; const FiltroEntorno: string; const Condicion: string): TBuscadorCampo;
begin
  Result := TBuscadorCampo.Create(AOwner);
  Result.FEdit := AEdit;
  Result.FTabla := Trim(Tabla);
  Result.FCampo := '';
  Result.FCampoDevolver := CampoDevolver;
  Result.FCampos := CopiaCampos(Campos);
  Result.FFiltroEntorno := FiltroEntorno;
  Result.FCondicionBusqueda := Condicion;
  Result.Engancha;
end;

procedure TBuscadorCampo.Engancha;
begin
  FEdit.FreeNotification(Self);
  FOldKeyDown := TEditAccess(FEdit).OnKeyDown;
  FOldDblClick := TEditAccess(FEdit).OnDblClick;
  FOldExit := TEditAccess(FEdit).OnExit;
  TEditAccess(FEdit).OnKeyDown := KeyDownEdit;
  TEditAccess(FEdit).OnDblClick := DblClickEdit;
  TEditAccess(FEdit).OnExit := ExitEdit;
  if FEdit.Hint = '' then
    FEdit.Hint := 'F3 o doble clic para buscar';
  FEdit.ShowHint := True;
end;

procedure TBuscadorCampo.Notification(AComponent: TComponent; Operation: TOperation);
begin
  inherited;
  if (Operation = opRemove) and (AComponent = FEdit) then
    FEdit := nil;
end;

procedure TBuscadorCampo.Dispara(Evento: TNotifyEvent);
begin
  // En Merge el Sender de estos eventos era el propio control de edición
  if Assigned(Evento) and Assigned(FEdit) then
    Evento(FEdit);
end;

function TBuscadorCampo.Condiciones: string;
var
  Entorno_: string;
begin
  // Filtro de entorno (empresa/ejercicio/canal/serie) + CondicionBusqueda, sin AND inicial
  Entorno_ := '';
  if (FFiltroEntorno <> '') and (FFiltroEntorno <> '0000') then
    Entorno_ := FiltroEntorno(FFiltroEntorno);
  Result := Entorno_;
  if Trim(FCondicionBusqueda) <> '' then
    if Result <> '' then
      Result := Result + ' AND (' + FCondicionBusqueda + ')'
    else
      Result := '(' + FCondicionBusqueda + ')';
end;

procedure TBuscadorCampo.KeyDownEdit(Sender: TObject; var Key: Word; Shift: TShiftState);
begin
  if Assigned(FOldKeyDown) then
    FOldKeyDown(Sender, Key, Shift);
  if (Key = VK_F3) and (Shift = []) then
  begin
    Key := 0;
    Buscar;
  end;
end;

procedure TBuscadorCampo.DblClickEdit(Sender: TObject);
begin
  if Assigned(FOldDblClick) then
    FOldDblClick(Sender);
  Buscar;
end;

procedure TBuscadorCampo.ExitEdit(Sender: TObject);
var
  EnEdicion: Boolean;
begin
  if Assigned(FOldExit) then
    FOldExit(Sender);
  if FValidando or (FEdit = nil) or (Trim(FEdit.Text) = '') then
    Exit;
  // Como TFIBDBEditFind.DoExit: solo se valida si el dataset está en edición
  EnEdicion := not (FEdit is TDBEdit) or (Assigned(TDBEdit(FEdit).DataSource) and
    (TDBEdit(FEdit).DataSource.State in [dsEdit, dsInsert]));
  if not EnEdicion then
    Exit;
  FValidando := True;
  try
    if Existe then
      Dispara(FOnExiste)
    else
    begin
      Dispara(FOnNoExiste);
      if not FSalirSiNoExiste then
      begin
        if not Buscar and Assigned(FAccion) then
          FAccion.Execute;
        if FEdit.CanFocus then
          FEdit.SetFocus;
      end;
    end;
  finally
    FValidando := False;
  end;
end;

function TBuscadorCampo.Existe: Boolean;
var
  Q: TFDQuery;
  Cond: string;
begin
  Dispara(FOnVerificacion);
  Result := False;
  if (FEdit = nil) or (FTabla = '') or (FCampoDevolver = '') then
    Exit(True);
  Q := TFDQuery.Create(nil);
  try
    Q.Connection := DMMain.DB;
    Q.SQL.Text := 'SELECT COUNT(*) FROM ' + FTabla + ' WHERE ' + FCampoDevolver + ' = :VALOR';
    Cond := Condiciones;
    if Cond <> '' then
      Q.SQL.Add(' AND ' + Cond);
    Q.ParamByName('VALOR').AsString := Trim(FEdit.Text);
    Q.Open;
    Result := Q.Fields[0].AsInteger > 0;
    Q.Close;
  finally
    Q.Free;
  end;
end;

procedure TBuscadorCampo.SetBufferText(const Texto: string);
begin
  if Assigned(FEdit) then
    FEdit.Text := Texto;
end;

procedure TBuscadorCampo.ClearBufferText;
begin
  // En Merge vaciaba el texto tecleado pendiente de buscar; aquí no hay buffer aparte
end;

function TBuscadorCampo.Buscar: Boolean;
begin
  Result := False;
  if (FEdit = nil) or (FTabla = '') then
    Exit;
  Dispara(FOnBusqueda);
  if (FEdit is TDBEdit) and Assigned(TDBEdit(FEdit).DataSource) and
    Assigned(TDBEdit(FEdit).DataSource.DataSet) then
  begin
    if TDBEdit(FEdit).ReadOnly or not TDBEdit(FEdit).DataSource.DataSet.CanModify then
      Exit;
    Result := BuscarEnDataSet(TDBEdit(FEdit).DataSource);
  end
  else
    Result := BuscarLibre;
  if Result then
  begin
    Dispara(FOnExiste);
    if Assigned(FOnSeleccion) then
      FOnSeleccion(Self);
    if FAutoCambiarFoco and Assigned(FEdit.Parent) then
      if GetParentForm(FEdit) <> nil then
        GetParentForm(FEdit).Perform(WM_NEXTDLGCTL, 0, 0);
  end;
end;

function TBuscadorCampo.BuscarEnDataSet(DS: TDataSource): Boolean;
var
  F: TFMBuscar;
  Antes: Variant;
begin
  Antes := DS.DataSet.FieldByName(FCampo).Value;
  F := TFMBuscar.Create(nil);
  try
    // TFMBuscar usa SubConsulta en lugar del filtro de entorno cuando se indica: se le pasa todo junto
    F.ConfigurarBusqueda(DS, FTabla, FCampo, FCampoDevolver, FCampos, FEdit.Text, '', Condiciones);
    F.ShowModal;
  finally
    F.Free;
  end;
  Result := not VarSameValue(Antes, DS.DataSet.FieldByName(FCampo).Value);
end;

function TBuscadorCampo.BuscarLibre: Boolean;
var
  F: TFMBuscar;
  MT: TFDMemTable;
  DS: TDataSource;
begin
  // TFMBuscar escribe el resultado en un dataset: para un TEdit sin datos se usa una tabla en memoria
  Result := False;
  MT := TFDMemTable.Create(nil);
  DS := TDataSource.Create(nil);
  F := TFMBuscar.Create(nil);
  try
    MT.FieldDefs.Add('VALOR', ftString, 255);
    MT.CreateDataSet;
    MT.Append;
    DS.DataSet := MT;
    F.ConfigurarBusqueda(DS, FTabla, 'VALOR', FCampoDevolver, FCampos, FEdit.Text, '', Condiciones);
    F.ShowModal;
    if not MT.FieldByName('VALOR').IsNull then
    begin
      FEdit.Text := MT.FieldByName('VALOR').AsString;
      Result := True;
    end;
  finally
    F.Free;
    DS.Free;
    MT.Free;
  end;
end;

end.
