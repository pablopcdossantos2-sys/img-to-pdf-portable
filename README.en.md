# PDF Hub

**Languages:** [Português (Brasil)](README.md) · English · [Español](README.es.md)

A desktop application for working with PDF files and images locally. It is built with **Python, PySide6, pypdf, and Pillow**. The application interface is currently in Brazilian Portuguese.

## Features

### PDF tools

- **Images to PDF:** convert JPG, JPEG, PNG, BMP, WEBP, TIFF, and GIF images into A4 pages, automatically choosing orientation and preserving aspect ratio. By default, all pages/frames in multipage or animated files are imported, with an option to use only the first. Transparency is placed on white.
- **Merge PDFs:** combine files in the chosen order, prompt for protected PDFs' passwords, and attempt to preserve compatible bookmarks, metadata, and internal references.
- **Extract pages:** save selected pages or ranges such as `1-3, 5, 8-10`, allow repeated pages, and accept a password. Navigation and annotations are retained where possible, with remapping to the retained pages.
- **Rotate pages:** rotate by 90°, 180°, or 270°, across the whole document or selected pages, including password-protected PDFs.
- **Split PDF:** create one PDF per page and create the output folder when needed. Passwords are supported, and metadata, bookmarks, and page annotations are preserved where possible. Existing destination files are never overwritten; conflicts stop the operation.
- **Safer output handling:** the save dialog adds the PDF extension, prevents choosing a source file as the output, and asks before replacing an existing file.

### Image tools

- **Batch conversion:** JPEG, PNG, WEBP, BMP, and TIFF.
- **Resize:** optional maximum width and height in pixels, preserving aspect ratio and avoiding enlargement of smaller images.
- **Quality controls:** JPEG/WEBP quality setting and ICC profile preservation when compatible with the destination color mode.
- **CMYK and transparency:** convert color modes that are unsupported by the destination format; transparency is composited onto white when exporting to JPEG/BMP.

### Usability, privacy, and reliability

- Desktop interface with tabs, reorder controls, drag and drop, intentional item duplication, Portuguese error messages, and a processing indicator. Passwords are entered through masked fields, are not stored in preferences, and the fields are cleared when an operation starts.
- DPI and margin controls when converting images to PDF.
- Long-running tasks execute outside the main UI thread; the window cannot be closed while a task is running.
- A button opens the output folder when processing finishes.
- Local processing: documents are not uploaded to external services.
- Source files are not replaced by normal processing operations.
- Temporary/atomic writes for PDF operations; splitting stops if an output filename already exists.
- Persistent output permission preference on Linux/macOS: owner-only (0600, recommended default) or shared-readable (0644). Windows permissions are managed by the operating system.
- Automated tests and dependency auditing run in GitHub Actions. The workflow also smoke-tests the Windows executable and publishes a SHA-256 checksum.

## Use on Windows without installing Python

The **PDF Hub CI, security and packages** workflow tests the app and builds portable packages for Windows x64, Linux x64, and macOS Apple Silicon. On pushes to `main`, download validation artifacts from [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions); permanent releases are created from `v*` tags.

1. For a permanent download, open [Releases](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases) and choose your operating system's package.
2. Until a release is available, open [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions), open the latest **PDF Hub CI, security and packages** run, and confirm it succeeded.
3. Under **Artifacts**, download the desired package: Windows x64, Linux x64, or macOS Apple Silicon.
4. Extract the package. On Windows, run `PDFHub.exe`; on Linux, run `PDFHub`; on macOS, open `PDF Hub.app`.
5. The `.sha256` files can be used to verify the package checksum. For releases, download the checksum beside the same package from the official release page.

The artifact includes the runtime and does not require a separate Python installation. Windows may show a security warning for downloaded files; verify the source before running the application.

> GitHub Actions artifacts are temporary and expire according to the configured retention period. Versioned GitHub Releases are created when a tag such as `v0.3.0` is pushed. The executables are not digitally signed/notarized; Windows SmartScreen or macOS Gatekeeper may display a warning.

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
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PDFHub main.py
```

The executable is created at `dist/PDFHub.exe`. To check that the packaged app can initialize its interface and load the Qt dependencies, run:

```powershell
.\dist\PDFHub.exe --selftest
```

The `--selftest` option initializes the interface in headless mode and exits with a success code if startup works.

## ROADMAP

### Completed in version 0.3.0

- [x] **Password-protected PDFs:** masked password fields for extraction, rotation, and splitting; prompt for each protected file when merging. Passwords are not saved in preferences.
- [x] **PDF resource preservation:** use pypdf document/page cloning to preserve bookmarks, metadata, annotations, and internal links where possible. Results depend on the PDF's structure; complex forms and links to removed pages still require review.
- [x] **Multipage and animated images:** choose whether to import all pages/frames or only the first when creating a PDF, including TIFF and Pillow-supported animated formats such as GIF and WEBP.
- [x] **Permanent releases:** CI is configured to create a GitHub Release when a `v*` tag is pushed, with platform packages and checksums.
- [x] **Cross-platform packages:** Windows x64, Linux x64, and macOS Apple Silicon builds are configured in GitHub Actions.
- [x] **Output permissions:** persistent preference to use 0600 (owner-only, default) or 0644 (shared-readable) on Linux/macOS.

### Possible next improvements

- [ ] Translate the interface into English and Spanish, in addition to Brazilian Portuguese.
- [ ] Add visual page reordering with drag and drop before saving.
- [ ] Add PDF compression/optimization with an explicit file-size vs. quality choice.
- [ ] Add watermarks, page numbers, and stamps.
