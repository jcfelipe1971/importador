unit UAuxMerge;

// Funciones auxiliares para el código convertido desde Merge (Delphi 6) al estilo MaxFactu.
// Aquí va lo que Merge tenía en TDMMain, REntorno, UFormGest o en los datasets FIB y que MaxFactu no tiene.
// Son funciones normales (sin class helpers): el conversor reescribe las llamadas, por ejemplo
//   DMMain.TituloSituacionProduccion[Situacion]  ->  TituloSituacionProduccion(Situacion)
//   QTabla.Ordenar('CAMPO')                      ->  Ordenar(QTabla, 'CAMPO')
//   REntorno.DatosAbiertos                       ->  EntornoMerge.DatosAbiertos

interface

uses
  System.SysUtils, System.Classes, System.Variants, Winapi.Windows, Winapi.ShellAPI,
  Vcl.Forms, Vcl.Controls, Vcl.Dialogs, Vcl.ActnList, Data.DB,
  FireDAC.Stan.Intf, FireDAC.Stan.Param, FireDAC.Comp.Client, FireDAC.DApt;

type
  // Antes en UDMMain de Merge
  TParametroFiltrado = class(TObject)
  public
    Filtro: string;
    SQLBase: TStrings;
    Tabla: TFDQuery;
  end;

  // Datos de REntorno de Merge que no existen en TEntorno de MaxFactu
  TEntornoMerge = record
    DatosAbiertos: Boolean;
    Delegacion: string;
    SerieRestringida: string;
    ColorEnlaceActivo: Integer;   // Merge: COLOR_ENLACE_ACTIVO del usuario
    ColorCampoID: Integer;        // Merge: COLOR_CAMPO_ID del usuario
    ColorEdtFnd: Integer;
    DirectorioComunicaciones: string;
  end;

var
  EntornoMerge: TEntornoMerge;
  // True solo en el programa de prueba de carga: los frames convertidos cargan su DFM y no ejecutan
  // el código de Merge (que necesita base de datos y sesión iniciada).
  ModoPruebaCarga: Boolean = False;

// Traza en fichero (DMMain.Log de Merge): <exe>\Log\Merge_aaaammdd.log
procedure LogMerge(const Texto: string);

// Nivel de acceso del usuario conectado (REntorno.Nivel / REntorno.Restriccion en Merge)
function NivelUsuario: Integer;

// ---- Métodos de TFIBTableSet de Merge ----
function OrdenadoPor(Q: TFDQuery): string;
procedure Ordenar(Q: TFDQuery; const Campo: string);
procedure DameFiltroSelect(Q: TFDQuery; Destino: TStrings);

// ---- Cachés de títulos que Merge cargaba en TDMMain ----
function TituloEstado(Estado: Integer): string;
function TituloSituacionProduccion(Situacion: Integer): string;
function TituloUnidadMedida: TStrings;
function TituloPeriodoFacturacion: TStrings;
procedure RecargaTitulos;

// ---- Otras funciones de TDMMain de Merge ----
procedure FiltraRO(Tabla: TFDQuery; Filtro: string = '000000'; Abre: Boolean = True);
procedure FiltraSQL(Parametro: TParametroFiltrado; Abrir: Boolean = True);
function MinTercero: Integer;
procedure AbrirArchivo(const Archivo: string);
function DameDirectorioComunicaciones(const Tipo: string): string;
function DameDirectorioCodCliPro(const Tipo: string; CodCliPro: Integer): string;

// ---- UFormGest de Merge ----
procedure AbreData(Clase: TComponentClass; var Referencia);
procedure AbreDataVarias(Clase: TComponentClass; var Referencia; Padre: TComponent);
procedure CierraData(var DModuloPar);
procedure AbreForm(Clase: TFormClass; var Referencia; Sender: TObject = nil);
procedure CierraForm(var Form);
function AbreFrame(Clase: TClass; const Titulo: string; Ventana: Boolean = False): TFrame;

implementation

uses
  gnugettext, UEntorno, UDMMain, UUtiles, UFMMain;

var
  GTituloEstado: TStringList = nil;
  GTituloSituacionProduccion: TStringList = nil;
  GTituloUnidadMedida: TStringList = nil;
  GTituloPeriodoFacturacion: TStringList = nil;
  GEmpresaPeriodos: Integer = -1;
  GNivelUsuario: Integer = -1;
  GNivelIdUsuario: Integer = -1;

procedure LogMerge(const Texto: string);
var
  Dir: string;
  F: TextFile;
begin
  try
    Dir := ExtractFilePath(ParamStr(0)) + 'Log';
    ForceDirectories(Dir);
    AssignFile(F, Dir + '\Merge_' + FormatDateTime('yyyymmdd', Now) + '.log');
    if FileExists(Dir + '\Merge_' + FormatDateTime('yyyymmdd', Now) + '.log') then
      Append(F)
    else
      Rewrite(F);
    try
      Writeln(F, FormatDateTime('hh:nn:ss.zzz', Now) + '  ' + Texto);
    finally
      CloseFile(F);
    end;
  except
    // la traza nunca debe interrumpir el programa
  end;
end;

function NivelUsuario: Integer;
var
  Q: TFDQuery;
begin
  // Se lee de SYS_USUARIOS la primera vez (y si cambia el usuario conectado)
  if (GNivelUsuario < 0) or (GNivelIdUsuario <> Entorno.IdUsuario) then
  begin
    Q := TFDQuery.Create(nil);
    try
      Q.Connection := DMMain.DB;
      Q.SQL.Text := 'SELECT NIVEL FROM SYS_USUARIOS WHERE USUARIO = :USUARIO';
      Q.ParamByName('USUARIO').AsInteger := Entorno.IdUsuario;
      Q.Open;
      GNivelUsuario := Q.Fields[0].AsInteger;
      GNivelIdUsuario := Entorno.IdUsuario;
      Q.Close;
    finally
      Q.Free;
    end;
  end;
  Result := GNivelUsuario;
end;

{ ---------------------------------------------------------------------------------------------- }
{ Métodos de TFIBTableSet                                                                        }
{ ---------------------------------------------------------------------------------------------- }

function OrdenadoPor(Q: TFDQuery): string;
var
  i, j, p: Integer;
begin
  Result := '';
  for i := Q.SQL.Count - 1 downto 0 do
  begin
    p := Pos('ORDER BY', UpperCase(Q.SQL[i]));
    if p > 0 then
    begin
      Result := Copy(Q.SQL[i], p + Length('ORDER BY'), MaxInt);
      for j := i + 1 to Q.SQL.Count - 1 do
        Result := Result + ' ' + Q.SQL[j];
      Break;
    end;
  end;
  Result := Trim(Result);
end;

procedure Ordenar(Q: TFDQuery; const Campo: string);
var
  i, j, p: Integer;
  EstabaActivo: Boolean;
  Valores: array of Variant;
begin
  // Sustituye o añade el ORDER BY conservando los valores de los parámetros
  EstabaActivo := Q.Active;
  SetLength(Valores, Q.Params.Count);
  for i := 0 to Q.Params.Count - 1 do
    Valores[i] := Q.Params[i].Value;
  if EstabaActivo then
    Q.Close;
  Q.SQL.BeginUpdate;
  try
    for i := Q.SQL.Count - 1 downto 0 do
    begin
      p := Pos('ORDER BY', UpperCase(Q.SQL[i]));
      if p > 0 then
      begin
        for j := Q.SQL.Count - 1 downto i + 1 do
          Q.SQL.Delete(j);
        Q.SQL[i] := Copy(Q.SQL[i], 1, p - 1);
        if Trim(Q.SQL[i]) = '' then
          Q.SQL.Delete(i);
        Break;
      end;
    end;
    if Campo <> '' then
      Q.SQL.Add('ORDER BY ' + Campo);
  finally
    Q.SQL.EndUpdate;
  end;
  for i := 0 to Q.Params.Count - 1 do
    if i <= High(Valores) then
      Q.Params[i].Value := Valores[i];
  if EstabaActivo then
    Q.Open;
end;

procedure DameFiltroSelect(Q: TFDQuery; Destino: TStrings);
var
  i, p: Integer;
  Linea: string;
  Dentro: Boolean;
begin
  // Condiciones del WHERE sin el ORDER BY
  Dentro := False;
  for i := 0 to Q.SQL.Count - 1 do
  begin
    Linea := Q.SQL[i];
    if not Dentro then
    begin
      p := Pos('WHERE', UpperCase(Linea));
      if p = 0 then
        Continue;
      Dentro := True;
      Linea := Copy(Linea, p + 5, MaxInt);
    end;
    p := Pos('ORDER BY', UpperCase(Linea));
    if p > 0 then
    begin
      Linea := Copy(Linea, 1, p - 1);
      if Trim(Linea) <> '' then
        Destino.Add(Linea);
      Break;
    end;
    if Trim(Linea) <> '' then
      Destino.Add(Linea);
  end;
end;

{ ---------------------------------------------------------------------------------------------- }
{ Cachés de títulos (mismas consultas que TDMMain de Merge)                                      }
{ ---------------------------------------------------------------------------------------------- }

function CargaLista(var Lista: TStringList; const aSQL: string): TStringList;
var
  Q: TFDQuery;
begin
  if Lista = nil then
  begin
    Lista := TStringList.Create;
    Q := TFDQuery.Create(nil);
    try
      Q.Connection := DMMain.DB;
      Q.SQL.Text := aSQL;
      Q.Open;
      while not Q.Eof do
      begin
        Lista.Values[Q.Fields[0].AsString] := Q.Fields[1].AsString;
        Q.Next;
      end;
      Q.Close;
    finally
      Q.Free;
    end;
  end;
  Result := Lista;
end;

function TituloEstado(Estado: Integer): string;
begin
  Result := CargaLista(GTituloEstado, 'SELECT ESTADO, TITULO FROM SYS_GES_ESTADOS').Values[IntToStr(Estado)];
  if Result = '' then
    Result := '-';
end;

function TituloSituacionProduccion(Situacion: Integer): string;
begin
  Result := CargaLista(GTituloSituacionProduccion,
    'SELECT ESTADO, TITULO FROM PRO_SYS_ESTADO ORDER BY ESTADO').Values[IntToStr(Situacion)];
  if Result = '' then
    Result := '-';
end;

function TituloUnidadMedida: TStrings;
begin
  Result := CargaLista(GTituloUnidadMedida, 'SELECT TIPO, TITULO FROM SYS_UNIDADES_ARTICULOS ORDER BY TIPO');
end;

function TituloPeriodoFacturacion: TStrings;
begin
  if GEmpresaPeriodos <> Entorno.Empresa then
  begin
    FreeAndNil(GTituloPeriodoFacturacion);
    GEmpresaPeriodos := Entorno.Empresa;
  end;
  Result := CargaLista(GTituloPeriodoFacturacion,
    'SELECT PERIODO, TITULO FROM EMP_PERIODOS_FACTURACION WHERE EMPRESA = ' + IntToStr(Entorno.Empresa) +
    ' ORDER BY PERIODO');
end;

procedure RecargaTitulos;
begin
  FreeAndNil(GTituloEstado);
  FreeAndNil(GTituloSituacionProduccion);
  FreeAndNil(GTituloUnidadMedida);
  FreeAndNil(GTituloPeriodoFacturacion);
  GEmpresaPeriodos := -1;
end;

{ ---------------------------------------------------------------------------------------------- }
{ Otras funciones de TDMMain de Merge                                                            }
{ ---------------------------------------------------------------------------------------------- }

procedure FiltraRO(Tabla: TFDQuery; Filtro: string; Abre: Boolean);
begin
  // En FireDAC no hay datasets RO/RW distintos: es el FiltraTabla de MaxFactu
  DMMain.FiltraTabla(Tabla, Filtro, Abre);
end;

procedure FiltraSQL(Parametro: TParametroFiltrado; Abrir: Boolean);
var
  Orden, Filtro, Nombre: string;
  i: Integer;
  Q: TFDQuery;
begin
  if Length(Parametro.Filtro) = 0 then
    Exit;
  Q := Parametro.Tabla;
  Q.DisableControls;
  try
    Q.Close;
    Q.SQL.Clear;
    Q.SQL.AddStrings(Parametro.SQLBase);
    Orden := OrdenadoPor(Q);
    Ordenar(Q, '');
    Q.SQL.Add(' AND (' + Parametro.Filtro + ')');
    Ordenar(Q, Orden);
    Filtro := '000000';
    for i := 0 to Q.Params.Count - 1 do
    begin
      Nombre := UpperCase(Q.Params[i].Name);
      if Nombre = 'EMPRESA' then Filtro[1] := '1'
      else if Nombre = 'EJERCICIO' then Filtro[2] := '1'
      else if Nombre = 'CANAL' then Filtro[3] := '1'
      else if Nombre = 'SERIE' then Filtro[4] := '1'
      else if Nombre = 'PAIS' then Filtro[5] := '1'
      else if Nombre = 'PGC' then Filtro[6] := '1';
    end;
    DMMain.FiltraTabla(Q, Filtro, Abrir);
  finally
    Q.EnableControls;
  end;
end;

function MinTercero: Integer;
var
  Q: TFDQuery;
begin
  Q := TFDQuery.Create(nil);
  try
    Q.Connection := DMMain.DB;
    Q.SQL.Text := 'SELECT MIN(TERCERO) AS MINIMO FROM SYS_TERCEROS WHERE TERCERO > -1';
    Q.Open;
    Result := Q.FieldByName('MINIMO').AsInteger;
    Q.Close;
  finally
    Q.Free;
  end;
end;

procedure AbrirArchivo(const Archivo: string);
var
  Resultado: NativeInt;
begin
  Resultado := ShellExecute(Application.Handle, nil, PChar(Archivo), nil, nil, SW_SHOW);
  if Resultado <= 32 then
    case Resultado of
      0: ShowMessage(_('El sistema operativo no tiene memoria o recursos suficientes.'));
      ERROR_BAD_FORMAT: ShowMessage(_('El archivo EXE es inválido.'));
      SE_ERR_ACCESSDENIED: ShowMessage(_('El sistema operativo denegó el acceso al archivo especificado.'));
      SE_ERR_ASSOCINCOMPLETE: ShowMessage(_('El archivo asociado es incompatible o inválido.'));
      SE_ERR_DLLNOTFOUND: ShowMessage(_('La librería dinámica especificada no se ha encontrado.'));
      SE_ERR_FNF: ShowMessage(_('El archivo no ha sido encontrado.'));
      SE_ERR_NOASSOC: ShowMessage(_('No hay ninguna aplicación asociada con la extensión del archivo.'));
      SE_ERR_OOM: ShowMessage(_('No ha habido memoria suficiente para completar la operación.'));
      SE_ERR_PNF: ShowMessage(_('No se ha encontrado la carpeta especificada.'));
      SE_ERR_SHARE: ShowMessage(_('Error de permisos.'));
    else
      ShowMessage(Format(_('No se ha podido abrir el archivo (código %d).'), [Resultado]));
    end;
end;

function AseguraDir(const Dir: string): string;
begin
  Result := ExcludeTrailingPathDelimiter(Dir);
  if not DirectoryExists(Result) then
    ForceDirectories(Result);
end;

function DirectorioComunicacionesBase: string;
begin
  if EntornoMerge.DirectorioComunicaciones = '' then
  begin
    // Merge: [Datos] DirectorioComunicaciones del INI; por defecto <exe>\Comunicaciones
    EntornoMerge.DirectorioComunicaciones := ExtractFilePath(ParamStr(0)) + 'Comunicaciones';
    if Assigned(Entorno.IniFile) then
      EntornoMerge.DirectorioComunicaciones := Entorno.IniFile.ReadString('Datos', 'DirectorioComunicaciones',
        EntornoMerge.DirectorioComunicaciones);
  end;
  Result := EntornoMerge.DirectorioComunicaciones;
end;

function DameDirectorioComunicaciones(const Tipo: string): string;
begin
  Result := AseguraDir(DirectorioComunicacionesBase);
  Result := AseguraDir(Result + '\' + Ajusta(IntToStr(Entorno.Empresa), 'I', 3, '0'));
  Result := AseguraDir(Result + '\' + Tipo) + '\';
end;

function DameDirectorioCodCliPro(const Tipo: string; CodCliPro: Integer): string;
begin
  Result := ExcludeTrailingPathDelimiter(DameDirectorioComunicaciones(Tipo));
  // 226 - Directorio = DirBase\Emp\Tipo\CodCliPro en 5 dígitos
  if DMMain.EstadoKri(226) = 1 then
    Result := AseguraDir(Result + '\' + Ajusta(IntToStr(CodCliPro), 'I', 5, '0')) + '\'
  else
    Result := AseguraDir(Result + '\' + IntToStr(CodCliPro)) + '\';
end;

{ ---------------------------------------------------------------------------------------------- }
{ UFormGest                                                                                      }
{ ---------------------------------------------------------------------------------------------- }

procedure AbreData(Clase: TComponentClass; var Referencia);
begin
  // Módulo compartido con contador de uso en Tag (como en Merge)
  if TComponent(Referencia) <> nil then
  begin
    TComponent(Referencia).Tag := TComponent(Referencia).Tag + 1;
    Exit;
  end;
  Screen.Cursor := crHourGlass;
  try
    TComponent(Referencia) := Clase.Create(Application);
    TComponent(Referencia).Tag := 0;
  finally
    Screen.Cursor := crDefault;
  end;
end;

procedure AbreDataVarias(Clase: TComponentClass; var Referencia; Padre: TComponent);
begin
  TComponent(Referencia) := Clase.Create(Padre);
end;

procedure CierraData(var DModuloPar);
var
  DM: TComponent;
begin
  DM := TComponent(DModuloPar);
  if (DM = nil) or (csDestroying in DM.ComponentState) then
    Exit;
  DM.Tag := DM.Tag - 1;
  if DM.Tag < 0 then
  begin
    TComponent(DModuloPar) := nil;
    DM.Free;
  end;
end;

procedure AbreForm(Clase: TFormClass; var Referencia; Sender: TObject);
begin
  if TForm(Referencia) = nil then
    Application.CreateForm(Clase, Referencia);
  TForm(Referencia).Show;
  TForm(Referencia).BringToFront;
end;

procedure CierraForm(var Form);
begin
  if TForm(Form) <> nil then
  begin
    TForm(Form).Close;
    TForm(Form) := nil;
  end;
end;

function AbreFrame(Clase: TClass; const Titulo: string; Ventana: Boolean): TFrame;
var
  A: TAction;
begin
  // Mismo mecanismo que las acciones del menú de MaxFactu (VCLComObject = clase del frame)
  A := TAction.Create(FMMain);
  A.Caption := Titulo;
  A.VCLComObject := Pointer(Clase);
  Result := FMMain.EjecutaAccion(A, Ventana);
end;

initialization
  EntornoMerge := Default(TEntornoMerge);
  // Valores por defecto hasta que se carguen de la configuración del usuario (como hacía Merge al entrar)
  EntornoMerge.ColorEnlaceActivo := $00FF0000;   // azul
  EntornoMerge.ColorCampoID := $00C0FFFF;        // amarillo claro
  EntornoMerge.ColorEdtFnd := $00FFF0E0;

finalization
  GTituloEstado.Free;
  GTituloSituacionProduccion.Free;
  GTituloUnidadMedida.Free;
  GTituloPeriodoFacturacion.Free;

end.
