# PDF Hub

**Idiomas:** [Português (Brasil)](README.md) · [English](README.en.md) · Español

Aplicación de escritorio para trabajar localmente con archivos PDF e imágenes. Está desarrollada con **Python, PySide6, pypdf y Pillow**. Actualmente, la interfaz de la aplicación está en portugués brasileño.

## Funcionalidades

### Herramientas para PDF

- **Imágenes a PDF:** convierte imágenes JPG, JPEG, PNG, BMP, WEBP, TIFF y GIF en páginas A4, eligiendo la orientación y conservando las proporciones. Por defecto, importa todas las páginas/fotogramas de archivos multipágina o animados, con una opción para usar solo el primero. La transparencia se coloca sobre fondo blanco.
- **Unir PDF:** combina archivos en el orden elegido, solicita contraseñas para los PDFs protegidos e intenta conservar marcadores, metadatos y referencias internas compatibles.
- **Extraer páginas:** guarda páginas o intervalos como `1-3, 5, 8-10`, permite repetir páginas y acepta contraseña. La navegación y las anotaciones se conservan cuando es posible, con referencias adaptadas a las páginas retenidas.
- **Girar páginas:** gira 90°, 180° o 270°, en todo el documento o solo las páginas seleccionadas, incluidos los PDFs protegidos con contraseña.
- **Dividir PDF:** crea un PDF por página y crea la carpeta de destino cuando hace falta. Admite contraseñas e intenta conservar metadatos, marcadores y anotaciones de página. Los archivos de destino existentes nunca se sobrescriben; si hay conflicto, la operación se detiene.
- **Protección de salida:** el cuadro de guardado añade la extensión PDF, impide elegir como destino uno de los archivos de origen y solicita confirmación antes de reemplazar un archivo existente.

### Herramientas para imágenes

- **Conversión por lotes:** JPEG, PNG, WEBP, BMP y TIFF.
- **Cambiar tamaño:** límites opcionales de ancho y alto en píxeles, conservando la proporción y sin ampliar imágenes pequeñas.
- **Calidad:** control de calidad JPEG/WEBP y conservación de perfiles ICC cuando son compatibles con el modo de color de destino.
- **CMYK y transparencia:** convierte los modos de color que no admite el formato de destino; al exportar a JPEG/BMP, la transparencia se compone sobre un fondo blanco.

### Facilidad de uso, privacidad y robustez

- Interfaz de escritorio con pestañas, controles para reordenar, arrastrar y soltar, duplicación intencional de elementos, mensajes en portugués e indicador de procesamiento. Las contraseñas se escriben en campos ocultos, no se guardan en las preferencias y los campos se limpian al iniciar la operación.
- Controles de DPI y márgenes al convertir imágenes a PDF.
- Las tareas largas se ejecutan fuera del hilo principal de la interfaz; la ventana no se puede cerrar mientras una tarea está activa.
- Un botón permite abrir la carpeta de salida al finalizar el procesamiento.
- Procesamiento local: los documentos no se envían a servicios externos.
- Las operaciones normales no reemplazan los archivos originales.
- Escrituras temporales/atómicas para operaciones PDF; la división se detiene si ya existe un archivo con el nombre de destino.
- Preferencia persistente de permisos de salida en Linux/macOS: solo el usuario (0600, recomendado por defecto) o lectura compartida (0644). En Windows, los permisos los gestiona el sistema operativo.
- Las pruebas automatizadas y la auditoría de dependencias se ejecutan en GitHub Actions. El flujo también prueba el inicio del ejecutable de Windows y publica una suma de verificación SHA-256.

## Usar en Windows sin instalar Python

El flujo **PDF Hub CI, security and packages** prueba la aplicación y genera paquetes portátiles para Windows x64, Linux x64 y macOS Apple Silicon. En los envíos a `main`, se pueden descargar artefactos temporales desde [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions); las versiones permanentes se generan a partir de etiquetas `v*`.

1. Para una descarga permanente, abre [Releases](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases) y elige el paquete de tu sistema operativo.
2. Hasta que haya una versión publicada, abre [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions), entra en la ejecución más reciente de **PDF Hub CI, security and packages** y confirma que haya terminado correctamente.
3. En **Artifacts**, descarga el paquete deseado: Windows x64, Linux x64 o macOS Apple Silicon.
4. Extrae el paquete. En Windows, ejecuta `PDFHub.exe`; en Linux, ejecuta `PDFHub`; en macOS, abre `PDF Hub.app`.
5. Los archivos `.sha256` permiten comprobar el hash del paquete. En las versiones publicadas, descarga el checksum junto al mismo paquete desde la página oficial.

El artefacto incluye el entorno de ejecución y no requiere instalar Python por separado. Windows puede mostrar una advertencia de seguridad para archivos descargados; verifica el origen antes de ejecutar la aplicación.

> Los artefactos de GitHub Actions son temporales y caducan según el periodo de retención configurado. Las versiones permanentes se generan al enviar una etiqueta como `v0.3.0`. Los ejecutables no tienen firma digital/notarización; Windows SmartScreen o macOS Gatekeeper pueden mostrar una advertencia.

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

## ROADMAP

### Completado en la versión 0.3.0

- [x] **PDF protegidos con contraseña:** campos de contraseña ocultos para extraer, girar y dividir; solicitud puntual para cada PDF protegido al unir. Las contraseñas no se guardan en las preferencias.
- [x] **Preservación de recursos PDF:** uso de clonación de documentos/páginas de pypdf para conservar marcadores, metadatos, anotaciones y enlaces internos cuando es posible. El resultado depende de la estructura del PDF; los formularios complejos y los enlaces a páginas eliminadas deben revisarse.
- [x] **Imágenes multipágina y animadas:** elección entre importar todos los fotogramas/páginas o solo el primero al crear un PDF, incluidos TIFF y formatos animados compatibles con Pillow, como GIF y WEBP.
- [x] **Versiones permanentes:** CI configurado para crear una versión de GitHub al enviar una etiqueta `v*`, con paquetes y checksums de las plataformas compatibles.
- [x] **Paquetes multiplataforma:** compilaciones para Windows x64, Linux x64 y macOS Apple Silicon configuradas en GitHub Actions.
- [x] **Permisos de salida:** preferencia persistente para usar 0600 (solo el usuario, por defecto) o 0644 (lectura compartida) en Linux/macOS.

### Posibles mejoras futuras

- [ ] Traducir la interfaz al inglés y al español, además del portugués brasileño.
- [ ] Añadir reordenación visual de páginas mediante arrastrar y soltar antes de guardar.
- [ ] Incorporar compresión/optimización PDF con una elección explícita entre tamaño y calidad.
- [ ] Añadir marcas de agua, numeración de páginas y sellos.
