# PDF Hub

**Idiomas:** Português (Brasil) · [English](README.en.md) · [Español](README.es.md)

Aplicativo desktop para trabalhar com PDFs e imagens localmente, desenvolvido com **Python, PySide6, pypdf, Pillow e ReportLab**. A interface pode ser alternada entre português brasileiro, inglês e espanhol; a preferência é salva localmente.

## Funcionalidades

### PDFs
- **Imagens para PDF:** converte JPG, JPEG, PNG, BMP, WEBP, TIFF e GIF em páginas A4, ajustando automaticamente a orientação e preservando as proporções. Por padrão, importa todas as páginas/quadros dos arquivos multipágina ou animados, com opção para usar apenas o primeiro. Imagens transparentes são compostas sobre branco.
- **Unir PDFs:** combina arquivos na ordem escolhida, solicita senhas para PDFs protegidos e tenta preservar marcadores, metadados e referências internas compatíveis.
- **Extrair páginas:** salva páginas específicas ou intervalos como `1-3, 5, 8-10`, permite repetir páginas e aceita senha. A estrutura de navegação e as anotações são preservadas na medida do possível, com remapeamento para as páginas mantidas.
- **Girar páginas:** rotação em 90°, 180° ou 270°, em todas as páginas ou somente nas selecionadas, inclusive em PDFs protegidos por senha.
- **Dividir PDF:** cria um arquivo PDF individual para cada página, criando a pasta de saída caso necessário. Aceita senha e tenta conservar metadados, marcadores e anotações associados à página. Nomes de destino existentes são preservados; se houver conflito, a operação é interrompida.
- **Reordenar páginas com prévia:** carregue um PDF, arraste as páginas e confira a página selecionada no painel de prévia. A prévia acompanha a página de origem mesmo depois de arrastar os itens; cada página precisa permanecer exatamente uma vez.
- **Marca d'água e numeração seletivas:** adicione texto, numeração ou ambos a todas as páginas ou apenas a intervalos (por exemplo, `2-4, 7`). Ao selecionar um intervalo, a numeração continua indicando a posição original no documento. O conteúdo original não é rasterizado.
- **Otimizar PDF:** modo sem perdas para comprimir streams e remover objetos repetidos; modo equilibrado para recomprimir imagens opacas em JPEG com qualidade ajustável. Imagens com transparência e imagens inline são mantidas sem recompressão.
- **Fluxo em lote:** combine rotação, marca d'água/numeração e otimização em uma única operação. As etapas seguem uma ordem definida, usam temporários locais e só concluem a gravação final quando a sequência termina sem erro.
- **Proteção de saída:** o diálogo acrescenta a extensão PDF, verifica se o destino é um dos arquivos de origem e pede confirmação antes de substituir um arquivo existente.

### Imagens
- **Converter em lote:** JPEG, PNG, WEBP, BMP e TIFF.
- **Redimensionar:** limites opcionais de largura e altura em pixels, preservando a proporção e sem ampliar imagens pequenas.
- **Qualidade:** controle JPEG/WEBP e preservação de perfis ICC quando compatíveis com o modo de cor de destino.
- **CMYK e transparência:** modos que não são aceitos pelo formato de destino são convertidos para formatos compatíveis; a transparência para JPEG/BMP é composta sobre fundo branco.

### Usabilidade, privacidade e robustez
- Interface desktop com abas e seletor de idioma (PT-BR/EN/ES), listas reordenáveis, painel de prévia da página selecionada, duplicação intencional de itens e indicador de processamento. Os diálogos principais, prompts de senha, confirmações e erros comuns de página também acompanham o idioma. As senhas são digitadas em campos protegidos, não são salvas nas preferências e os campos são limpos ao iniciar a operação.
- Opções de resolução (DPI) e margem na conversão de imagens para PDF.
- Operações demoradas fora da thread principal; a janela não fecha enquanto uma operação está ativa.
- Botão para abrir a pasta de saída depois de concluir a operação.
- Processamento local: os documentos não são enviados a serviços externos.
- Os arquivos originais não são substituídos pelas operações.
- Gravação temporária/atômica para operações PDF; a divisão interrompe conflitos sem substituir arquivos preexistentes.
- Preferência persistente para arquivos gerados em Linux/macOS: somente o usuário (0600, padrão recomendado) ou leitura compartilhada (0644). No Windows, as permissões seguem as regras do sistema.
- **Atenção à qualidade:** o modo equilibrado de otimização pode reduzir a qualidade de imagens e não garante que todos os PDFs fiquem menores; mantenha o original e compare o resultado. A marca d'água usa fonte Helvetica incorporada e pode não aceitar todos os caracteres Unicode.
- Testes automatizados e auditoria de dependências executados no GitHub Actions. O pipeline valida os pacotes de Windows, Linux e macOS e gera checksums SHA-256.


## Baixar pacotes portáteis

O fluxo **PDF Hub CI, security and packages** testa o projeto e gera pacotes portáteis para Windows x64, Linux x64 e macOS Apple Silicon. Em pushes para `main`, consulte [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions) para baixar artefatos de validação; releases permanentes são geradas a partir de tags `v*`.

1. Para um download duradouro, abra a seção [Releases](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/releases) e baixe o pacote do seu sistema operacional.
2. Antes de uma release estar disponível, abra [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions), entre na execução mais recente chamada **PDF Hub CI, security and packages** e confirme que terminou com sucesso.
3. Na seção **Artifacts**, baixe o pacote da plataforma desejada: Windows x64, Linux x64 ou macOS Apple Silicon.
4. Extraia o arquivo. No Windows, execute `PDFHub.exe`; no Linux, execute `PDFHub`; no macOS, abra `PDF Hub.app`.
5. Os arquivos `.sha256` permitem verificar o checksum do pacote. Nas releases, compare o checksum com o mesmo pacote baixado da fonte oficial.

O artefato contém o runtime necessário e não exige instalação separada do Python. O Windows pode apresentar um aviso de segurança para arquivos baixados; confirme a origem antes de executar.

> Os artefatos de Actions são temporários e expiram conforme a retenção configurada no GitHub. Releases versionadas são criadas quando uma tag como `v0.5.0` é enviada ao repositório. Os executáveis não são assinados/notarizados digitalmente; Windows SmartScreen e macOS Gatekeeper podem exibir avisos.

## Executar a partir do código-fonte

Requisitos: Windows, macOS ou Linux e Python 3.11 ou superior.

A forma mais simples no Windows, após instalar Python 3.11 ou superior, é dar duplo clique em `instalar-e-iniciar.bat`. O script cria o ambiente isolado, instala as dependências e abre o aplicativo. Nas próximas execuções, use `executar-aplicativo.bat`. Na primeira instalação, é necessária uma conexão com a internet.

Também é possível executar manualmente:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

O ambiente virtual `.venv` não deve ser copiado para outra pasta ou computador. Se o projeto for movido e o ambiente deixar de funcionar, apague a pasta `.venv` e execute novamente `instalar-e-iniciar.bat`.

Se preferir ativar o ambiente virtual no PowerShell e a política de execução bloquear `Activate.ps1`, use apenas na sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
```

No macOS ou Linux, use `python3 -m venv .venv`, `source .venv/bin/activate` e depois `python -m pip install -r requirements.txt`.

## Testes e criação do executável

Instale as dependências de desenvolvimento e rode os testes e a auditoria:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip_audit --local
```

Para gerar o executável no Windows, use o mesmo comando do CI:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PDFHub main.py
```

O executável será criado em `dist/PDFHub.exe`. Para verificar se o pacote inicializa a interface e carrega as dependências Qt, execute:

```powershell
.\dist\PDFHub.exe --selftest
```

A opção `--selftest` cria a interface em modo sem janela visível e encerra com código de sucesso se a inicialização funcionar.

## ROADMAP

### Concluído até a versão 0.5.0

- [x] **Interface multilíngue:** seletor de idioma com português brasileiro, inglês e espanhol, incluindo as abas e os principais controles.
- [x] **Reorganização visual:** arraste as páginas na lista e salve o PDF na nova ordem; todas as páginas são exigidas exatamente uma vez.
- [x] **Compressão/otimização:** modo sem perdas para streams e objetos duplicados, e modo equilibrado para recompressão JPEG com qualidade configurável. A recompressão pode alterar a aparência das imagens e não garante redução em todos os documentos.
- [x] **Marca d'água e numeração por intervalo:** escolha páginas específicas ou deixe o campo vazio para aplicar ao documento inteiro; a numeração preserva a referência à página original.
- [x] **Prévia durante a reorganização:** painel que renderiza a página selecionada e acompanha o número original da página após reordenar.
- [x] **Fluxo em lote:** combine rotação, marca d'água/numeração e otimização sem gerar manualmente arquivos intermediários.

### Próximas melhorias possíveis

- [ ] Miniaturas de todas as páginas diretamente na lista de reorganização, além da prévia da página selecionada.
- [ ] Traduções para mensagens excepcionais emitidas por bibliotecas externas e formatos PDF incomuns.
