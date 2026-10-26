using System.Buffers.Binary;
using DocumentTools.Desktop.Services;
using PdfSharp;
using PdfSharp.Drawing;
using PdfSharp.Pdf;
using PdfSharp.Pdf.IO;
using Xunit;

namespace DocumentTools.Tests;

public sealed class PdfOperationsTests
{
    [Fact]
    public void ParsePageRanges_ExpandsRangesAndPreservesOrder()
    {
        IReadOnlyList<int> result = PdfOperations.ParsePageRanges("3, 1-2, 5, 8-9", 9);

        Assert.Equal(new[] { 2, 0, 1, 4, 7, 8 }, result);
    }

    [Fact]
    public void ParsePageRanges_RejectsDuplicatePages()
    {
        Assert.Throws<FormatException>(() => PdfOperations.ParsePageRanges("1, 1-2", 4));
    }

    [Fact]
    public void ParsePageRanges_RejectsPagesOutsideDocument()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => PdfOperations.ParsePageRanges("2-5", 4));
    }

    [Fact]
    public void CreatePdfFromImages_CreatesOnePagePerImage()
    {
        using var directory = new TemporaryDirectory();
        string imagePath = Path.Combine(directory.Path, "pixel.bmp");
        string outputPath = Path.Combine(directory.Path, "images.pdf");
        WriteOnePixelBitmap(imagePath);

        PdfOperations.CreatePdfFromImages([imagePath], outputPath);

        using PdfDocument output = PdfReader.Open(outputPath, PdfDocumentOpenMode.Import);
        Assert.Equal(1, output.PageCount);
        Assert.True(output.Pages[0].Width.Point > 500);
        Assert.True(output.Pages[0].Height.Point > 700);
    }

    [Fact]
    public void MergePdfs_CombinesAllPagesInSourceOrder()
    {
        using var directory = new TemporaryDirectory();
        string first = CreatePdf(directory.Path, "first.pdf", [120, 130]);
        string second = CreatePdf(directory.Path, "second.pdf", [220, 230, 240]);
        string outputPath = Path.Combine(directory.Path, "merged.pdf");

        PdfOperations.MergePdfs([first, second], outputPath);

        using PdfDocument output = PdfReader.Open(outputPath, PdfDocumentOpenMode.Import);
        Assert.Equal(5, output.PageCount);
        Assert.Equal(120, output.Pages[0].Width.Point);
        Assert.Equal(130, output.Pages[1].Width.Point);
        Assert.Equal(220, output.Pages[2].Width.Point);
    }

    [Fact]
    public void ExtractPages_KeepsRequestedPageOrder()
    {
        using var directory = new TemporaryDirectory();
        string input = CreatePdf(directory.Path, "input.pdf", [110, 120, 130, 140, 150]);
        string outputPath = Path.Combine(directory.Path, "extracted.pdf");

        PdfOperations.ExtractPages(input, "5, 2-3", outputPath);

        using PdfDocument output = PdfReader.Open(outputPath, PdfDocumentOpenMode.Import);
        Assert.Equal(3, output.PageCount);
        Assert.Equal(150, output.Pages[0].Width.Point);
        Assert.Equal(120, output.Pages[1].Width.Point);
        Assert.Equal(130, output.Pages[2].Width.Point);
    }

    private static string CreatePdf(string directory, string fileName, IReadOnlyList<double> pageWidths)
    {
        string path = Path.Combine(directory, fileName);
        using var document = new PdfDocument();
        foreach (double width in pageWidths)
        {
            PdfPage page = document.AddPage();
            page.Width = XUnit.FromPoint(width);
            page.Height = XUnit.FromPoint(300);
        }

        document.Save(path);
        return path;
    }

    private static void WriteOnePixelBitmap(string path)
    {
        byte[] bitmap = new byte[58];
        bitmap[0] = (byte)'B';
        bitmap[1] = (byte)'M';
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(2, 4), bitmap.Length);
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(10, 4), 54);
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(14, 4), 40);
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(18, 4), 1);
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(22, 4), 1);
        BinaryPrimitives.WriteUInt16LittleEndian(bitmap.AsSpan(26, 2), 1);
        BinaryPrimitives.WriteUInt16LittleEndian(bitmap.AsSpan(28, 2), 24);
        BinaryPrimitives.WriteInt32LittleEndian(bitmap.AsSpan(34, 4), 4);
        bitmap[54] = 0;
        bitmap[55] = 0;
        bitmap[56] = 255;
        bitmap[57] = 0;
        File.WriteAllBytes(path, bitmap);
    }

    private sealed class TemporaryDirectory : IDisposable
    {
        internal TemporaryDirectory()
        {
            Path = System.IO.Path.Combine(
                System.IO.Path.GetTempPath(),
                $"DocumentTools.Tests-{Guid.NewGuid():N}");
            Directory.CreateDirectory(Path);
        }

        internal string Path { get; }

        public void Dispose()
        {
            if (Directory.Exists(Path))
            {
                Directory.Delete(Path, recursive: true);
            }
        }
    }
}
