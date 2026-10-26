# YPDF Portable

Aplicativo desktop para operações locais com arquivos PDF e imagens, com foco em portabilidade no Windows.

## Estado atual

O repositório ainda está em fase inicial. A interface existente é um esqueleto Avalonia e **as operações de PDF e imagem ainda não estão implementadas**. Não distribua uma compilação atual como se já oferecesse essas funções.

## Objetivos

- Processar arquivos localmente, sem enviar documentos para serviços externos.
- Preservar os arquivos originais por padrão.
- Validar entradas e evitar sobrescrita acidental.
- Apresentar mensagens de erro compreensíveis e progresso em operações demoradas.
- Distribuir uma versão portátil para Windows, sem exigir que o usuário instale o .NET.

## Funcionalidades planejadas

### PDF
- Unir documentos.
- Extrair ou dividir páginas.
- Reordenar e girar páginas.
- Otimizar tamanho do arquivo, com indicação de eventuais perdas de qualidade.

### Imagens
- Converter imagens para formatos comuns.
- Redimensionar e girar.
- Ajustar qualidade quando aplicável.
- Converter várias imagens em um único PDF.

As funções serão adicionadas gradualmente e acompanhadas de testes automatizados.

## Desenvolvimento

Requisitos para compilar a partir do código-fonte:

- SDK do .NET 8.
- Windows, Linux ou macOS para desenvolvimento da interface Avalonia.

Na pasta do repositório, execute:

```bash
dotnet restore Ypdf.Desktop.slnx
dotnet build Ypdf.Desktop.slnx --configuration Release
```

Para publicar uma versão portátil para Windows x64:

```bash
dotnet publish Application/Ypdf.Desktop.csproj --configuration Release --runtime win-x64 --self-contained true -p:PublishSingleFile=true
```

O executável publicado ficará no diretório de saída indicado pelo .NET dentro de `Application/bin/Release/net8.0/win-x64/publish/`.

> A publicação portátil e o funcionamento em Windows precisam ser confirmados em uma execução real do pipeline antes de anunciar um release.

## Privacidade

O objetivo é manter o processamento dos documentos no próprio computador. Dependências, atualizações e verificações de versão poderão usar a internet durante instalação ou desenvolvimento; isso não deve implicar envio do conteúdo dos arquivos do usuário.

## Licença

A licença ainda precisa ser definida. Até que exista um arquivo de licença no repositório, não presuma que o código esteja licenciado para redistribuição.
