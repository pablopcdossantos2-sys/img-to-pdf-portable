# Herramientas de archivos (Ferramentas de Arquivo)

**Idiomas:** [Português (Brasil)](README.md) · [English](README.en.md) · Español

Aplicación de escritorio para trabajar localmente con archivos PDF e imágenes. Está desarrollada con **Python, PySide6, pypdf y Pillow**. Actualmente, la interfaz de la aplicación está en portugués brasileño.

## Funcionalidades

### Herramientas para PDF

- **Imágenes a PDF:** convierte imágenes JPG, JPEG, PNG, BMP, WEBP y TIFF en páginas A4, eligiendo automáticamente la orientación y conservando las proporciones. Las imágenes transparentes se colocan sobre un fondo blanco.
- **Unir PDF:** combina varios archivos en el orden elegido e intenta conservar los marcadores importados.
- **Extraer páginas:** guarda páginas o intervalos seleccionados, como `1-3, 5, 8-10`. Hay una opción para repetir páginas en el documento de salida.
- **Girar páginas:** gira 90°, 180° o 270°, en todo el documento o solo en las páginas seleccionadas.
- **Dividir PDF:** crea un archivo PDF independiente por página. La carpeta de destino se crea si hace falta. Los archivos de destino existentes nunca se sobrescriben; si hay un conflicto, la operación se detiene.
- **Protección de salida:** el cuadro de guardado añade la extensión PDF, impide elegir como destino uno de los archivos de origen y solicita confirmación antes de reemplazar un archivo existente.

### Herramientas para imágenes

- **Conversión por lotes:** JPEG, PNG, WEBP, BMP y TIFF.
- **Cambiar tamaño:** límites opcionales de ancho y alto en píxeles, conservando la proporción y sin ampliar imágenes pequeñas.
- **Calidad:** control de calidad JPEG/WEBP y conservación de perfiles ICC cuando son compatibles con el modo de color de destino.
- **CMYK y transparencia:** convierte los modos de color que no admite el formato de destino; al exportar a JPEG/BMP, la transparencia se compone sobre un fondo blanco.

### Facilidad de uso, privacidad y robustez

- Interfaz de escritorio con pestañas, controles para reordenar, arrastrar y soltar, duplicación intencional de elementos, mensajes en portugués e indicador de procesamiento.
- Controles de DPI y márgenes al convertir imágenes a PDF.
- Las tareas largas se ejecutan fuera del hilo principal de la interfaz; la ventana no se puede cerrar mientras una tarea está activa.
- Un botón permite abrir la carpeta de salida al finalizar el procesamiento.
- Procesamiento local: los documentos no se envían a servicios externos.
- Las operaciones normales no reemplazan los archivos originales.
- Escrituras temporales/atómicas para operaciones PDF; la división se detiene si ya existe un archivo con el nombre de destino.
- Las pruebas automatizadas y la auditoría de dependencias se ejecutan en GitHub Actions. El flujo también prueba el inicio del ejecutable de Windows y publica una suma de verificación SHA-256.

## Usar en Windows sin instalar Python

El flujo **Python CI, security and package** genera un ejecutable portable para Windows x64 y una suma de verificación SHA-256.

1. Abre la pestaña [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions) del repositorio.
2. Entra en la ejecución más reciente llamada **Python CI, security and package** y comprueba que haya terminado correctamente.
3. En la sección **Artifacts**, descarga `Ferramentas-de-Arquivo-Portable-win-x64`.
4. Extrae el archivo ZIP y ejecuta `FerramentasDeArquivo.exe`.
5. Usa `FerramentasDeArquivo.exe.sha256` para verificar el hash del ejecutable.

El artefacto incluye el entorno de ejecución y no requiere instalar Python por separado. Windows puede mostrar una advertencia de seguridad para archivos descargados; verifica el origen antes de ejecutar la aplicación.

> Los artefactos de GitHub Actions son temporales y caducan según el periodo de retención de GitHub. Se podrá publicar una versión permanente por separado cuando el paquete se haya validado en uso real.

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
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FerramentasDeArquivo main.py
```

El ejecutable se crea en `dist/FerramentasDeArquivo.exe`. Para comprobar que el paquete inicia la interfaz y carga las dependencias de Qt, ejecuta:

```powershell
.\dist\FerramentasDeArquivo.exe --selftest
```

La opción `--selftest` inicializa la interfaz sin mostrar una ventana y termina con código de éxito si el inicio funciona correctamente.

## ROADMAP

Este roadmap reúne posibles mejoras para orientar el desarrollo futuro. El orden indica prioridades relativas, no fechas de entrega garantizadas.

### Prioridades

- [ ] **Abrir PDF protegidos con contraseña:** añadir un campo de contraseña con tratamiento seguro, sin registrar ni guardar la contraseña innecesariamente.
- [ ] **Conservar funciones avanzadas de PDF:** mejorar la conservación de marcadores, metadatos, formularios, enlaces internos y destinos al unir, extraer, girar o dividir documentos.
- [ ] **Gestionar imágenes multipágina y animadas:** permitir elegir entre importar solo el primer fotograma o crear páginas a partir de fotogramas/páginas adicionales de TIFF multipágina y formatos animados compatibles.
- [ ] **Publicar versiones permanentes:** automatizar GitHub Releases con el ejecutable, la suma de verificación SHA-256 y las notas de la versión, para que las descargas no dependan de artefactos temporales de Actions.
- [ ] **Crear paquetes para otros sistemas operativos:** evaluar versiones portables para macOS y Linux, además del ejecutable actual para Windows x64.
- [ ] **Configurar los permisos de salida:** documentar y, si resulta útil, permitir controlar los permisos de los archivos generados en Linux/macOS, que actualmente pueden quedar restringidos al usuario actual.
