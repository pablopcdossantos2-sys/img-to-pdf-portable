# PDF Hub

**Languages:** [Português (Brasil)](README.md) · English · [Español](README.es.md)

A desktop application for working with PDF files and images locally, built with **Python, PySide6, pypdf, Pillow, and ReportLab**. The interface can be switched between Brazilian Portuguese, English, and Spanish; the choice is stored locally.

**Download:** [Get PDF Hub for Windows, Linux, or macOS](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases/latest).

> The link above points to the latest published version. Changes on the `main` branch are not included in downloads until a new release is published.

## Features

### PDF tools
- **Interface and quick image input:** left-side navigation with an icon for every tool, light/dark appearance in Settings, drag-and-drop image import, automatic DPI recommendation from image dimensions, and a default 0 mm margin.

- **Images to PDF:** convert JPG, JPEG, PNG, BMP, WEBP, TIFF, and GIF images into A4 pages, automatically choosing orientation and preserving aspect ratio. By default, all pages/frames in multipage or animated files are imported, with an option to use only the first. Transparency is placed on white.
- **Merge PDFs:** combine files in the chosen order, select page ranges for each input independently, prompt for protected PDFs' passwords, and attempt to preserve compatible bookmarks, metadata, and internal references.
- **Mix PDFs:** interleave pages from two documents, with optional page ranges, reverse order for the second file, and configurable pages per block. Supports passwords and preserves the originals.
- **Insert pages repeatedly:** insert selected pages from one PDF into another after every N target pages, repeating the chosen selection. Supports passwords and preserves the original files.
- **Extract pages:** save selected pages or ranges such as `1-3, 5, 8-10`, allow repeated pages, and accept a password. Navigation and annotations are retained where possible, with remapping to the retained pages.
- **Delete pages:** remove selected pages or ranges, such as `2, 4-6, 9`, into a new PDF while preserving the original. Supports password-protected documents and prevents deleting every page.
- **Rotate pages:** rotate by 90°, 180°, or 270°, across the whole document or selected pages, including password-protected PDFs.
- **Split PDF:** supports one file per page, groups of N pages, breaks after selected/even/odd pages, approximate target size, and bookmarks with a selected level and optional regular-expression filter. Creates the output folder if needed, accepts a password, preserves compatible structures where possible, and never overwrites existing files. Size is estimated; a single page can exceed the target.
- **PDF to images:** export all pages or selected ranges as PNG or JPEG, with adjustable resolution (72–600 DPI), configurable JPEG quality, password support, and filenames that avoid overwriting existing files.
- **Reorder pages with thumbnails and preview:** every page appears as a thumbnail in a grid; drag to change the order and inspect the selected page in the preview panel. Thumbnails render in the background and track the original page; every page must appear exactly once.
- **Selective watermarks and page numbers:** apply text, numbering, or both to all pages or only selected ranges (for example, `2-4, 7`). Numbering retains the page's original position in the document. Original content is not rasterized.
- **Optimize PDF:** choose lossless stream compression/deduplication or balanced JPEG recompression of opaque raster images with adjustable quality. Transparent and inline images are left unchanged.
- **Batch workflow:** combine rotation, watermark/page numbering, and optimization in one operation, or apply a saved profile to all PDFs in a folder. Each PDF receives an individual result; a failure does not stop the remaining files. Export a CSV report and optionally preserve subfolders. Manual pause takes effect between PDFs; cancellation finishes the current PDF before stopping. A local journal records each completed result to improve recovery after an interruption; checkpoints are isolated by source, profile, inventory, and batch selection. Enable resume to reuse completed PDFs and retry failures. The retry action reruns only failed PDFs that still exist, preserving the remaining results. CSV reports use semicolons when the interface is set to Portuguese or Spanish, and commas in English.
- **Reusable batch profiles:** save, load, and delete named profiles in local preferences, or export/import them as JSON. Schema 2 automatically migrates older schema 1 profiles, preserving their settings and adding a default output suffix. PDF paths and passwords are never included; unknown fields and invalid options are rejected.
- **Safer output handling:** the save dialog adds the PDF extension, prevents choosing a source file as the output, and asks before replacing an existing file.

### Image tools

- **Batch conversion:** JPEG, PNG, WEBP, BMP, and TIFF.
- **Resize:** optional maximum width and height in pixels, preserving aspect ratio and avoiding enlargement of smaller images.
- **Quality controls:** JPEG/WEBP quality setting and ICC profile preservation when compatible with the destination color mode.
- **CMYK and transparency:** convert color modes that are unsupported by the destination format; transparency is composited onto white when exporting to JPEG/BMP.

### Usability, privacy, and reliability

- Desktop interface with sidebar navigation and a PT-BR/English/Spanish language selector, reorderable thumbnail grids with a selected-page preview, reusable batch profiles, intentional item duplication, and a processing indicator. Main dialogs, password prompts, confirmations, and common page-range errors follow the selected language. Common pypdf parsing, Qt PDF rendering, and image-processing errors receive clearer translated messages without exposing internal diagnostics. Passwords are entered through masked fields, are not stored in preferences, and the fields are cleared when an operation starts.
- DPI and margin controls when converting images to PDF.
- Long-running tasks execute outside the main UI thread; the window cannot be closed while a task is running.
- A button opens the output folder when processing finishes.
- Local processing: documents are not uploaded to external services.
- Source files are not replaced by normal processing operations.
- Temporary/atomic writes for PDF operations; splitting stops if an output filename already exists.
- Persistent output permission preference on Linux/macOS: owner-only (0600, recommended default) or shared-readable (0644). Windows permissions are managed by the operating system.
- **Protected PDFs and privacy:** a password is needed to process a protected PDF, but the generated file does not automatically inherit the source document's encryption or restrictions. Re-protect the output if confidentiality is required. Basic document metadata may be preserved.
- **Quality note:** balanced optimization may reduce image quality and cannot guarantee a smaller result for every PDF; keep the original and compare outputs. Watermarks use the built-in Helvetica font and may not support every Unicode character.
- Automated tests and dependency auditing run in GitHub Actions. The workflow validates Windows, Linux, and macOS packages and generates SHA-256 checksums.

## Download portable packages

The **PDF Hub CI, security and packages** workflow tests the app and builds portable packages for Windows x64, Linux x64, and macOS Apple Silicon. On pushes to `main`, download validation artifacts from [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions); permanent releases are created from `v*` tags.

1. For a permanent download, open [Releases](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases) and choose your operating system's package.
2. Until a release is available, open [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions), open the latest **PDF Hub CI, security and packages** run, and confirm it succeeded.
3. Under **Artifacts**, download the desired package: Windows x64, Linux x64, or macOS Apple Silicon.
4. Extract the package. On Windows, run `PDFHub.exe`; on Linux, run `PDFHub`; on macOS, open `PDF Hub.app`.
5. The `.sha256` files can be used to verify the package checksum. For releases, download the checksum beside the same package from the official release page.

The artifact includes the runtime and does not require a separate Python installation. Packages include `LICENSE` and `LICENSES-THIRD-PARTY.md`. Windows may show a security warning for downloaded files; verify the source before running the application.

> GitHub Actions artifacts are temporary and expire according to the configured retention period. Versioned GitHub Releases are created when a tag such as `v0.11.0` is pushed. The executables are not digitally signed/notarized; Windows SmartScreen or macOS Gatekeeper may display a warning.

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
