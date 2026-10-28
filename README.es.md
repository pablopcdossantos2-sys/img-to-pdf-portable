# PDF Hub

**Idiomas:** [Português (Brasil)](README.md) · [English](README.en.md) · Español

Aplicación de escritorio para trabajar localmente con archivos PDF e imágenes, desarrollada con **Python, PySide6, pypdf, Pillow y ReportLab**. La interfaz se puede cambiar entre portugués brasileño, inglés y español; la preferencia se guarda localmente.

**Descarga:** [Descargar PDF Hub para Windows, Linux o macOS](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases/latest).

> El enlace anterior apunta a la última versión publicada. Los cambios en la rama `main` no se incluyen en las descargas hasta que se publique una nueva versión.

## Funcionalidades

### Herramientas para PDF
- **Interfaz y entrada rápida:** navegación lateral con iconos para cada herramienta, temas claro/oscuro en Configuración, importación de imágenes mediante arrastrar y soltar, recomendación automática de DPI a partir de las dimensiones y margen inicial de 0 mm.

- **Imágenes a PDF:** convierte imágenes JPG, JPEG, PNG, BMP, WEBP, TIFF y GIF en páginas A4, eligiendo la orientación y conservando las proporciones. Por defecto, importa todas las páginas/fotogramas de archivos multipágina o animados, con una opción para usar solo el primero. La transparencia se coloca sobre fondo blanco.
- **Unir PDF:** combina archivos en el orden elegido, solicita contraseñas para los PDFs protegidos e intenta conservar marcadores, metadatos y referencias internas compatibles.
- **Mezclar PDF:** intercala páginas de dos documentos, con intervalos opcionales, orden inverso para el segundo archivo y cantidad configurable de páginas por bloque. Admite contraseñas y conserva los originales.
- **Insertar páginas repetidamente:** inserta páginas seleccionadas de un PDF en otro después de cada N páginas del documento de destino, repitiendo la selección elegida. Admite contraseñas y conserva los archivos originales.
- **Extraer páginas:** guarda páginas o intervalos como `1-3, 5, 8-10`, permite repetir páginas y acepta contraseña. La navegación y las anotaciones se conservan cuando es posible, con referencias adaptadas a las páginas retenidas.
- **Eliminar páginas:** elimina páginas concretas o intervalos, como `2, 4-6, 9`, creando un PDF nuevo y conservando el original. Admite documentos protegidos con contraseña e impide eliminar todas las páginas.
- **Girar páginas:** gira 90°, 180° o 270°, en todo el documento o solo las páginas seleccionadas, incluidos los PDFs protegidos con contraseña.
- **Dividir PDF:** permite un archivo por página, grupos de N páginas, cortes después de páginas seleccionadas, pares o impares, tamaño aproximado y marcadores con nivel y filtro opcional de expresión regular. Crea la carpeta si hace falta, acepta contraseña, conserva estructuras compatibles cuando es posible y nunca sobrescribe archivos existentes. El tamaño es estimado; una página puede superar el límite.
- **PDF a imágenes:** exporta todas las páginas o solo intervalos seleccionados como PNG o JPEG, con resolución ajustable (72–600 DPI), calidad JPEG configurable, soporte para contraseña y nombres que evitan sobrescribir archivos existentes.
- **Reordenar páginas con miniaturas y vista previa:** cada página aparece como miniatura en una cuadrícula; arrastra para cambiar el orden y revisa la página seleccionada en el panel de vista previa. Las miniaturas se generan en segundo plano y siguen la página original. Cada página debe aparecer exactamente una vez.
- **Marcas de agua y numeración selectivas:** aplica texto, numeración o ambos a todas las páginas o solo a intervalos (por ejemplo, `2-4, 7`). La numeración conserva la posición original de la página en el documento. El contenido original no se rasteriza.
- **Optimizar PDF:** elige compresión de streams sin pérdida y eliminación de objetos duplicados, o recomprensión JPEG equilibrada de imágenes opacas con calidad ajustable. Las imágenes transparentes y las imágenes inline se mantienen sin cambios.
- **Flujo por lotes:** combina rotación, marca de agua/numeración y optimización en una sola operación, o aplica un perfil guardado a todos los PDF de una carpeta. Cada PDF obtiene un resultado individual; un error no detiene los demás archivos. El informe se puede exportar a CSV y es posible conservar subcarpetas. La pausa manual se aplica entre PDF; la cancelación segura termina el PDF actual antes de detenerse y conserva un punto de control para reanudar. Si se interrumpe un lote, activa la reanudación para reutilizar los PDF ya completados; los archivos que fallaron se vuelven a intentar. La acción de reintento procesa solo los PDF fallidos y conserva los demás resultados.
- **Perfiles reutilizables por lotes:** guarda, carga y elimina perfiles con nombre en las preferencias locales, o expórtalos/importarlos como JSON. El esquema 2 migra automáticamente los perfiles antiguos del esquema 1, conserva sus opciones y añade un sufijo de salida predeterminado. Nunca incluye rutas de PDF ni contraseñas; se rechazan campos desconocidos y opciones no válidas.
- **Protección de salida:** el cuadro de guardado añade la extensión PDF, impide elegir como destino uno de los archivos de origen y solicita confirmación antes de reemplazar un archivo existente.

### Herramientas para imágenes

- **Conversión por lotes:** JPEG, PNG, WEBP, BMP y TIFF.
- **Cambiar tamaño:** límites opcionales de ancho y alto en píxeles, conservando la proporción y sin ampliar imágenes pequeñas.
- **Calidad:** control de calidad JPEG/WEBP y conservación de perfiles ICC cuando son compatibles con el modo de color de destino.
- **CMYK y transparencia:** convierte los modos de color que no admite el formato de destino; al exportar a JPEG/BMP, la transparencia se compone sobre un fondo blanco.

### Facilidad de uso, privacidad y robustez

- Interfaz de escritorio con selector de idioma PT-BR/inglés/español, cuadrículas de miniaturas con vista previa, perfiles reutilizables de flujo por lotes, duplicación intencional e indicador de procesamiento. Los diálogos principales, solicitudes de contraseña, confirmaciones y errores habituales de intervalos siguen el idioma seleccionado. Los errores comunes de análisis pypdf, renderizado Qt PDF y procesamiento de imágenes reciben mensajes más claros y traducidos, sin exponer diagnósticos internos. Las contraseñas se escriben en campos ocultos, no se guardan en las preferencias y los campos se limpian al iniciar la operación.
- Controles de DPI y márgenes al convertir imágenes a PDF.
- Las tareas largas se ejecutan fuera del hilo principal de la interfaz; la ventana no se puede cerrar mientras una tarea está activa.
- Un botón permite abrir la carpeta de salida al finalizar el procesamiento.
- Procesamiento local: los documentos no se envían a servicios externos.
- Las operaciones normales no reemplazan los archivos originales.
- Escrituras temporales/atómicas para operaciones PDF; la división se detiene si ya existe un archivo con el nombre de destino.
- Preferencia persistente de permisos de salida en Linux/macOS: solo el usuario (0600, recomendado por defecto) o lectura compartida (0644). En Windows, los permisos los gestiona el sistema operativo.
- **Nota sobre calidad:** la optimización equilibrada puede reducir la calidad de imagen y no garantiza que todos los PDFs sean más pequeños; conserva el original y compara los resultados. Las marcas de agua usan la fuente Helvetica integrada y pueden no admitir todos los caracteres Unicode.
- Las pruebas automatizadas y la auditoría de dependencias se ejecutan en GitHub Actions. El flujo valida los paquetes de Windows, Linux y macOS y genera checksums SHA-256.

## Descargar paquetes portátiles

El flujo **PDF Hub CI, security and packages** prueba la aplicación y genera paquetes portátiles para Windows x64, Linux x64 y macOS Apple Silicon. En los envíos a `main`, se pueden descargar artefactos temporales desde [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions); las versiones permanentes se generan a partir de etiquetas `v*`.

1. Para una descarga permanente, abre [Releases](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases) y elige el paquete de tu sistema operativo.
2. Hasta que haya una versión publicada, abre [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions), entra en la ejecución más reciente de **PDF Hub CI, security and packages** y confirma que haya terminado correctamente.
3. En **Artifacts**, descarga el paquete deseado: Windows x64, Linux x64 o macOS Apple Silicon.
4. Extrae el paquete. En Windows, ejecuta `PDFHub.exe`; en Linux, ejecuta `PDFHub`; en macOS, abre `PDF Hub.app`.
5. Los archivos `.sha256` permiten comprobar el hash del paquete. En las versiones publicadas, descarga el checksum junto al mismo paquete desde la página oficial.

El artefacto incluye el entorno de ejecución y no requiere instalar Python por separado. Windows puede mostrar una advertencia de seguridad para archivos descargados; verifica el origen antes de ejecutar la aplicación.

> Los artefactos de GitHub Actions son temporales y caducan según el periodo de retención configurado. Las versiones permanentes se generan al enviar una etiqueta como `v0.10.0`. Los ejecutables no tienen firma digital/notarización; Windows SmartScreen o macOS Gatekeeper pueden mostrar una advertencia.

## Ejecutar desde el código fuente

Requisitos: Windows, macOS o Linux y Python 3.11 o posterior.

En Windows, después de instalar Python 3.11 o posterior, haz doble clic en `instalar-e-iniciar.bat`. El script crea un entorno virtual, instala las dependencias e inicia la aplicación. Para las siguientes ejecuciones, usa `executar-aplicativo.bat`. Se necesita conexión a internet durante la primera instalación.

También puedes ejecutar manualmente estos comandos en PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

No copies el entorno virtual `.venv` a otra carpeta o computadora. Si mueves el proyecto y el entorno deja de funcionar, elimina `.venv` y vuelve a ejecutar `instalar-e-iniciar.bat`.

Si PowerShell bloquea `Activate.ps1`, puedes cambiar la política de ejecución solo para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
```

En macOS o Linux, usa `python3 -m venv .venv`, `source .venv/bin/activate` y después `python -m pip install -r requirements.txt`.

## Pruebas y creación del ejecutable

Instala las dependencias de desarrollo y ejecuta las pruebas y la auditoría de dependencias:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip_audit --local
```

Para generar el ejecutable de Windows con el mismo comando que usa CI:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PDFHub main.py
```

El ejecutable se crea en `dist/PDFHub.exe`. Para comprobar que el paquete inicia la interfaz y carga las dependencias de Qt, ejecuta:

```powershell
.\dist\PDFHub.exe --selftest
```

La opción `--selftest` inicializa la interfaz sin mostrar una ventana y termina con código de éxito si el inicio funciona correctamente.
