using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace DocumentTools.Desktop.ViewModels;

public sealed record FileEntry(string FullPath)
{
    public string Name => Path.GetFileName(FullPath);

    public string Folder => Path.GetDirectoryName(FullPath) ?? FullPath;
}

public sealed class MainWindowViewModel : ObservableObject
{
    private FileEntry? _selectedImage;
    private FileEntry? _selectedPdf;
    private string? _extractSourcePath;
    private string _pageRanges = "1-3";
    private string _statusMessage = "Pronto para começar. Selecione uma operação acima.";
    private bool _isBusy;

    public ObservableCollection<FileEntry> Images { get; } = [];

    public ObservableCollection<FileEntry> Pdfs { get; } = [];

    public FileEntry? SelectedImage
    {
        get => _selectedImage;
        set => SetProperty(ref _selectedImage, value);
    }

    public FileEntry? SelectedPdf
    {
        get => _selectedPdf;
        set => SetProperty(ref _selectedPdf, value);
    }

    public string? ExtractSourcePath
    {
        get => _extractSourcePath;
        private set
        {
            if (SetProperty(ref _extractSourcePath, value))
            {
                OnPropertyChanged(nameof(ExtractSourceName));
                OnPropertyChanged(nameof(HasExtractSource));
            }
        }
    }

    public string ExtractSourceName => string.IsNullOrWhiteSpace(ExtractSourcePath)
        ? "Nenhum arquivo selecionado"
        : Path.GetFileName(ExtractSourcePath);

    public bool HasExtractSource => !string.IsNullOrWhiteSpace(ExtractSourcePath);

    public string PageRanges
    {
        get => _pageRanges;
        set => SetProperty(ref _pageRanges, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    public bool IsBusy
    {
        get => _isBusy;
        set => SetProperty(ref _isBusy, value);
    }

    public string ImagesSummary => Images.Count switch
    {
        0 => "Nenhuma imagem adicionada",
        1 => "1 imagem selecionada",
        _ => $"{Images.Count} imagens selecionadas",
    };

    public string PdfsSummary => Pdfs.Count switch
    {
        0 => "Nenhum PDF adicionado",
        1 => "1 PDF adicionado",
        _ => $"{Pdfs.Count} PDFs adicionados",
    };

    public int AddImagePaths(IEnumerable<string> paths)
    {
        int added = 0;
        foreach (string path in paths)
        {
            if (!File.Exists(path) || Images.Any(item => SamePath(item.FullPath, path)))
            {
                continue;
            }

            Images.Add(new FileEntry(path));
            added++;
        }

        OnPropertyChanged(nameof(ImagesSummary));
        StatusMessage = added == 0
            ? "Nenhuma imagem nova foi adicionada."
            : $"{added} imagem(ns) adicionada(s). Você pode mudar a ordem antes de criar o PDF.";
        return added;
    }

    public void RemoveSelectedImage()
    {
        if (SelectedImage is null)
        {
            StatusMessage = "Selecione uma imagem na lista para removê-la.";
            return;
        }

        Images.Remove(SelectedImage);
        SelectedImage = null;
        OnPropertyChanged(nameof(ImagesSummary));
        StatusMessage = "Imagem removida da lista. O arquivo original continua intacto.";
    }

    public void MoveSelectedImage(int offset)
    {
        if (SelectedImage is null)
        {
            StatusMessage = "Selecione uma imagem para mudar sua posição.";
            return;
        }

        int index = Images.IndexOf(SelectedImage);
        int targetIndex = index + offset;
        if (index < 0 || targetIndex < 0 || targetIndex >= Images.Count)
        {
            return;
        }

        Images.Move(index, targetIndex);
        StatusMessage = "Ordem das imagens atualizada.";
    }

    public int AddPdfPaths(IEnumerable<string> paths)
    {
        int added = 0;
        foreach (string path in paths)
        {
            if (!File.Exists(path) ||
                !string.Equals(Path.GetExtension(path), ".pdf", StringComparison.OrdinalIgnoreCase) ||
                Pdfs.Any(item => SamePath(item.FullPath, path)))
            {
                continue;
            }

            Pdfs.Add(new FileEntry(path));
            added++;
        }

        OnPropertyChanged(nameof(PdfsSummary));
        StatusMessage = added == 0
            ? "Nenhum PDF novo foi adicionado."
            : $"{added} PDF(s) adicionado(s). A ordem da lista será mantida na união.";
        return added;
    }

    public void RemoveSelectedPdf()
    {
        if (SelectedPdf is null)
        {
            StatusMessage = "Selecione um PDF na lista para removê-lo.";
            return;
        }

        Pdfs.Remove(SelectedPdf);
        SelectedPdf = null;
        OnPropertyChanged(nameof(PdfsSummary));
        StatusMessage = "PDF removido da lista. O arquivo original continua intacto.";
    }

    public void MoveSelectedPdf(int offset)
    {
        if (SelectedPdf is null)
        {
            StatusMessage = "Selecione um PDF para mudar sua posição.";
            return;
        }

        int index = Pdfs.IndexOf(SelectedPdf);
        int targetIndex = index + offset;
        if (index < 0 || targetIndex < 0 || targetIndex >= Pdfs.Count)
        {
            return;
        }

        Pdfs.Move(index, targetIndex);
        StatusMessage = "Ordem dos PDFs atualizada.";
    }

    public void SelectExtractSource(string path)
    {
        ExtractSourcePath = path;
        StatusMessage = $"PDF selecionado: {Path.GetFileName(path)}. Agora informe as páginas.";
    }

    public void SetStatus(string message)
    {
        StatusMessage = message;
    }

    private static bool SamePath(string first, string second)
    {
        return string.Equals(
            Path.GetFullPath(first),
            Path.GetFullPath(second),
            StringComparison.OrdinalIgnoreCase);
    }
}
