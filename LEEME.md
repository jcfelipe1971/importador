# Merge13 + importador de módulos de Merge — primer módulo: Familias

## Contenido
- **Merge13/**: el proyecto Delphi 13 (aspecto y datos de MaxFactu, nombres y API de Merge) con **Familias**
  importado. Compila con 0 errores (127.095 líneas): `Merge13\compila.bat` o abrir `Merge13.dpr` en el IDE.
  - `Merge\` – módulos importados de Merge, en sus mismas carpetas (`Merge\Almacenes\UFMFamilias`, `UDMFamilias`)
    y units que usan (`UDameDato`, `UParam`).
  - `Pendientes\` – units de las que dependen y aún no se han importado (interfaz real de Merge, cuerpo vacío).
    Al importar cada una, desaparece de aquí.
  - `Conversion\` – utilidades del importador (buscador de campo, control de concurrencia, rutinas de Merge
    que MaxFactu no tiene) e `informes\informe_UFMFamilias.txt` con lo convertido y lo que queda por revisar.
- **importador/**: `merge2m13.py` y sus módulos (Python 3.10+, `pip install firebird-driver`).
- **importar_modulo.bat**: `importar_modulo.bat UFMFamilias` → importa el módulo y compila. Ajustar rutas dentro.
- **pruebas/**: prueba automática de Familias, su resultado y una captura.
- **gen/**: generadores de `UFMain` y de las bases `TFPEdit…` a partir de MaxFactu.

## Qué hace el importador con un módulo (`--modulo UFMFamilias`)
1. El formulario **sigue siendo formulario**: misma unit, misma clase (`TFMFamilias`), misma base (`TFPEdit`),
   su `FormCreate`, `AbreData`, `FMain`, `REntorno`… no cambian. Los componentes de Merge pasan a VCL estándar
   con sus propiedades y eventos exactos de Delphi 13; los EditFind a `TDBEdit` + buscador (F3 / doble clic).
2. Su módulo de datos pasa de FIB a FireDAC: consultas, SQL de actualización, transacciones `TLocal`/`TUpdate`,
   **tipos de campo leídos de la base de datos** y parámetros guardados en el DFM.
3. Registra la acción de `FMain` que abría el módulo en Merge (`RegistraModulo('AFamilias', …)`): aparece en
   el menú, en su grupo (**Almacenes**), y se abre en pestaña (clic en el nombre) o ventana (clic en el icono).
4. Actualiza `Merge13.dpr`. Se puede **volver a importar** el mismo módulo cuantas veces haga falta.
5. Deja el informe en `Conversion\informes\`.

## Resultado con Familias (probado contra ARMTEX-DEMO, Firebird 5)
Conectar → sesión ADMIN → aparece el grupo Almacenes → Familias en pestaña (48 familias, 11 consultas abiertas)
→ ficha → **modificar el título y grabar: comprobado en la base de datos** → deshacer → cerrar y abrir en ventana.
Sin excepciones. Ver `pruebas/resultado_prueba_familias.log` y `pruebas/captura_familias.png`.

## Pendiente en Familias
Opciones que dependen de units aún no importadas (en `Pendientes\`): listados (`UDMLstFamilias`,
`UFMListConfig`, `UFPEditListado…`), correo (`UFSendCorreo`), imágenes (`UImagenes`, `UFMostrarImagen`),
sincronización con la tienda, pregunta de artículos por familia, `uFBusca`. Compilan, pero no hacen nada hasta
importarlas. `UImagenes` está en `importador\m13_pendientes.txt` a propósito (usa una segunda base de datos
de imágenes y requiere una conversión propia).
