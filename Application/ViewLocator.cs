using System;
using System.Diagnostics.CodeAnalysis;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using DocumentTools.Desktop.ViewModels;

namespace DocumentTools.Desktop;

[RequiresUnreferencedCode(
    "Default implementation of ViewLocator involves reflection which may be trimmed away.",
    Url = "https://docs.avaloniaui.net/docs/concepts/view-locator")]
internal sealed class ViewLocator : IDataTemplate
{
    public Control? Build(object? param)
    {
        if (param is null)
        {
            return null;
        }

        string paramTypeFullName = param.GetType().FullName ?? string.Empty;
        string name = paramTypeFullName.Replace("ViewModel", "View", StringComparison.Ordinal);
        Type? type = Type.GetType(name);

        if (type is not null && Activator.CreateInstance(type) is Control control)
        {
            return control;
        }

        return new TextBlock
        {
            Text = $"View not found: {name}",
        };
    }

    public bool Match(object? data)
    {
        return data is ViewModelBase;
    }
}
