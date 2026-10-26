using System.Globalization;
using PdfSharp;
using PdfSharp.Drawing;
using PdfSharp.Pdf;
using PdfSharp.Pdf.IO;

namespace DocumentTools.Desktop.Services;

/// <summary>
/// Performs local PDF operations without uploading document contents anywhere.
/// </summary>
internal static class PdfOperations
{
    private static readonly HashSet<string> SupportedImageExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
    };

    internal static void CreatePdfFromImages(IReadOnlyList<string> imagePaths, string outputPath)
    {
        ArgumentNullException.ThrowIfNull(imagePaths);
        if (imagePaths.Count == 0)
        {
            throw new ArgumentException("Selecione pelo menos uma imagem.", nameof(imagePaths));
        }

        ValidateOutputPath(outputPath, imagePaths);
        foreach (string imagePath in imagePaths)
        {
            if (!File.Exists(imagePath))
            {
                throw new FileNotFoundException("Uma das imagens selecionadas não foi encontrada.", imagePath);
            }

            if (!SupportedImageExtensions.Contains(Path.GetExtension(imagePath)))
            {
                throw new NotSupportedException(
                    $"Formato de imagem não suportado: {Path.GetFileName(imagePath)}. Use JPG, PNG ou BMP.");
            }
        }

        SaveAtomically(outputPath, temporaryPath =>
        {
            using var document = new PdfDocument();
            document.Info.Title = "PDF criado a partir de imagens";

            foreach (string imagePath in imagePaths)
            {
                using XImage image = XImage.FromFile(imagePath);
                PdfPage page = document.AddPage();
                page.Size = PageSize.A4;
                page.Orientation = image.PointWidth > image.PointHeight
                    ? PageOrientation.Landscape
                    : PageOrientation.Portrait;

                const double margin = 28;
                double availableWidth = page.Width.Point - (margin * 2);
                double availableHeight = page.Height.Point - (margin * 2);
                double scale = Math.Min(
                    availableWidth / image.PointWidth,
                    availableHeight / image.PointHeight);
                double drawWidth = image.PointWidth * scale;
                double drawHeight = image.PointHeight * scale;
                double x = (page.Width.Point - drawWidth) / 2;
                double y = (page.Height.Point - drawHeight) / 2;

                using XGraphics graphics = XGraphics.FromPdfPage(page);
                graphics.DrawImage(image, x, y, drawWidth, drawHeight);
            }

            document.Save(temporaryPath);
        });
    }

    internal static void MergePdfs(IReadOnlyList<string> pdfPaths, string outputPath)
    {
        ArgumentNullException.ThrowIfNull(pdfPaths);
        if (pdfPaths.Count < 2)
        {
            throw new ArgumentException("Selecione pelo menos dois arquivos PDF para unir.", nameof(pdfPaths));
        }

        ValidateOutputPath(outputPath, pdfPaths);
        using var outputDocument = new PdfDocument();
        outputDocument.Info.Title = "PDFs unidos";

        SaveAtomically(outputPath, temporaryPath =>
        {
            foreach (string pdfPath in pdfPaths)
            {
                if (!File.Exists(pdfPath))
                {
                    throw new FileNotFoundException("Um dos arquivos PDF selecionados não foi encontrado.", pdfPath);
                }

                using PdfDocument inputDocument = PdfReader.Open(pdfPath, PdfDocumentOpenMode.Import);
                for (int pageIndex = 0; pageIndex < inputDocument.PageCount; pageIndex++)
                {
                    outputDocument.AddPage(inputDocument.Pages[pageIndex]);
                }
            }

            if (outputDocument.PageCount == 0)
            {
                throw new InvalidDataException("Os arquivos selecionados não contêm páginas.");
            }

            outputDocument.Save(temporaryPath);
        });
    }

    internal static void ExtractPages(string inputPath, string pageRanges, string outputPath)
    {
        if (!File.Exists(inputPath))
        {
            throw new FileNotFoundException("O arquivo PDF selecionado não foi encontrado.", inputPath);
        }

        ValidateOutputPath(outputPath, [inputPath]);

        using PdfDocument inputDocument = PdfReader.Open(inputPath, PdfDocumentOpenMode.Import);
        IReadOnlyList<int> pageIndexes = ParsePageRanges(pageRanges, inputDocument.PageCount);
        using var outputDocument = new PdfDocument();
        outputDocument.Info.Title = "Páginas extraídas";

        SaveAtomically(outputPath, temporaryPath =>
        {
            foreach (int pageIndex in pageIndexes)
            {
                outputDocument.AddPage(inputDocument.Pages[pageIndex]);
            }

            outputDocument.Save(temporaryPath);
        });
    }

    internal static IReadOnlyList<int> ParsePageRanges(string pageRanges, int pageCount)
    {
        if (string.IsNullOrWhiteSpace(pageRanges))
        {
            throw new ArgumentException("Informe páginas, por exemplo: 1-3, 5, 8-10.", nameof(pageRanges));
        }

        if (pageCount < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(pageCount), "O PDF não possui páginas.");
        }

        var indexes = new List<int>();
        var seen = new HashSet<int>();
        string[] segments = pageRanges.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (segments.Length == 0)
        {
            throw new FormatException("O intervalo de páginas está vazio.");
        }

        foreach (string segment in segments)
        {
            string[] endpoints = segment.Split('-', StringSplitOptions.TrimEntries);
            if (endpoints.Length is < 1 or > 2 ||
                !int.TryParse(endpoints[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out int start))
            {
                throw new FormatException($"Intervalo de páginas inválido: '{segment}'.");
            }

            int end = start;
            if (endpoints.Length == 2 &&
                !int.TryParse(endpoints[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out end))
            {
                throw new FormatException($"Intervalo de páginas inválido: '{segment}'.");
            }

            if (start < 1 || end < start || end > pageCount)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(pageRanges),
                    $"O intervalo '{segment}' precisa estar entre 1 e {pageCount}.");
            }

            for (int pageNumber = start; pageNumber <= end; pageNumber++)
            {
                int pageIndex = pageNumber - 1;
                if (!seen.Add(pageIndex))
                {
                    throw new FormatException($"A página {pageNumber} foi informada mais de uma vez.");
                }

                indexes.Add(pageIndex);
            }
        }

        return indexes;
    }

    private static void ValidateOutputPath(string outputPath, IReadOnlyList<string> sourcePaths)
    {
        if (string.IsNullOrWhiteSpace(outputPath))
        {
            throw new ArgumentException("Escolha o caminho do arquivo de saída.", nameof(outputPath));
        }

        string fullOutputPath = Path.GetFullPath(outputPath);
        if (sourcePaths.Any(sourcePath => string.Equals(
            Path.GetFullPath(sourcePath),
            fullOutputPath,
            StringComparison.OrdinalIgnoreCase)))
        {
            throw new IOException("O arquivo de saída não pode substituir um dos arquivos de origem.");
        }

        string? directory = Path.GetDirectoryName(fullOutputPath);
        if (directory is null || !Directory.Exists(directory))
        {
            throw new DirectoryNotFoundException("A pasta de destino não existe.");
        }
    }

    private static void SaveAtomically(string outputPath, Action<string> save)
    {
        string fullOutputPath = Path.GetFullPath(outputPath);
        string outputDirectory = Path.GetDirectoryName(fullOutputPath)
            ?? throw new DirectoryNotFoundException("A pasta de destino não existe.");
        string temporaryPath = Path.Combine(
            outputDirectory,
            $".document-tools-{Guid.NewGuid():N}.tmp.pdf");

        try
        {
            save(temporaryPath);
            File.Move(temporaryPath, fullOutputPath, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporaryPath))
            {
                File.Delete(temporaryPath);
            }
        }
    }
}
