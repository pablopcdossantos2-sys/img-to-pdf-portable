# Ferramentas de Arquivo

Aplicativo desktop para operações locais com PDFs e imagens. A interface é em português brasileiro e foi construída com Avalonia UI; o processamento de documentos usa PDFsharp.

## O que já funciona

- **Imagens para PDF:** transforma várias imagens em páginas A4, preservando a proporção e permitindo reorganizar a sequência antes da conversão.
- **Unir PDFs:** combina dois ou mais documentos na ordem escolhida.
- **Extrair páginas:** salva páginas individuais ou intervalos, por exemplo `1-3, 5, 8-10`.
- **Interface visual:** janela moderna, seleção de arquivos, listas organizáveis, mensagens de status e confirmação antes de substituir um arquivo existente.
- **Proteção dos originais:** as operações criam um novo arquivo; arquivos de origem não podem ser escolhidos como destino.

Formatos de imagem aceitos nesta versão: JPG/JPEG, PNG e BMP. PDFs protegidos por senha e arquivos danificados podem não ser processados. A extração aceita intervalos e páginas separadas por vírgula; intervalos inválidos e páginas repetidas são recusados.

## Privacidade

O processamento dos documentos acontece localmente no computador. A aplicação não envia os arquivos escolhidos a um serviço externo. A conexão com a internet é necessária para baixar dependências ao compilar o código-fonte, mas não para executar as operações depois de publicada.

## Usar no Windows

A cada atualização, o fluxo do GitHub Actions compila e publica um artefato portátil para Windows x64.

1. Abra a aba **Actions** deste repositório.
2. Selecione a execução mais recente do fluxo **Build and package**.
3. Na seção **Artifacts**, baixe `DocumentTools-Portable-win-x64`.
4. Extraia o ZIP para uma pasta e execute `DocumentTools.Desktop.exe`.

O artefato é self-contained: não exige que o .NET seja instalado separadamente. O Windows pode exibir um aviso de segurança para executáveis baixados da internet; confirme a origem do arquivo antes de executá-lo.

## Compilar a partir do código-fonte

Recomendado: SDK do .NET 10. O projeto tem como alvo o .NET 8 e usa o formato de solução `.slnx`.

Na pasta do repositório, execute:

```powershell
dotnet restore DocumentTools.slnx
dotnet build DocumentTools.slnx --configuration Release
```

Para gerar uma publicação portátil para Windows x64:

```powershell
dotnet publish Application/DocumentTools.Desktop.csproj --configuration Release --runtime win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true --output artifacts/DocumentTools-Portable-win-x64
```

## Próximas etapas

Funcionalidades que podem ser adicionadas nas próximas versões: girar e reordenar páginas de PDF, converter PDF para imagens, redimensionar/comprimir imagens, dividir um documento em vários arquivos e adicionar processamento em lote com progresso detalhado.

## Licença

Este repositório inclui um arquivo `LICENSE`. Verifique os termos dessa licença e das dependências antes de redistribuir versões modificadas.
