# Ferramentas de Arquivo

**Idiomas:** Português (Brasil) · [English](README.en.md) · [Español](README.es.md)

Aplicativo desktop para trabalhar com PDFs e imagens localmente, com interface moderna em português brasileiro. A implementação é em **Python, PySide6, pypdf e Pillow**.

## Funcionalidades

### PDFs
- **Imagens para PDF:** converte JPG, JPEG, PNG, BMP, WEBP e TIFF em páginas A4, ajustando automaticamente a orientação e preservando as proporções. Imagens transparentes são compostas sobre branco.
- **Unir PDFs:** combina vários arquivos na ordem escolhida e tenta preservar os marcadores importados.
- **Extrair páginas:** salva páginas específicas ou intervalos como `1-3, 5, 8-10`. Há uma opção para repetir páginas no documento de saída.
- **Girar páginas:** rotação em 90°, 180° ou 270°, em todas as páginas ou somente nas selecionadas.
- **Dividir PDF:** cria um arquivo PDF individual para cada página, criando a pasta de saída caso necessário. Nomes de destino existentes são preservados; se houver conflito, a operação é interrompida.
- **Proteção de saída:** o diálogo acrescenta a extensão PDF, verifica se o destino é um dos arquivos de origem e pede confirmação antes de substituir um arquivo existente.

### Imagens
- **Converter em lote:** JPEG, PNG, WEBP, BMP e TIFF.
- **Redimensionar:** limites opcionais de largura e altura em pixels, preservando a proporção e sem ampliar imagens pequenas.
- **Qualidade:** controle JPEG/WEBP e preservação de perfis ICC quando compatíveis com o modo de cor de destino.
- **CMYK e transparência:** modos que não são aceitos pelo formato de destino são convertidos para formatos compatíveis; a transparência para JPEG/BMP é composta sobre fundo branco.

### Usabilidade, privacidade e robustez
- Interface desktop com abas, ordenação por botões ou arrastar e soltar, duplicação intencional de itens, mensagens em português e indicador de processamento.
- Opções de resolução (DPI) e margem na conversão de imagens para PDF.
- Operações demoradas fora da thread principal; a janela não fecha enquanto uma operação está ativa.
- Botão para abrir a pasta de saída depois de concluir a operação.
- Processamento local: os documentos não são enviados a serviços externos.
- Os arquivos originais não são substituídos pelas operações.
- Gravação temporária/atômica para operações PDF; a divisão interrompe conflitos sem substituir arquivos preexistentes.
- Testes automatizados e auditoria de dependências executados no GitHub Actions. O pipeline também faz um teste de fumaça no executável Windows e publica um checksum SHA-256.

## ROADMAP

Este plano reúne melhorias possíveis para orientar as próximas etapas. A ordem indica prioridades relativas, não prazos garantidos.

### Prioridades

- [ ] **Abrir PDFs protegidos por senha:** adicionar um campo de senha com tratamento seguro, sem registrar a senha em logs nem armazená-la desnecessariamente.
- [ ] **Preservar recursos avançados de PDF:** melhorar a manutenção de marcadores, metadados, formulários, links internos e destinos ao unir, extrair, girar ou dividir documentos.
- [ ] **Controlar páginas de imagens multipágina e animadas:** permitir escolher entre importar apenas o primeiro quadro ou gerar páginas para quadros/páginas adicionais de TIFF e formatos animados compatíveis.
- [ ] **Publicar releases permanentes e versionados:** automatizar releases do GitHub com executável, checksum SHA-256 e notas de versão, para que o download não dependa de artefatos temporários do Actions.
- [ ] **Distribuir pacotes para outros sistemas:** avaliar builds portáteis para macOS e Linux, além do executável Windows x64 atual.
- [ ] **Oferecer opções de permissões de saída:** documentar e, se fizer sentido, permitir configurar as permissões de arquivos gerados em Linux/macOS, que hoje podem ficar restritas ao usuário atual.

## Usar no Windows sem instalar Python

O fluxo **Python CI, security and package** gera um executável portátil para Windows x64 e um checksum SHA-256.

1. Abra a aba [Actions](https://github.com/pablopcdossantos2-sys/img-to-pdf-portable/actions).
2. Entre na execução mais recente chamada **Python CI, security and package** e confirme que terminou com sucesso.
3. Na seção **Artifacts**, baixe `Ferramentas-de-Arquivo-Portable-win-x64`.
4. Extraia o ZIP e execute `FerramentasDeArquivo.exe`.
5. O arquivo `FerramentasDeArquivo.exe.sha256` contém o hash para conferir a integridade do executável.

O artefato contém o runtime necessário e não exige instalação separada do Python. O Windows pode apresentar um aviso de segurança para arquivos baixados; confirme a origem antes de executar.

> O artefato de Actions é temporário e tem prazo de expiração definido pelo GitHub. Um release permanente poderá ser publicado separadamente depois de validar o pacote em uso real.

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
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FerramentasDeArquivo main.py
```

O executável será criado em `dist/FerramentasDeArquivo.exe`. Para verificar se o pacote inicializa a interface e carrega as dependências Qt, execute:

```powershell
.\dist\FerramentasDeArquivo.exe --selftest
```

A opção `--selftest` cria a interface em modo sem janela visível e encerra com código de sucesso se a inicialização funcionar.

