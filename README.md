# Ferramentas de Arquivo

Aplicativo desktop para trabalhar com PDFs e imagens localmente, com uma interface moderna em português brasileiro. O projeto agora usa **Python, PySide6, pypdf e Pillow**.

## O que já funciona

### PDFs
- **Unir PDFs:** combina vários arquivos na ordem escolhida.
- **Extrair páginas:** seleciona páginas e intervalos, como `1-3, 5, 8-10`, preservando a ordem informada.
- **Girar páginas:** rotação em 90°, 180° ou 270°, em todas as páginas ou somente nas selecionadas.
- **Dividir PDF:** cria um arquivo PDF individual para cada página. A função se recusa a sobrescrever nomes que já existam na pasta de destino.
- **Imagens para PDF:** cada imagem vira uma página A4; orientação e proporção são preservadas, com margens configuráveis no código.

### Imagens
- **Converter e redimensionar em lote:** JPEG, PNG, WEBP, BMP e TIFF.
- **Limitar dimensões:** define largura e altura máximas em pixels, preservando a proporção e sem ampliar imagens menores.
- **Qualidade:** controle para formatos com compressão com perdas, como JPEG e WEBP.

### Experiência e segurança
- Interface desktop com abas, listas organizáveis, mensagens de status e indicador de processamento.
- Operações longas executadas fora da thread principal da interface.
- Processamento local; os documentos não são enviados a serviços externos.
- Arquivos de origem protegidos contra substituição acidental.
- Arquivos intermediários temporários e gravação atômica para operações PDF.
- Testes automatizados executados no GitHub Actions antes da geração do executável portátil.

PDFs danificados ou protegidos por senha podem ser recusados. A conversão de imagens depende dos formatos suportados pela versão instalada do Pillow.

## Usar no Windows sem instalar Python

O fluxo **Python CI and package** gera o executável portátil para Windows x64.

1. Abra a aba [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions).
2. Entre na execução mais recente com o nome **Python CI and package** e confirme que ela terminou com sucesso.
3. Na seção **Artifacts**, baixe `DocumentTools-Portable-win-x64`.
4. Extraia o arquivo ZIP e execute `DocumentTools.exe`.

O executável contém o runtime necessário e não requer uma instalação separada do Python. O Windows pode mostrar um aviso de segurança para arquivos baixados; confira a origem antes de executar.

> O artefato de Actions é temporário e tem prazo de expiração definido pelo GitHub. Um release permanente poderá ser publicado separadamente depois de validar o pacote em uso real no Windows.

## Executar a partir do código-fonte

Requisitos: Windows, macOS ou Linux e Python 3.13 recomendado (Python 3.11 ou superior é declarado no projeto).

No Windows, se você já instalou o Python 3.13, pode dar duplo clique em `instalar-e-iniciar.bat`. Ele prepara o ambiente isolado, instala as dependências e abre a aplicação. Nas próximas vezes, use `executar-aplicativo.bat`. O primeiro uso precisa de internet para baixar os pacotes Python.

Na pasta do repositório, execute:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

No macOS ou Linux, a ativação do ambiente virtual usa:

```bash
source .venv/bin/activate
```

### Testes e compilação do executável

Instale as dependências de desenvolvimento e execute os testes:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Para gerar o executável localmente no Windows:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DocumentTools --collect-all PySide6 --collect-all shiboken6 main.py
```

O executável será criado em `dist/DocumentTools.exe`.

## Estrutura principal

- `main.py`: ponto de entrada da aplicação.
- `document_tools/gui.py`: interface PySide6.
- `document_tools/pdf_ops.py`: operações PDF e imagem.
- `tests/`: testes automatizados.
- `requirements.txt`: dependências de execução.
- `requirements-dev.txt`: testes e empacotamento.
- `.github/workflows/build.yml`: testes e geração do executável Windows.

## Licença

O projeto usa a GNU AGPL v3, conforme o arquivo `LICENSE`. As dependências têm seus próprios termos: consulte [LICENSES-THIRD-PARTY.md](LICENSES-THIRD-PARTY.md), em especial as condições aplicáveis às bibliotecas Qt incluídas no executável.
