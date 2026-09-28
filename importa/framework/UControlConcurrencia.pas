unit UControlConcurrencia;

// Control de concurrencia para TFDQuery, equivalente al que hacía TFIBTableSet en Merge:
//   - cmSelectWithLock: BloqOpt=True + TablasBloqueo/CamposBloqueo -> SELECT ... WITH LOCK en tablas base
//   - cmUpdate: control por defecto de TFIBTableSet -> UPDATE <tabla> SET pk=pk WHERE pk=...
// El bloqueo se toma al entrar en edición dentro de la UpdateTransaction del dataset, y se libera
// con Commit en AfterPost o Rollback en AfterCancel. Los eventos que ya tuviera el dataset se respetan.

interface

uses
  System.SysUtils, System.Classes, System.Generics.Collections, Data.DB,
  FireDAC.Stan.Intf, FireDAC.Stan.Param, FireDAC.Stan.Error, FireDAC.Comp.Client, FireDAC.Comp.DataSet;

type
  TModoConcurrencia = (cmSelectWithLock, cmUpdate);

  TControlConcurrencia = class(TComponent)
  private
    FDataSet: TFDQuery;
    FSentencias: TObjectList<TFDQuery>;
    FBeforeEdit: TDataSetNotifyEvent;
    FAfterPost: TDataSetNotifyEvent;
    FAfterCancel: TDataSetNotifyEvent;
    FIniciadaPorMi: Boolean;
    function Transaccion: TFDCustomTransaction;
    procedure DoBeforeEdit(DataSet: TDataSet);
    procedure DoAfterPost(DataSet: TDataSet);
    procedure DoAfterCancel(DataSet: TDataSet);
    procedure Libera(Confirmar: Boolean);
  public
    constructor Create(ADataSet: TFDQuery); reintroduce;
    destructor Destroy; override;
    procedure Anyade(const Tabla, Campos: string; Modo: TModoConcurrencia);
    class procedure Registra(ADataSet: TFDQuery; const Tabla, Campos: string;
      Modo: TModoConcurrencia = cmSelectWithLock);
  end;

implementation

uses gnugettext;

{ TControlConcurrencia }

constructor TControlConcurrencia.Create(ADataSet: TFDQuery);
begin
  inherited Create(ADataSet);
  FDataSet := ADataSet;
  FSentencias := TObjectList<TFDQuery>.Create(True);
  // Encadenar con los eventos que vienen del DFM
  FBeforeEdit := ADataSet.BeforeEdit;
  FAfterPost := ADataSet.AfterPost;
  FAfterCancel := ADataSet.AfterCancel;
  ADataSet.BeforeEdit := DoBeforeEdit;
  ADataSet.AfterPost := DoAfterPost;
  ADataSet.AfterCancel := DoAfterCancel;
end;

destructor TControlConcurrencia.Destroy;
begin
  FSentencias.Free;
  inherited;
end;

class procedure TControlConcurrencia.Registra(ADataSet: TFDQuery; const Tabla, Campos: string;
  Modo: TModoConcurrencia);
var
  i: Integer;
  CC: TControlConcurrencia;
begin
  CC := nil;
  for i := 0 to ADataSet.ComponentCount - 1 do
    if ADataSet.Components[i] is TControlConcurrencia then
      CC := TControlConcurrencia(ADataSet.Components[i]);
  if CC = nil then
    CC := TControlConcurrencia.Create(ADataSet);
  CC.Anyade(Tabla, Campos, Modo);
end;

procedure TControlConcurrencia.Anyade(const Tabla, Campos: string; Modo: TModoConcurrencia);
var
  Q: TFDQuery;
  Lista: TStringList;
  i: Integer;
  Where, SetPk: string;
begin
  if Trim(Tabla) = '' then
    Exit;
  Lista := TStringList.Create;
  try
    Lista.CommaText := StringReplace(Campos, ';', ',', [rfReplaceAll]);
    Where := '';
    SetPk := '';
    for i := 0 to Lista.Count - 1 do
      if Trim(Lista[i]) <> '' then
      begin
        if Where <> '' then
        begin
          Where := Where + ' AND ';
          SetPk := SetPk + ', ';
        end;
        Where := Where + Format('%0:s = :%0:s', [Trim(Lista[i])]);
        SetPk := SetPk + Format('%0:s = :%0:s', [Trim(Lista[i])]);
      end;
  finally
    Lista.Free;
  end;
  Q := TFDQuery.Create(nil);
  Q.Connection := FDataSet.Connection;
  case Modo of
    cmSelectWithLock:
      Q.SQL.Text := 'SELECT * FROM ' + Tabla + ' WHERE ' + Where + ' WITH LOCK';
    cmUpdate:
      Q.SQL.Text := 'UPDATE ' + Tabla + ' SET ' + SetPk + ' WHERE ' + Where;
  end;
  Q.Tag := Ord(Modo);
  FSentencias.Add(Q);
end;

function TControlConcurrencia.Transaccion: TFDCustomTransaction;
begin
  Result := FDataSet.UpdateTransaction;
  if Result = nil then
    Result := FDataSet.Transaction;
end;

procedure TControlConcurrencia.DoBeforeEdit(DataSet: TDataSet);
var
  T: TFDCustomTransaction;
  Q: TFDQuery;
  i: Integer;
begin
  if Assigned(FBeforeEdit) then
    FBeforeEdit(DataSet);
  T := Transaccion;
  if (T = nil) or (FSentencias.Count = 0) then
    Exit;
  FIniciadaPorMi := not T.Active;
  if FIniciadaPorMi then
    T.StartTransaction;
  try
    for Q in FSentencias do
    begin
      Q.Transaction := T;
      for i := 0 to Q.Params.Count - 1 do
        Q.Params[i].Value := DataSet.FieldByName(Q.Params[i].Name).Value;
      if TModoConcurrencia(Q.Tag) = cmSelectWithLock then
      begin
        Q.Open;
        Q.Close;
      end
      else
        Q.ExecSQL;
    end;
  except
    on E: EFDDBEngineException do
    begin
      if FIniciadaPorMi and T.Active then
        T.Rollback;
      FIniciadaPorMi := False;
      raise EDatabaseError.Create(_('El registro está siendo modificado por otro usuario. Inténtelo más tarde.'));
    end;
  end;
end;

procedure TControlConcurrencia.Libera(Confirmar: Boolean);
var
  T: TFDCustomTransaction;
begin
  T := Transaccion;
  if FIniciadaPorMi and (T <> nil) and T.Active then
    if Confirmar then
      T.Commit
    else
      T.Rollback;
  FIniciadaPorMi := False;
end;

procedure TControlConcurrencia.DoAfterPost(DataSet: TDataSet);
begin
  // En Merge (TFIBTableSet.AutoCommit) el commit se hacía antes del AfterPost del usuario
  Libera(True);
  if Assigned(FAfterPost) then
    FAfterPost(DataSet);
end;

procedure TControlConcurrencia.DoAfterCancel(DataSet: TDataSet);
begin
  Libera(False);
  if Assigned(FAfterCancel) then
    FAfterCancel(DataSet);
end;

end.
