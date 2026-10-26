# File Tools (Ferramentas de Arquivo)

**Languages:** [Português (Brasil)](README.md) · English · [Español](README.es.md)

A desktop application for working with PDF files and images locally. It is built with **Python, PySide6, pypdf, and Pillow**. The application interface is currently in Brazilian Portuguese.

## Features

### PDF tools

- **Images to PDF:** convert JPG, JPEG, PNG, BMP, WEBP, and TIFF images into A4 pages, automatically choosing page orientation while preserving aspect ratio. Transparent images are placed on a white background.
- **Merge PDFs:** combine multiple files in the chosen order and attempt to preserve imported bookmarks.
- **Extract pages:** save selected pages or ranges such as `1-3, 5, 8-10`. An option allows pages to be repeated in the output document.
- **Rotate pages:** rotate by 90°, 180°, or 270°, either across the whole document or only on selected pages.
- **Split PDF:** create a separate PDF for every page. The output folder is created when needed. Existing destination files are never overwritten; conflicts stop the operation.
- **Safer output handling:** the save dialog adds the PDF extension, prevents choosing a source file as the output, and asks before replacing an existing file.

### Image tools

- **Batch conversion:** JPEG, PNG, WEBP, BMP, and TIFF.
- **Resize:** optional maximum width and height in pixels, preserving aspect ratio and avoiding enlargement of smaller images.
- **Quality controls:** JPEG/WEBP quality setting and ICC profile preservation when compatible with the destination color mode.
- **CMYK and transparency:** convert color modes that are unsupported by the destination format; transparency is composited onto white when exporting to JPEG/BMP.

### Usability, privacy, and reliability

- Desktop interface with tabs, reorder controls, drag and drop, intentional item duplication, Portuguese error messages, and a processing indicator.
- DPI and margin controls when converting images to PDF.
- Long-running tasks execute outside the main UI thread; the window cannot be closed while a task is running.
- A button opens the output folder when processing finishes.
- Local processing: documents are not uploaded to external services.
- Source files are not replaced by normal processing operations.
- Temporary/atomic writes for PDF operations; splitting stops if an output filename already exists.
- Automated tests and dependency auditing run in GitHub Actions. The workflow also smoke-tests the Windows executable and publishes a SHA-256 checksum.

## Use on Windows without installing Python

The **Python CI, security and package** workflow builds a portable executable for Windows x64 and a SHA-256 checksum.

1. Open the repository's [Actions page](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions).
2. Open the latest run named **Python CI, security and package** and confirm that it succeeded.
3. Under **Artifacts**, download `Ferramentas-de-Arquivo-Portable-win-x64`.
4. Extract the ZIP file and run `FerramentasDeArquivo.exe`.
5. Use `FerramentasDeArquivo.exe.sha256` to verify the executable's hash.

The artifact includes the runtime and does not require a separate Python installation. Windows may show a security warning for downloaded files; verify the source before running the application.

> GitHub Actions artifacts are temporary and expire according to GitHub's retention period. A permanent release can be published separately after the package has been validated in real-world use.

## Run from source

Requirements: Windows, macOS, or Linux and Python 3.11 or later.

On Windows, after installing Python 3.11 or later, double-click `instalar-e-iniciar.bat`. The script creates a virtual environment, installs dependencies, and launches the app. For later runs, use `executar-aplicativo.bat`. An internet connection is required for the first installation.

You can also run the following commands manually in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Do not copy the `.venv` virtual environment to a different folder or computer. If you move the project and the environment stops working, delete `.venv` and run `instalar-e-iniciar.bat` again.

If PowerShell blocks `Activate.ps1`, you can adjust the execution policy for the current session only:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`, and then `python -m pip install -r requirements.txt`.

## Tests and executable build

Install the development dependencies, then run tests and the dependency audit:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip_audit --local
```

To build the Windows executable using the same command as CI:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FerramentasDeArquivo main.py
```

The executable is created at `dist/FerramentasDeArquivo.exe`. To check that the packaged app can initialize its interface and load the Qt dependencies, run:

```powershell
.\dist\FerramentasDeArquivo.exe --selftest
```

The `--selftest` option initializes the interface in headless mode and exits with a success code if startup works.

## ROADMAP

This roadmap records potential improvements for future development. The order indicates relative priority, not guaranteed delivery dates.

### Priorities

- [ ] **Open password-protected PDFs:** add a password field with secure handling, without logging or unnecessarily storing passwords.
- [ ] **Preserve advanced PDF features:** improve retention of bookmarks, metadata, forms, internal links, and destinations when merging, extracting, rotating, or splitting documents.
- [ ] **Handle multipage and animated images:** allow users to choose between importing only the first frame or creating pages from additional frames/pages in multipage TIFF and supported animated formats.
- [ ] **Publish permanent, versioned releases:** automate GitHub Releases with the executable, SHA-256 checksum, and release notes so downloads do not depend on temporary Actions artifacts.
- [ ] **Package for other operating systems:** evaluate portable builds for macOS and Linux in addition to the current Windows x64 executable.
- [ ] **Configure output permissions:** document and, where useful, let users control permissions for generated files on Linux/macOS, which may currently be restricted to the current user.
