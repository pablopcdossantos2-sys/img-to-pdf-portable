using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Avalonia.Platform.Storage;
using DocumentTools.Desktop.Services;
using DocumentTools.Desktop.ViewModels;

namespace DocumentTools.Desktop.Views;

internal sealed partial class MainWindow : Window
{
    private static readonly FilePickerFileType ImageFileType = new("Imagens (JPG, PNG, BMP)")
    {
        Patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp"],
    };

    private static readonly FilePickerFileType PdfFileType = new("Documentos PDF")
    {
        Patterns = ["*.pdf"],
    };

    private MainWindowViewModel ViewModel => (MainWindowViewModel)DataContext!;

    public MainWindow()
    {
        InitializeComponent();
    }

    private async void OnAddImagesClick(object? sender, RoutedEventArgs e)
    {
        try
        {
            IReadOnlyList<IStorageFile> files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
            {
                Title = "Adicionar imagens",
                AllowMultiple = true,
                FileTypeFilter = [ImageFileType],
            });

            ViewModel.AddImagePaths(files.Select(file => file.Path.LocalPath));
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível selecionar as imagens: {exception.Message}");
        }
    }

    private void OnRemoveImageClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.RemoveSelectedImage();
    }

    private void OnMoveImageUpClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.MoveSelectedImage(-1);
    }

    private void OnMoveImageDownClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.MoveSelectedImage(1);
    }

    private async void OnCreatePdfClick(object? sender, RoutedEventArgs e)
    {
        if (ViewModel.Images.Count == 0)
        {
            ViewModel.SetStatus("Adicione pelo menos uma imagem antes de criar o PDF.");
            return;
        }

        string[] sourcePaths = ViewModel.Images.Select(item => item.FullPath).ToArray();
        string? outputPath = await PickOutputPathAsync("imagens.pdf", sourcePaths);
        if (outputPath is null)
        {
            return;
        }

        ViewModel.IsBusy = true;
        ViewModel.SetStatus("Criando PDF a partir das imagens selecionadas…");
        try
        {
            await Task.Run(() => PdfOperations.CreatePdfFromImages(sourcePaths, outputPath));
            ViewModel.SetStatus($"PDF criado com sucesso: {outputPath}");
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível criar o PDF: {exception.Message}");
        }
        finally
        {
            ViewModel.IsBusy = false;
        }
    }

    private async void OnAddPdfsClick(object? sender, RoutedEventArgs e)
    {
        try
        {
            IReadOnlyList<IStorageFile> files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
            {
                Title = "Adicionar PDFs para unir",
                AllowMultiple = true,
                FileTypeFilter = [PdfFileType],
            });

            ViewModel.AddPdfPaths(files.Select(file => file.Path.LocalPath));
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível selecionar os PDFs: {exception.Message}");
        }
    }

    private void OnRemovePdfClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.RemoveSelectedPdf();
    }

    private void OnMovePdfUpClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.MoveSelectedPdf(-1);
    }

    private void OnMovePdfDownClick(object? sender, RoutedEventArgs e)
    {
        ViewModel.MoveSelectedPdf(1);
    }

    private async void OnMergePdfsClick(object? sender, RoutedEventArgs e)
    {
        if (ViewModel.Pdfs.Count < 2)
        {
            ViewModel.SetStatus("Adicione pelo menos dois PDFs para uni-los.");
            return;
        }

        string[] sourcePaths = ViewModel.Pdfs.Select(item => item.FullPath).ToArray();
        string? outputPath = await PickOutputPathAsync("documentos-unidos.pdf", sourcePaths);
        if (outputPath is null)
        {
            return;
        }

        ViewModel.IsBusy = true;
        ViewModel.SetStatus("Unindo os PDFs. Arquivos grandes podem levar alguns instantes…");
        try
        {
            await Task.Run(() => PdfOperations.MergePdfs(sourcePaths, outputPath));
            ViewModel.SetStatus($"PDFs unidos com sucesso: {outputPath}");
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível unir os PDFs: {exception.Message}");
        }
        finally
        {
            ViewModel.IsBusy = false;
        }
    }

    private async void OnChooseExtractPdfClick(object? sender, RoutedEventArgs e)
    {
        try
        {
            IReadOnlyList<IStorageFile> files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
            {
                Title = "Escolher PDF de origem",
                AllowMultiple = false,
                FileTypeFilter = [PdfFileType],
            });

            if (files.Count > 0)
            {
                ViewModel.SelectExtractSource(files[0].Path.LocalPath);
            }
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível selecionar o PDF: {exception.Message}");
        }
    }

    private async void OnExtractPagesClick(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(ViewModel.ExtractSourcePath))
        {
            ViewModel.SetStatus("Escolha primeiro o PDF de origem.");
            return;
        }

        string sourcePath = ViewModel.ExtractSourcePath;
        string? outputPath = await PickOutputPathAsync(
            $"{Path.GetFileNameWithoutExtension(sourcePath)}-paginas.pdf",
            [sourcePath]);
        if (outputPath is null)
        {
            return;
        }

        string ranges = ViewModel.PageRanges;
        ViewModel.IsBusy = true;
        ViewModel.SetStatus("Extraindo as páginas solicitadas…");
        try
        {
            await Task.Run(() => PdfOperations.ExtractPages(sourcePath, ranges, outputPath));
            ViewModel.SetStatus($"Páginas extraídas com sucesso: {outputPath}");
        }
        catch (Exception exception)
        {
            ViewModel.SetStatus($"Não foi possível extrair as páginas: {exception.Message}");
        }
        finally
        {
            ViewModel.IsBusy = false;
        }
    }

    private async Task<string?> PickOutputPathAsync(string suggestedFileName, IReadOnlyList<string> sources)
    {
        IStorageFile? selectedFile = await StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "Salvar PDF resultante",
            SuggestedFileName = suggestedFileName,
            DefaultExtension = "pdf",
            FileTypeChoices = [PdfFileType],
        });

        if (selectedFile is null)
        {
            ViewModel.SetStatus("Operação cancelada. Nenhum arquivo foi alterado.");
            return null;
        }

        string outputPath = selectedFile.Path.LocalPath;
        if (!string.Equals(Path.GetExtension(outputPath), ".pdf", StringComparison.OrdinalIgnoreCase))
        {
            outputPath += ".pdf";
        }

        if (sources.Any(sourcePath => SamePath(sourcePath, outputPath)))
        {
            ViewModel.SetStatus("Escolha outro nome: o arquivo de saída não pode substituir um dos arquivos originais.");
            return null;
        }

        if (File.Exists(outputPath) && !await ConfirmOverwriteAsync(outputPath))
        {
            ViewModel.SetStatus("Operação cancelada. O arquivo existente foi preservado.");
            return null;
        }

        return outputPath;
    }

    private async Task<bool> ConfirmOverwriteAsync(string outputPath)
    {
        var dialog = new Window
        {
            Title = "Confirmar substituição",
            Width = 440,
            Height = 190,
            MinWidth = 440,
            MinHeight = 190,
            MaxWidth = 440,
            MaxHeight = 190,
            CanResize = false,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
        };

        var content = new StackPanel
        {
            Margin = new Thickness(22),
            Spacing = 16,
        };
        content.Children.Add(new TextBlock
        {
            Text = $"O arquivo “{Path.GetFileName(outputPath)}” já existe. Deseja substituí-lo?",
            TextWrapping = Avalonia.Media.TextWrapping.Wrap,
        });

        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Right,
            Spacing = 8,
        };
        var cancelButton = new Button
        {
            Content = "Cancelar",
            MinWidth = 105,
        };
        var replaceButton = new Button
        {
            Content = "Substituir",
            MinWidth = 105,
            Background = Avalonia.Media.Brushes.CornflowerBlue,
            Foreground = Avalonia.Media.Brushes.White,
        };
        cancelButton.Click += (_, _) => dialog.Close(false);
        replaceButton.Click += (_, _) => dialog.Close(true);
        buttons.Children.Add(cancelButton);
        buttons.Children.Add(replaceButton);
        content.Children.Add(buttons);
        dialog.Content = content;

        return await dialog.ShowDialog<bool>(this);
    }

    private static bool SamePath(string first, string second)
    {
        return string.Equals(
            Path.GetFullPath(first),
            Path.GetFullPath(second),
            StringComparison.OrdinalIgnoreCase);
    }
}
