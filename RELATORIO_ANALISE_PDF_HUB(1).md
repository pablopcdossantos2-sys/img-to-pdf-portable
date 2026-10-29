# Relatório de Análise — PDF Hub v0.11.1

> **Escopo desta execução: SOMENTE a PARTE 2 de 5** (Imagens, renderização e tratamento de erros).
> As Partes 1, 3, 4 e 5 **não foram analisadas** neste relatório; suas seções aparecem marcadas como "NÃO ANALISADA" para que o relatório final possa ser consolidado depois sem renumerar IDs.

## 0. Instruções para a IA que vai corrigir (copie literalmente)
- Corrija UM achado por vez, na ordem da seção 3; após cada um rode `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
- Adicione/ajuste os testes indicados; não remova testes existentes sem justificar (exceto se o achado disser que o teste está errado).
- Não altere comportamento público documentado no README sem atualizar README (pt/en/es).
- Preserve compatibilidade com Python 3.11–3.14 e com as versões fixadas.
- Em caso de conflito entre achados, siga o campo "Depende de / Conflita com".
- Se uma correção proposta se mostrar inadequada, implemente a alternativa e documente o motivo no commit.

Instruções adicionais específicas deste relatório:
- Todas as reproduções foram executadas com **Pillow 12.3.0, pypdf 6.17.0, reportlab 5.0.1, Python 3.13.18** (não as versões fixadas — ver seção 2). **Reexecute cada script de `repros/` com as versões fixadas (Pillow 13.0.0 etc.) antes de corrigir** e confirme que o sintoma continua.
- Números de linha referem-se ao ZIP `img-to-pdf-portable-main` recebido (v0.11.1), sem nenhuma modificação.
- Scripts de reprodução: `repros/`. Execute com `PDFHUB_REPO=<raiz do repo> python repros/<script>.py` (o helper `_common.py` põe a raiz no `sys.path`).

## 1. Resumo executivo

### 1.1 Delimitação das 5 partes e parte analisada
| Nº | Parte | Escopo (arquivos / trechos) | Situação neste relatório |
|---|---|---|---|
| 1 | Núcleo de operações em PDF | `pdf_ops.py`: `parse_page_ranges`, `_normalise_pdf_paths`, `_atomic_pdf_save`, `_open_reader`, merge/mix/insert/extract/delete/rotate/`split_pdf`/reorder/optimize/stamp/pipeline (≈ l.1–197 e 325–748, 872–1195) | **NÃO ANALISADA** |
| **2** | **Imagens, renderização e tratamento de erros** | **`pdf_ops.py`: `_normalise_high_bit_depth` (l.198), `_flatten_to_rgb` (l.221), `_resize_to_a4` (l.238), `images_to_pdf` (l.258–322), `_format_image_for_output` (l.749), `convert_image` (l.772–869); `pdf_rendering.py` (111 l.), `image_resolution.py` (68 l.), `errors.py` (31 l.)** | **ANALISADA (esta execução)** |
| 3 | Casca da aplicação (GUI infra, i18n, tema, workers), build/CI, distribuição | `gui.py` ≈ l.1–2146, `main.py`, `.github/`, `pyproject.toml`, `requirements*.txt`, `*.bat`, licenças, READMEs | **NÃO ANALISADA** |
| 4 | Abas de operação individual (GUI) | `gui.py` ≈ l.2147–3468 | **NÃO ANALISADA** |
| 5 | Lote, perfis, histórico, PDF→imagens e Converter imagens (módulos de apoio + GUI) | `batch_processing.py`, `report_history.py`, `profiles.py`, `gui.py` ≈ l.3469–4773 | **NÃO ANALISADA** |

Fronteira prática: para a Parte 2 li também, **apenas para checar contratos**, os pontos da GUI que chamam suas funções (`gui.py` l.1344–1362 `OperationWorker`, l.1989–1992 `_operation_failed`, l.2218–2247 DPI recomendado, l.4498–4538 PDF→imagens, l.4710–4762 Converter imagens). Defeitos de GUI encontrados lá que pertencem a outras partes estão em §5 como transversais (HIPÓTESE para a parte dona).

### 1.2 Resultado
- **Ambiente:** sandbox sem acesso ao PyPI (proxy devolve 403) → versões fixadas **não** instaláveis, **PySide6 ausente**. Rodei os testes que não dependem de Qt: `tests/test_pdf_ops.py`, `test_image_resolution.py`, `test_errors.py` → **100 passaram, 0 falharam** (inclusive com `-W error::DeprecationWarning`). `test_pdf_rendering.py`, `test_gui.py` e `main.py` **não puderam ser executados**; `pdf_rendering.py` foi analisado só por leitura.
- **Achados da Parte 2: 18** — **1 ALTA, 12 MÉDIA, 5 BAIXA, 0 CRÍTICA.** Confirmados por execução: 14; prováveis (leitura de código): 3 (P2-005, P2-013, P2-014); hipótese: 1 (P2-015).
- Todo o código dos módulos da Parte 2 foi lido linha a linha; testes correspondentes lidos e lacunas listadas na seção 6.
- **5 riscos mais importantes:**
  1. **P2-001 (ALTA)** — fotos JPEG de celular com formato MPO (mapa de ganho/profundidade) geram **páginas extras** no PDF por padrão (`all_frames=True`).
  2. **P2-004 (MÉDIA)** — todo PNG/BMP/TIFF/GIF vira JPEG q95 no PDF (perda silenciosa; capturas de tela com texto ficam maiores *e* piores que em compressão sem perdas).
  3. **P2-002/P2-003 (MÉDIA)** — o cálculo de DPI recomendado roda na thread da GUI, decodifica **todos os pixels** só para ler o tamanho (1,75 s para 8 fotos de 24 MP; refeito para a lista inteira a cada inclusão/remoção) e deixa escapar `DecompressionBombError` sem tratamento.
  4. **P2-009/P2-010 (MÉDIA)** — `errors.py` esconde causas acionáveis (imagem truncada, disco cheio, memória) atrás de "detalhes internos ocultados" e, ao mesmo tempo, repassa texto cru de bibliotecas em inglês (`ValueError`/`UnicodeError`).
  5. **P2-007 (MÉDIA)** — normalização de imagens `I`/`F` estica o contraste por imagem, contradizendo o próprio comentário do código (tons mudam silenciosamente e diferem de página para página).

## 2. Ambiente e linha de base
**Versões efetivamente usadas** (≠ fixadas): Python 3.13.18; Pillow 12.3.0 (fixado: 13.0.0); pypdf 6.17.0 (fixado: 6.21.2); reportlab 5.0.1 (fixado: 5.1.0); pytest 9.1.1 (igual). **Ausentes:** PySide6, cryptography fixada, pip-audit, ruff, pyflakes, PyInstaller.

**Comandos e resultados**
```
pip install -r requirements.txt            -> falha: "-e .[dev]" exige setuptools>=77 (indisponível)
pip install PySide6==6.12.0 ...            -> "Tunnel connection failed: 403 Forbidden" (pypi.org bloqueado pelo proxy)
python3 -m pytest -q tests/test_pdf_ops.py tests/test_image_resolution.py tests/test_errors.py
                                           -> 100 passed
python3 -W error::DeprecationWarning -W error::PendingDeprecationWarning -m pytest (mesmos arquivos)
                                           -> 100 passed
python3 -m compileall -q (4 módulos)       -> ok
python3 -W error -c "import document_tools.pdf_ops, .errors, .image_resolution"  -> ok
python3 -X dev (images_to_pdf/convert_image com falhas) -> sem ResourceWarning, sem arquivo .pdf-hub-* residual
```
**Limitações (o que NÃO foi possível executar):** `pdf_rendering.py` e tudo que importa PySide6 (incluindo `gui.py`, `test_gui.py`, o teste que falha citado em §2 do prompt — pertence à Parte 3); `pip-audit`; linter; build PyInstaller; as versões fixadas de Pillow/pypdf/reportlab. Achados de `pdf_rendering.py` estão rotulados PROVAVEL/HIPOTESE por isso.

## 3. Plano de correção ordenado
Ordenado por severidade → dependências → esforço. "Conflita": aplicar na ordem indicada porque editam o mesmo trecho.

| Ordem | ID | Sev. | Esforço | Arquivo(s) | Depende de | Resumo |
|---|---|---|---|---|---|---|
| 1 | P2-001 | ALTA | P | `pdf_ops.py` | — | Importar vários quadros só de GIF/TIFF/WEBP/PNG; nunca de JPEG/MPO |
| 2 | P2-002 | MÉDIA | P | `image_resolution.py`, `gui.py` | — | `recommend_dpi_from_images` não pode deixar escapar `DecompressionBombError`; GUI sem try/except |
| 3 | P2-003 | MÉDIA | M | `image_resolution.py` | P2-002 | Ler tamanho/EXIF sem decodificar pixels + cache por (caminho, mtime, tamanho) |
| 4 | P2-009 | MÉDIA | M | `errors.py` | — | Mapear MemoryError/ENOSPC/IsADirectory/OSError do Pillow em vez de mensagem genérica |
| 5 | P2-010 | MÉDIA | P | `errors.py` | P2-009 | Não repassar `ValueError`/`UnicodeError` vindos de bibliotecas |
| 6 | P2-011 | BAIXA | P | `errors.py` | P2-009 | `DependencyError` enganoso e ramo `PySide6.QtPdf` morto |
| 7 | P2-016 | MÉDIA | P | `pdf_ops.py` | — | `_flatten_to_rgb` cria cópias RGBA+RGB mesmo sem transparência (pico 1,6 GB p/ 100 MP) |
| 8 | P2-005 | MÉDIA | M | `pdf_ops.py` | P2-016 | Perfil ICC descartado em `images_to_pdf` (converter para sRGB) |
| 9 | P2-004 | MÉDIA | M | `pdf_ops.py` | P2-005 | Codificar páginas sem perdas quando a origem não é JPEG/WebP; manter cinza |
| 10 | P2-006 | MÉDIA | P | `pdf_ops.py` | — | `thumbnail` em modo `P`/`1` usa NEAREST |
| 11 | P2-007 | MÉDIA | M | `pdf_ops.py` | — | Normalização `I`/`F` por faixa fixa, não por min/max da imagem |
| 12 | P2-008 | MÉDIA | M | `pdf_ops.py`, `gui.py` | P2-001 | `convert_image` descarta quadros sem avisar |
| 13 | P2-013 | MÉDIA | M | `pdf_rendering.py` | — | Validar todas as páginas antes de renderizar; informar saídas parciais; progresso/cancelamento |
| 14 | P2-012 | MÉDIA | M | `gui.py` (tabelas), `pdf_ops.py`, `pdf_rendering.py` | P2-010, P2-013 | 15 mensagens estáticas sem tradução + 8 f-strings nunca traduzidas |
| 15 | P2-017 | BAIXA | P | `pdf_ops.py` | — | `PA`/`LAB` → PNG falha com `OSError` |
| 16 | P2-018 | BAIXA | P | `pdf_ops.py` | P2-010 | Validar limites WebP 16383 / JPEG 65500 px antes de salvar |
| 17 | P2-014 | BAIXA | M | `pdf_rendering.py` | P2-013 | Gravação não atômica + TOCTOU na escolha do nome |
| 18 | P2-015 | BAIXA | P | `pdf_rendering.py` | P2-013 | Fundo transparente em PNG (hipótese), `QImage` nulo, memória dobrada no JPEG |

Conflitos de trecho: **P2-016 → P2-005 → P2-004** editam `images_to_pdf.write()`/`_flatten_to_rgb` (pdf_ops.py l.221–235 e 289–321) — aplicar nessa ordem. **P2-006, P2-007, P2-017, P2-018** editam `convert_image`/`_format_image_for_output` (l.749–856) em pontos distintos; aplicar na ordem 6→7→17→18. **P2-009 → P2-010 → P2-011** reescrevem `friendly_error_message`; o protótipo completo está em `repros/proposta_p2_009_errors_patched.py` (já inclui os três).

## 4. Achados por parte

### Parte 1 — Núcleo de operações em PDF
**NÃO ANALISADA nesta execução.** (IDs `P1-001…` reservados.)

### Parte 2 — Imagens, renderização e tratamento de erros

#### [P2-001] Fotos JPEG/MPO de celular geram páginas extras no PDF
- **Severidade:** ALTA
- **Categoria:** correcao-logica
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:296-298` (função `images_to_pdf`, closure `write`)
- **Descrição:** com `all_frames=True` (padrão da função e da caixa marcada em `gui.py:2201-2202`) o código importa `n_frames` páginas de **qualquer** formato. Pillow abre JPEGs com cabeçalho MPF (fotos de iPhone/Samsung/Pixel com mapa de ganho HDR, profundidade ou miniatura) como `MPO` com `n_frames ≥ 2`; cada quadro secundário vira uma página A4 (geralmente um mapa de ganho em tons de cinza ou imagem reduzida).
- **Evidência:**
  ```python
  296    frame_count = max(1, int(getattr(opened, "n_frames", 1)))
  297    frame_indexes = range(frame_count) if all_frames else range(1)
  ```
  Execução (`repros/repro_p2_003_mpo_extra_pages.py`): `formato: MPO n_frames: 2 sufixo: .jpg` → `paginas no PDF (esperado 1): 2`; com `all_frames=False` → 1.
- **Como reproduzir:** `python repros/repro_p2_003_mpo_extra_pages.py`. Observado: 2 páginas; esperado: 1.
- **Causa raiz:** `n_frames` é tratado como "páginas do documento" para todos os formatos; só é verdade para GIF/TIFF/WEBP animado/APNG.
- **Impacto:** quem converte fotos de celular modernas em PDF recebe páginas "fantasma" sem aviso; o README (l.15) só promete múltiplas páginas para arquivos "multipágina ou animados".
- **Correção proposta:** restringir a importação multi-quadro a formatos cujo `n_frames` representa conteúdo.
  ```diff
   SUPPORTED_OUTPUT_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
   ALPHA_MODES = {"RGBA", "LA", "PA"}
  +# Formatos em que n_frames são páginas/quadros do conteúdo. JPEG/MPO fica de fora:
  +# MPO guarda miniaturas, mapas de ganho/profundidade e pares estereoscópicos.
  +MULTI_FRAME_FORMATS = {"GIF", "TIFF", "WEBP", "PNG"}
  ...
   frame_count = max(1, int(getattr(opened, "n_frames", 1)))
  -frame_indexes = range(frame_count) if all_frames else range(1)
  +import_all = all_frames and opened.format in MULTI_FRAME_FORMATS
  +frame_indexes = range(frame_count) if import_all else range(1)
  ```
  Validado em memória: MPO → 1 quadro; GIF de 2 quadros → 2.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_images_to_pdf_ignores_secondary_mpo_frames` (gera MPO com `Image.save(..., format="MPO", save_all=True, append_images=[...])`, asserta `len(PdfReader(out).pages) == 1`); manter `test_images_to_pdf_imports_all_frames_from_multipage_tiff`.
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k "mpo or multipage_tiff or first_frame"` passa; `python repros/repro_p2_003_mpo_extra_pages.py` imprime 1 página nos dois casos.
- **Risco de regressão / efeitos colaterais:** PNG animado (APNG) continua multi-página; WebP estático tem `n_frames=1`. Revalidar GIF animado e TIFF multipágina.
- **Depende de / Conflita com:** nenhum (P2-008 reutiliza `MULTI_FRAME_FORMATS`).
- **Esforço:** P

#### [P2-002] `recommend_dpi_from_images` deixa escapar `DecompressionBombError`; a GUI não trata
- **Severidade:** MÉDIA
- **Categoria:** validacao-entrada
- **Confiança:** CONFIRMADO (exceção na função) / PROVAVEL (efeito na GUI, não executada)
- **Local:** `document_tools/image_resolution.py:36-45` (`recommend_dpi_from_images`); chamadores `gui.py:2218-2224` (`_add_images`), `2226-2234`, `2236-2243`, `2245-2247`
- **Descrição:** o `except` só cobre `(OSError, ValueError, EOFError)`. `PIL.Image.DecompressionBombError` herda de `Exception`, portanto sobe até o slot da GUI, que não tem `try/except`. Uma única imagem enorme na lista impede o cálculo do DPI de todas as outras. (O Pillow também pode lançar `SyntaxError` em PNG corrompido; não reproduzi esse caso neste ambiente — as 4 corrupções testadas viraram `OSError`.)
- **Evidência:**
  ```python
  44        except (OSError, ValueError, EOFError):
  45            continue
  ```
  Saída (`repros/repro_p2_001_recommend_dpi_exceptions.py`): `bomba -> EXCECAO ESCAPOU: PIL.Image.DecompressionBombError | Image size (200000000 pixels) exceeds limit of 178956970 pixels`.
- **Como reproduzir:** `python repros/repro_p2_001_recommend_dpi_exceptions.py` (PNG 20000×10000 em modo L). Esperado: imagem ignorada; observado: exceção propagada. Em GUI: arrastar o arquivo para a aba Imagens→PDF — sem tratamento o slot lança, o rótulo de status não é atualizado e (em executável sem console) o usuário não vê nada.
- **Causa raiz:** lista de exceções incompleta; sem rede de segurança na GUI.
- **Impacto:** qualquer usuário com uma imagem acima de 2× `MAX_IMAGE_PIXELS` (≈179 MP) perde a sugestão de DPI e recebe falha silenciosa.
- **Correção proposta:** (a) em `image_resolution.py` capturar também `SyntaxError` (Pillow a usa em PNG corrompido) e `Image.DecompressionBombError`; (b) em `gui.py:2236` proteger o cálculo:
  ```diff
  -        except (OSError, ValueError, EOFError):
  +        except (OSError, ValueError, EOFError, SyntaxError, Image.DecompressionBombError):
               continue
  ```
  ```diff
   def _update_image_dpi_from_sources(self) -> None:
       sources = self._all_paths(self.image_list)
  -    recommended = recommend_dpi_from_images(sources, margin_mm=self.image_margin.value())
  +    try:
  +        recommended = recommend_dpi_from_images(sources, margin_mm=self.image_margin.value())
  +    except Exception:  # sugestão de DPI nunca deve derrubar o fluxo de adicionar imagens
  +        recommended = None
  ```
- **Testes a adicionar/alterar:** `tests/test_image_resolution.py::test_decompression_bomb_images_are_skipped` (monkeypatch `Image.MAX_IMAGE_PIXELS = 100` e imagem 50×50; asserta que a função devolve o DPI das demais, não levanta).
- **Critério de aceite:** `pytest tests/test_image_resolution.py` passa; `python repros/repro_p2_001_recommend_dpi_exceptions.py` imprime `bomba -> retornou <int>`.
- **Risco de regressão / efeitos colaterais:** nenhum para imagens válidas.
- **Depende de / Conflita com:** P2-003 edita o mesmo bloco (aplicar P2-002 antes).
- **Esforço:** P

#### [P2-003] Cálculo de DPI decodifica todos os pixels, roda na thread da GUI e é refeito para a lista inteira
- **Severidade:** MÉDIA
- **Categoria:** recursos-memoria
- **Confiança:** CONFIRMADO (custo medido) / PROVAVEL (travamento da interface, GUI não executada)
- **Local:** `document_tools/image_resolution.py:36-45`; `gui.py:2236-2243`, `2245-2247`, `2218-2224`, `2226-2234`
- **Descrição:** para obter apenas largura/altura orientadas, o código chama `ImageOps.exif_transpose(opened)`, que **copia e decodifica a imagem inteira**. `_update_image_dpi_from_sources` é chamado de forma síncrona a cada inclusão, soltura e remoção e reprocessa **todas** as imagens da lista (custo O(n²) ao montar uma lista de n imagens em lotes).
- **Evidência:** `38  oriented = ImageOps.exif_transpose(opened)`. Medido (`repros/repro_p2_011_recommend_cost_and_crc.py`): 8 JPEGs de 24 MP → **1,75 s** para `recommend_dpi_from_images`, contra **0,000 s** para apenas `Image.open().size`. (≈0,22 s por foto; 200 fotos de 24 MP ≈ 44 s de interface congelada, repetidos a cada nova inclusão.)
- **Como reproduzir:** `python repros/repro_p2_011_recommend_cost_and_crc.py`.
- **Causa raiz:** uso de `exif_transpose` só para trocar largura/altura; ausência de cache.
- **Impacto:** interface congela ao adicionar/remover muitas fotos grandes; picos de memória (cada imagem decodificada ≈ 3 bytes × pixels).
- **Correção proposta:** ler `size` e a tag EXIF 0x0112 sem decodificar, e cachear por arquivo:
  ```python
  from functools import lru_cache

  _EXIF_ORIENTATION = 0x0112
  _SWAPPED_ORIENTATIONS = {5, 6, 7, 8}

  def _oriented_size(path: Path) -> tuple[int, int]:
      with Image.open(path) as opened:
          width, height = opened.size
          try:
              orientation = opened.getexif().get(_EXIF_ORIENTATION)
          except Exception:
              orientation = None
          return (height, width) if orientation in _SWAPPED_ORIENTATIONS else (width, height)

  @lru_cache(maxsize=2048)
  def _cached_oriented_size(path: str, mtime_ns: int, file_size: int) -> tuple[int, int]:
      return _oriented_size(Path(path))
  ```
  e no laço:
  ```python
  try:
      stat = path.stat()
      width, height = _cached_oriented_size(str(path), stat.st_mtime_ns, stat.st_size)
  except (OSError, ValueError, EOFError, SyntaxError, Image.DecompressionBombError):
      continue
  ```
  Validado em memória: JPEG 1600×900 com EXIF=6 → `(900, 1600)`, igual a `exif_transpose`. Remover `opened.seek(0)` (desnecessário).
- **Testes a adicionar/alterar:** `tests/test_image_resolution.py::test_orientation_swaps_dimensions_without_decoding_pixels` (JPEG com `Image.Exif()[0x0112]=6`; mocka `ImageOps.exif_transpose` para falhar se chamado); `::test_size_cache_invalidates_when_file_changes`; comparar resultado com a implementação antiga para JPEG, PNG (chunk eXIf) e WEBP com orientação.
- **Critério de aceite:** `pytest tests/test_image_resolution.py` passa; `python repros/repro_p2_011_recommend_cost_and_crc.py` mostra `recommend_dpi` < 0,05 s para as 8 imagens.
- **Risco de regressão / efeitos colaterais:** `exif_transpose` também lê orientação de XMP em algumas versões do Pillow; validar PNG/WEBP com orientação (se divergir, usar `_oriented_size` apenas quando `getexif()` tem a tag e cair para `exif_transpose` caso contrário).
- **Depende de / Conflita com:** depende de P2-002 (mesmo bloco).
- **Esforço:** M

#### [P2-004] `images_to_pdf` recodifica toda página como JPEG q95 em RGB
- **Severidade:** MÉDIA
- **Categoria:** correcao-logica
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:302-318` (`write`), `221-235` (`_flatten_to_rgb`), `238-255` (`_resize_to_a4`)
- **Descrição:** cada página é salva com `canvas.save(page_pdf, format="PDF", resolution=dpi, quality=95)`. O plugin PDF do Pillow grava RGB como `/DCTDecode` (JPEG). Assim PNG/BMP/TIFF/GIF (originalmente sem perdas) viram JPEG com perda, e imagens em tons de cinza viram RGB (arquivo muito maior).
- **Evidência:**
  ```python
  313    canvas.save(page_pdf, format="PDF", resolution=dpi, quality=95)
  ```
  Medido (`repros/repro_p2_006_pdf_output_properties.py`): captura de tela PNG de 258 KB → PDF 356 KB `/DCTDecode /DeviceRGB`; gradiente cinza PNG de 1,6 KB → PDF de **67 KB** em `/DeviceRGB`. Alternativa sem perdas testada (ReportLab, Flate, `rl_config.useA85 = 0`): **223 KB** para a mesma captura, ou seja, **menor e sem artefatos**.
- **Como reproduzir:** `python repros/repro_p2_006_pdf_output_properties.py`. Esperado: sem perdas para origem sem perdas; observado: DCT q95 sempre.
- **Causa raiz:** uso do salvamento nativo do Pillow para PDF, que escolhe o filtro pelo modo (RGB → JPEG), e `_flatten_to_rgb` que força RGB.
- **Impacto:** perda de qualidade silenciosa (texto de capturas de tela, diagramas, documentos escaneados em PNG/TIFF ganham artefatos de bloco); PDFs de imagens cinza ficam dezenas de vezes maiores.
- **Correção proposta:** escolher a codificação pela origem: JPEG/MPO/WebP (já com perda) → manter DCT q95; demais formatos → Flate via ReportLab (já é dependência). Esboço (`from reportlab.lib.utils import ImageReader`; `from reportlab import rl_config`):
  ```python
  LOSSY_SOURCE_FORMATS = {"JPEG", "MPO", "WEBP"}

  def _save_page_pdf(page: Image.Image, target: Path, *, dpi: int, lossless: bool) -> None:
      if not lossless:
          page.save(target, format="PDF", resolution=dpi, quality=95)
          return
      rl_config.useA85 = 0                       # evita o overhead de +25% do ASCII85
      width_pt, height_pt = page.width * 72.0 / dpi, page.height * 72.0 / dpi
      pdf = canvas.Canvas(str(target), pagesize=(width_pt, height_pt), pageCompression=1)
      pdf.drawImage(ImageReader(page), 0, 0, width=width_pt, height=height_pt)
      pdf.showPage()
      pdf.save()
  ```
  No `write()`: capturar `source_format = opened.format` e chamar `_save_page_pdf(page_image, page_pdf, dpi=dpi, lossless=source_format not in LOSSY_SOURCE_FORMATS)`; **renomear a variável local `canvas`** (l.307) para `page_image` para não sombrear o módulo `reportlab.pdfgen.canvas`. Passo opcional: manter modo `L` quando a origem é `L`/`1` sem alpha (criar `Image.new("L", ...)` em `_resize_to_a4`) para obter `/DeviceGray`. Validado: página gerada abre no pypdf e passa por `PdfWriter.add_page`; mediabox `595.2 × 841.92`.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_images_to_pdf_uses_flate_for_lossless_sources` (PNG → imagem XObject com `/FlateDecode`, pixels extraídos == pixels esperados); `::test_images_to_pdf_keeps_dct_for_jpeg_sources`; `::test_images_to_pdf_gray_source_stays_gray` (se o passo opcional for feito).
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k images_to_pdf` passa; no repro, `png_captura` fica `/FlateDecode` e menor que o DCT; `jpeg_com_icc` continua `/DCTDecode`.
- **Risco de regressão / efeitos colaterais:** PNG/TIFF fotográficos grandes ficam **maiores** em Flate do que em JPEG q95 — considerar parâmetro/opção de interface ("Qualidade: sem perdas / compactar") e atualizar README pt/en/es. `rl_config` é estado global: restaurar o valor anterior após o uso. Revalidar `optimize_pdf` modo equilibrado (recomprime imagens JPEG).
- **Depende de / Conflita com:** depende de P2-005 e P2-016 (mesmo trecho; ordem 016 → 005 → 004).
- **Esforço:** M

#### [P2-005] Perfil ICC embutido é ignorado em `images_to_pdf`
- **Severidade:** MÉDIA
- **Categoria:** correcao-logica
- **Confiança:** PROVAVEL (perfil descartado confirmado; efeito visual não medido por falta de perfil de gama ampla no ambiente)
- **Local:** `document_tools/pdf_ops.py:295-309` (`write`), `221-235`
- **Descrição:** as páginas são geradas em `DeviceRGB` sem converter o conteúdo do perfil de origem (AdobeRGB, Display P3, ProPhoto) para sRGB nem embutir o perfil. Fotos de gama ampla aparecem dessaturadas/deslocadas em qualquer leitor.
- **Evidência:** `repros/repro_p2_006_pdf_output_properties.py`: `jpeg_com_icc ... cs=/DeviceRGB ... ICCBased=False`. Em contraste, `convert_image` (l.845-855) preserva o perfil quando compatível, e o README (l.34) divulga preservação de ICC — somente para a conversão de imagens.
- **Como reproduzir:** gerar JPEG Display P3 com saturação alta, converter com `images_to_pdf`, comparar visualmente com o original.
- **Causa raiz:** Pillow não embute ICC no PDF e o código não transforma as cores antes de achatar para RGB.
- **Impacto:** cores incorretas em fotos de câmeras/celulares com gama ampla (uso comum: iPhone grava Display P3).
- **Correção proposta:** converter para sRGB quando houver perfil RGB embutido (validado: perfil sRGB → imagem idêntica, perfil inválido/LAB → cai para a imagem original sem erro):
  ```python
  from io import BytesIO
  from PIL import ImageCms

  def _to_srgb(image: Image.Image, icc_profile: bytes | None) -> Image.Image:
      if not icc_profile or image.mode != "RGB":
          return image
      try:
          source = ImageCms.ImageCmsProfile(BytesIO(icc_profile))
          target = ImageCms.createProfile("sRGB")
          return ImageCms.profileToProfile(
              image, source, target,
              renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="RGB",
          ) or image
      except (ImageCms.PyCMSError, OSError, ValueError):
          return image
  ```
  No `write()`, depois de `_flatten_to_rgb(oriented)`: `icc = opened.info.get("icc_profile")`; `converted = _to_srgb(image, icc)`; se `converted is not image`, `image.close()` e `image = converted`.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_images_to_pdf_converts_embedded_profile_to_srgb` (criar perfil com `ImageCms.createProfile("sRGB")` e outro perfil sintético via `ImageCms.buildTransform`/`LAB`; verificar pixels antes/depois) e `::test_images_to_pdf_ignores_invalid_icc_profile` (bytes inválidos não impedem a geração).
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k icc` passa; imagem Display P3 de teste muda de pixel após a conversão, sRGB permanece igual.
- **Risco de regressão / efeitos colaterais:** custo extra de CPU por página; perfis CMYK/cinza não são tratados (ficam como hoje). Documentar no README.
- **Depende de / Conflita com:** depende de P2-016; conflita com P2-004 (mesmo bloco).
- **Esforço:** M

#### [P2-006] `thumbnail` em imagens paletizadas usa vizinho mais próximo
- **Severidade:** MÉDIA
- **Categoria:** correcao-logica
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:829-831` (`convert_image`)
- **Descrição:** o Pillow força `NEAREST` em `Image.resize`/`thumbnail` quando o modo é `P` ou `1`, ignorando `Resampling.LANCZOS`. Reduzir PNG/GIF paletizados (ícones, ilustrações, GIFs) com largura/altura máximas produz serrilhado forte e perda de linhas finas.
- **Evidência:**
  ```python
  829            if max_width or max_height:
  830                bounds = (max_width or image.width, max_height or image.height)
  831                image.thumbnail(bounds, Image.Resampling.LANCZOS)
  ```
  `repros/repro_p2_007_palette_resize_and_frames.py`: reduzir 4× um PNG paletizado de linhas diagonais finas → **2** cores distintas na saída; a mesma imagem em RGB → **229** cores (suavização correta).
- **Como reproduzir:** `python repros/repro_p2_007_palette_resize_and_frames.py`.
- **Causa raiz:** comportamento documentado do Pillow para modos `1`/`P`.
- **Impacto:** qualidade ruim em redimensionamentos de GIF/PNG-8; o usuário escolheu LANCZOS implicitamente.
- **Correção proposta:** converter antes de reduzir, só quando a redução realmente ocorrer (validado: 229 cores):
  ```python
  needs_resize = bool((max_width and image.width > max_width) or (max_height and image.height > max_height))
  if needs_resize and image.mode in {"P", "PA", "1"}:
      keeps_alpha = image.mode == "PA" or "transparency" in image.info
      image = image.convert("RGBA" if keeps_alpha else ("L" if image.mode == "1" else "RGB"))
  if max_width or max_height:
      image.thumbnail((max_width or image.width, max_height or image.height), Image.Resampling.LANCZOS)
  ```
  Cuidar do fechamento: `image` reatribuída precisa ser fechada no `finally` (l.865-868 já fecha `image` quando `image is not final_image`); fechar a imagem original antes de reatribuir se `image is not opened`.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_convert_image_resizes_palette_images_with_smoothing` (PNG `P` com diagonais, `max_width` metade; asserta > 2 cores).
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k convert_image` passa; repro mostra > 2 cores.
- **Risco de regressão / efeitos colaterais:** PNG de saída deixa de ser paletizado quando redimensionado (arquivo maior); revalidar `test_convert_image_supports_each_output_format`.
- **Depende de / Conflita com:** nenhum (mesma função de P2-007/017/018 em pontos distintos; ordem 006 → 007 → 017 → 018).
- **Esforço:** P

#### [P2-007] `_normalise_high_bit_depth` estica o contraste de imagens `I`/`F` e trata 12 bits como quase preto
- **Severidade:** MÉDIA
- **Categoria:** correcao-logica
- **Confiança:** CONFIRMADO (comportamento) / PROVAVEL (qual é o comportamento desejado — decisão de produto)
- **Local:** `document_tools/pdf_ops.py:198-218`
- **Descrição:** para os modos `I` e `F` o código normaliza por `min/max` **da própria imagem**, mas o comentário da linha 211-212 diz que "preserva valores 0..255 comuns". Na prática uma imagem `I` com tons 50..200 sai com 0..255; duas páginas com o mesmo valor de entrada recebem tons diferentes. Para `I;16` o divisor fixo `/257` assume 16 bits completos: dados de 12 bits (0..4095, comuns em TIFF científicos/médicos) saem com máximo 15.
- **Evidência:**
  ```python
  211            # Normalize by this image's dynamic range. This preserves ordinary
  212            # 0..255 values in Pillow's "I" mode instead of crushing them to black.
  213            scale = 255.0 / float(high - low)
  214            return image.point(lambda value: (value - low) * scale).convert("L")
  ```
  `repros/repro_p2_005_tone_normalisation.py`: `I 50,200 -> [0, 255]`; `I;16 0,4095 -> [0, 15]`; `I 100,120 -> [0,255]` e `I 100,250 -> [0,255]` (pixel 100 vira 0 nas duas, mas 120 e 250 viram 255).
- **Como reproduzir:** `python repros/repro_p2_005_tone_normalisation.py`.
- **Causa raiz:** normalização dependente do conteúdo; escala fixa para `I;16`.
- **Impacto:** tons alterados silenciosamente e inconsistentes entre páginas/arquivos (TIFF 32-bit, 16-bit com faixa reduzida). PNG/TIFF 16-bit de faixa cheia continuam corretos (testes existentes).
- **Correção proposta:** usar faixas "nominais" (8, 16 bits ou 0..1) e só normalizar por conteúdo quando a faixa é desconhecida. Ramo `I`/`F` (testado em memória: `I 50,200→[50,200]`, `I 100,250→[100,250]`, `I 0,65535→[0,255]`, `F 0,1→[0,255]`, constante → cinza médio):
  ```python
  if image.mode in {"I", "F"}:
      low, high = (float(value) for value in image.getextrema())
      if not (math.isfinite(low) and math.isfinite(high)):
          return Image.new("L", image.size, 0)
      if image.mode == "F" and 0.0 <= low and high <= 1.0:
          floor, ceiling = 0.0, 1.0
      elif 0 <= low and high <= 255:
          floor, ceiling = 0.0, 255.0
      elif 0 <= low and high <= 65535:
          floor, ceiling = 0.0, 65535.0
      else:
          floor, ceiling = low, high            # faixa desconhecida: normaliza pelo conteúdo
      if ceiling == floor:
          return Image.new("L", image.size, 0)
      scale = 255.0 / (ceiling - floor)
      return image.point(lambda value: (value - floor) * scale).convert("L")
  ```
  Decisão de produto para `I;16` de 12 bits: manter `/257` (documentando no README) **ou** inferir a escala (`high <= 4095` → dividir por 4095/255). Recomendado: manter `/257` e acrescentar nota na documentação, pois a inferência escurece/clareia imagens legitimamente escuras.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_normalise_keeps_8_bit_values_in_i_mode`, `::test_normalise_is_independent_between_images`, `::test_normalise_float_unit_range`; manter `test_images_to_pdf_preserves_tones_from_16_bit_grayscale_png` e `test_convert_image_preserves_tones_from_16_bit_grayscale_png`.
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k "normalise or 16_bit"` passa; `python repros/repro_p2_005_tone_normalisation.py` (ou `repros/proposta_p2_007_normalise_check.py`) mostra `[50, 200]`.
- **Risco de regressão / efeitos colaterais:** imagens `I` de faixa 0..65535 continuam mapeadas para 0..255; imagens `I` com faixa estreita (ex.: 1000..1100) deixam de ser esticadas — dentro da faixa 0..65535 ficam escuras (escolha deliberada). Revalidar os dois testes 16-bit.
- **Depende de / Conflita com:** nenhum.
- **Esforço:** M

#### [P2-008] `convert_image` descarta quadros de GIF/TIFF/WEBP animados sem avisar
- **Severidade:** MÉDIA
- **Categoria:** integridade-de-dados
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:819-831` (`convert_image`); resumo em `gui.py:4753-4760`
- **Descrição:** a conversão grava somente o quadro 0. GIF animado, TIFF multipágina e WebP animado viram imagem de um quadro e a mensagem de sucesso diz "N imagem(ns) convertida(s)" sem qualquer aviso. (Os originais não são alterados — a perda é do resultado esperado pelo usuário.)
- **Evidência:** `repros/repro_p2_007_palette_resize_and_frames.py`: `anim.gif: 3 quadros na origem -> saida PNG com n_frames=1 (sem aviso ao usuario)`; idem `multi.tif`.
- **Como reproduzir:** `python repros/repro_p2_007_palette_resize_and_frames.py`.
- **Causa raiz:** `convert_image` foi desenhada para imagem única e não informa nem trata multi-quadro.
- **Impacto:** TIFF multipágina (digitalizações) convertido em lote para JPEG/PNG perde páginas sem o usuário perceber.
- **Correção proposta:** manter o comportamento (primeiro quadro) mas **avisar**: criar `image_frame_count(path) -> int` em `pdf_ops.py` (usando `MULTI_FRAME_FORMATS` de P2-001; `1` para os demais) e, em `_convert_images` (`gui.py` ≈ l.4728-4760), acrescentar ao resumo: "{n} arquivo(s) tinham vários quadros; somente o primeiro foi convertido." (nova string em PT + EN/ES). Opcional: para saída TIFF/WEBP usar `save_all=True` com `append_images`.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_image_frame_count_reports_gif_tiff_and_ignores_mpo`; teste de GUI correspondente em `tests/test_gui.py` (Parte 5).
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k frame_count` passa; GUI exibe aviso para um GIF de 3 quadros.
- **Risco de regressão / efeitos colaterais:** nenhuma alteração no arquivo gerado; apenas texto novo (traduzir).
- **Depende de / Conflita com:** depende de P2-001; coordenar com P2-012 (novas traduções) e com a Parte 5 (GUI da aba Converter).
- **Esforço:** M

#### [P2-009] `errors.py` oculta causas acionáveis atrás de "detalhes internos ocultados"
- **Severidade:** MÉDIA
- **Categoria:** ui-ux
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/errors.py:5-31` (`friendly_error_message`)
- **Descrição:** a classificação usa `error.__class__.__module__`. O Pillow lança `OSError` (módulo `builtins`) para imagem truncada, falha de escrita e limites de encoder, então cai no fim da função. O mesmo acontece com `MemoryError`, `OSError(ENOSPC)` e `IsADirectoryError`. Além disso `FileNotFoundError` troca qualquer texto (que já dizia *qual* arquivo faltou) por mensagem genérica.
- **Evidência:** `repros/repro_p2_002_errors_mapping.py`:
  ```
  PNG truncado   -> 'Não foi possível concluir a operação. Os detalhes internos foram ocultados.'
  MemoryError    -> (mesma mensagem)
  OSError ENOSPC -> (mesma mensagem)
  IsADirectoryError -> (mesma mensagem)
  ```
  (a exceção real do PNG truncado é `builtins.OSError: image file is truncated`; JPEG com 70000 px: `OSError: broken data stream when writing image file`, via `repros/repro_p2_009_encoder_limits.py`).
- **Como reproduzir:** `python repros/repro_p2_002_errors_mapping.py`.
- **Causa raiz:** decisão pelo módulo da *classe* da exceção, não pela origem do `raise`; ausência de tratamento de `errno`/`MemoryError`.
- **Impacto:** usuário com disco cheio, pouca memória ou imagem truncada recebe uma mensagem sem ação possível.
- **Correção proposta:** protótipo completo e testado em `repros/proposta_p2_009_errors_patched.py` (substituir o corpo de `errors.py`). Pontos centrais: helper `_origin_root(error)` que percorre `__traceback__` até o último frame Python e devolve o pacote raiz (`PIL`, `pypdf`, …); mensagens novas para `MemoryError`, `errno.ENOSPC`, `IsADirectoryError/NotADirectoryError`; qualquer exceção originada em `PIL` → mensagem de imagem. Saídas verificadas: PNG truncado → "A imagem não pôde ser processada…"; MemoryError → "Memória insuficiente…"; ENOSPC → "Não há espaço livre…".
  Para `FileNotFoundError`: manter o texto genérico (o teste existente exige não vazar caminho) **mas** acrescentar o `name` do arquivo quando a exceção for criada com `filename` ou usar `Path(error.filename).name`.
- **Testes a adicionar/alterar:** `tests/test_errors.py::test_truncated_image_message`, `::test_memory_error_message`, `::test_disk_full_message` (`OSError(errno.ENOSPC, "x")`), `::test_is_a_directory_message`; manter os 3 testes atuais.
- **Critério de aceite:** `pytest tests/test_errors.py` passa; `PDFHUB_REPO=. python repros/repro_p2_002_errors_mapping.py` não mostra "detalhes internos ocultados" nas 4 linhas acima.
- **Risco de regressão / efeitos colaterais:** `__traceback__` só existe depois do `raise` — em testes, exceções criadas sem `raise` têm origem vazia (o protótipo trata como app). Revalidar `batch_processing.py` (usa `friendly_error_message` em l.346) e mensagens do histórico de relatórios.
- **Depende de / Conflita com:** nenhum; P2-010 e P2-011 editam a mesma função (aplicar 009 → 010 → 011 juntos, protótipo já os contém).
- **Esforço:** M

#### [P2-010] `errors.py` repassa `ValueError`/`UnicodeError` de bibliotecas, contrariando a própria garantia
- **Severidade:** MÉDIA
- **Categoria:** seguranca
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/errors.py:25-28` (docstring em l.6, ramo `ValueError` em l.27-28)
- **Descrição:** a docstring afirma "sem expor detalhes arbitrários de bibliotecas", mas **qualquer** `ValueError` é devolvido com `str(error)`. Isso inclui texto em inglês do Pillow (limite do WebP), `UnicodeEncodeError` (subclasse de `ValueError`; ocorre, por exemplo, com texto fora do Latin-1 em fonte Helvetica ou nomes de arquivo inválidos) e mensagens de `int()`.
- **Evidência:** `repros/repro_p2_002_errors_mapping.py`:
  ```
  UnicodeEncodeError (ReportLab) -> "'latin-1' codec can't encode character '—' in position 0: ordinal not in range(256)"
  ValueError arbitrario          -> "invalid literal for int() with base 10: 'x'"
  ```
  E `repros/repro_p2_009_encoder_limits.py`: WebP > 16383 px → usuário vê `encoding error 5: Image size exceeds WebP limit of 16383 pixels` (inglês, não traduzível).
- **Como reproduzir:** os dois scripts acima.
- **Causa raiz:** ramo `isinstance(error, ValueError)` é amplo demais porque o app usa `ValueError` como canal de mensagens amigáveis.
- **Impacto:** texto técnico e em inglês na interface PT/ES; vazamento de detalhes de implementação.
- **Correção proposta:** (a) caminho mínimo (incluído no protótipo): tratar `UnicodeError` com mensagem própria e só repassar `ValueError` cuja **origem** não é `PIL/pypdf/reportlab/PySide6/cryptography` (função `_origin_root` de P2-009); (b) caminho estrutural (recomendado a médio prazo): criar `class UserMessageError(ValueError)` em `errors.py`, trocar `raise ValueError(` por `raise UserMessageError(` nos módulos próprios e repassar **somente** essa classe — fazer em PR separado (toca todas as partes).
- **Testes a adicionar/alterar:** `tests/test_errors.py::test_unicode_errors_are_not_echoed`, `::test_library_value_errors_are_not_echoed` (levantar `ValueError` dentro de função que simula frame de `PIL` — ou usar o erro real do WebP), `::test_app_value_errors_are_still_shown`.
- **Critério de aceite:** `pytest tests/test_errors.py` passa; no repro, "UnicodeEncodeError" mostra a mensagem amigável.
- **Risco de regressão / efeitos colaterais:** mensagens de validação de `pdf_ops.py` (`ValueError` próprios) devem continuar visíveis — coberto pelo teste `::test_app_value_errors_are_still_shown`.
- **Depende de / Conflita com:** depende de P2-009 (helper).
- **Esforço:** P

#### [P2-011] `DependencyError` do pypdf é descrito como "PDF danificado"; ramo `PySide6.QtPdf` é código morto
- **Severidade:** BAIXA
- **Categoria:** ui-ux
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/errors.py:19-24`
- **Descrição:** `pypdf.errors.DependencyError` ("cryptography>=… is required for AES") cai no ramo `module_name.startswith("pypdf")` e informa PDF danificado; a causa real é instalação/build sem `cryptography` (risco no executável PyInstaller). O ramo `PySide6.QtPdf` (l.23-24) nunca é atingido porque `QtPdf` não define exceções próprias (`pdf_rendering.py` levanta `ValueError`/`OSError`).
- **Evidência:** `pypdf DependencyError -> 'O PDF contém uma estrutura não suportada ou está danificado…'` (`repros/repro_p2_002_errors_mapping.py`).
- **Como reproduzir:** mesmo script.
- **Causa raiz:** classificação só por prefixo de módulo.
- **Impacto:** build quebrado parece "PDF do usuário corrompido"; diagnóstico difícil.
- **Correção proposta:** já no protótipo (`error_type == "DependencyError"` → "Falta um componente de criptografia nesta instalação. Reinstale o aplicativo."); remover o ramo `QtPdf`. Recomendar à Parte 3 que `main.py --selftest` execute uma abertura de PDF AES-256.
- **Testes a adicionar/alterar:** `tests/test_errors.py::test_dependency_error_points_to_installation`.
- **Critério de aceite:** `pytest tests/test_errors.py` passa.
- **Risco de regressão / efeitos colaterais:** nenhum.
- **Depende de / Conflita com:** depende de P2-009 (mesma função).
- **Esforço:** P

#### [P2-012] Mensagens de erro da Parte 2 sem tradução EN/ES
- **Severidade:** MÉDIA
- **Categoria:** i18n
- **Confiança:** CONFIRMADO (análise estática por AST)
- **Local:** `pdf_ops.py:100, 248, 269, 273, 278, 280, 282, 800, 802, 804, 806, 808, 859`; `image_resolution.py:29`; `pdf_rendering.py:34` (estáticas) e `pdf_ops.py:285, 287, 787, 796, 798`; `pdf_rendering.py:74, 84, 103` (f-strings)
- **Descrição:** `OperationWorker` emite o texto do erro e `_operation_failed` o passa por `self._t(...)`, que só traduz **correspondência exata** com `TRANSLATIONS`. Das mensagens estáticas levantadas nos trechos da Parte 2, **15** não existem nas tabelas `en`/`es`; as **8** montadas com f-string (nomes de arquivo, formatos, número da página) nunca casam. Em EN/ES a janela de erro aparece em português. Ressalva: mensagens levantadas como `FileNotFoundError` (ex.: "A pasta de destino não existe.", "Escolha um arquivo PDF existente.") são trocadas por `errors.py` por um texto genérico já traduzido, então só as levantadas como `ValueError` chegam em português ao usuário; ainda assim todas devem ter tradução porque a API é usada diretamente (lote, perfis). Além disso `gui.py:1991` faz `self._t(f"…: {message}")`, f-string avaliada **antes** de traduzir (ver T-001).
- **Evidência:** `python repros/repro_p2_012_i18n_coverage.py` lista cada linha. Exemplos faltantes: "A pasta de destino não existe.", "O arquivo de saída não pode substituir uma imagem de origem.", "A qualidade precisa ficar entre 1 e 100.", "A largura máxima precisa ser maior que zero.".
- **Como reproduzir:** o script (não requer Qt).
- **Causa raiz:** tradução por texto exato sem chaves/placeholder para mensagens dinâmicas.
- **Impacto:** UI parcialmente em português para usuários EN/ES.
- **Correção proposta:** (1) adicionar as 15 chaves estáticas às tabelas (sugestão EN/ES: "The destination folder does not exist." / "La carpeta de destino no existe."; "The output file cannot replace a source image." / "El archivo de salida no puede reemplazar una imagen de origen."; "Quality must be between 1 and 100." / "La calidad debe estar entre 1 y 100."; "Maximum width must be greater than zero." / "El ancho máximo debe ser mayor que cero."; "Maximum height must be greater than zero." / "El alto máximo debe ser mayor que cero."; "Margins leave no room on the page." / "Los márgenes no dejan espacio suficiente en la página."; "Add at least one image." / "Agregue al menos una imagen."; demais análogas); (2) para as dinâmicas, levantar a mensagem a partir de **template** traduzível: `raise ValueError(MSG_PAGE_RENDER.format(page=n))` com `MSG_PAGE_RENDER = "Não foi possível renderizar a página {page}."` e na GUI traduzir o template antes de formatar (ex.: exceção `UserMessageError(template, **fields)` — ver P2-010 b).
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_part2_error_messages_have_translations` (coletar literais por AST como no repro e exigir presença em `TRANSLATIONS["en"]` e `["es"]`).
- **Critério de aceite:** `python repros/repro_p2_012_i18n_coverage.py` imprime lista vazia para "ESTATICAS SEM TRADUCAO".
- **Risco de regressão / efeitos colaterais:** nenhum funcional; mensagens existentes mantêm o texto em PT.
- **Depende de / Conflita com:** depende de P2-010 e P2-013 (novos textos); coordenar com Parte 3 (`_t`).
- **Esforço:** M

#### [P2-013] PDF→imagens: pixels validados página a página, saídas parciais sem aviso, sem progresso/cancelamento
- **Severidade:** MÉDIA
- **Categoria:** integridade-de-dados
- **Confiança:** PROVAVEL (leitura de código; `pdf_rendering.py` não executado — PySide6 ausente)
- **Local:** `document_tools/pdf_rendering.py:69-104, 106-109` (`export_pdf_pages_to_images`)
- **Descrição:** o limite `MAX_RENDER_PIXELS` é verificado **dentro** do laço, página por página. Num PDF em que a página 5 é grande demais, as páginas 1-4 já foram gravadas quando o `ValueError` sobe; o usuário só vê "A página ultrapassa o limite seguro…" e não sabe que há 4 arquivos novos na pasta. O comentário de l.107-108 admite manter as saídas, mas nada informa. A função não aceita callback de progresso nem sinal de cancelamento, e roda no `OperationWorker` sem interrupção (um PDF de 500 páginas a 600 DPI não pode ser cancelado).
- **Evidência:**
  ```python
  77             if pixel_width * pixel_height > MAX_RENDER_PIXELS:
  78                 raise ValueError(
  ...
  106    except Exception:
  107        # Keep successful earlier outputs; report the error without silently deleting
  109        raise
  ```
- **Como reproduzir:** PDF de 5 páginas, páginas 1-4 A4 e a 5ª 5000×5000 pt; exportar a 150 DPI → 4 PNG criados e erro. (Não executado.)
- **Causa raiz:** validação tardia; API sem progresso/cancelamento.
- **Impacto:** resultado parcial inesperado; operações longas impossíveis de interromper.
- **Correção proposta:** (a) pré-validar tamanhos de **todas** as páginas selecionadas antes de renderizar a primeira (laço só com `pagePointSize`); (b) incluir a contagem de arquivos já criados na mensagem de falha (`raise ValueError(f"{base} {len(created)} arquivo(s) já foram gravados.")` via template traduzível) **ou** remover os criados quando o usuário não pediu retomada; (c) adicionar parâmetros opcionais `progress: Callable[[int, int], None] | None = None` e `should_cancel: Callable[[], bool] | None = None`, verificados a cada página (levantar `InterruptedError` e fazer `OperationWorker` tratá-lo — coordenar com Parte 3/5).
- **Testes a adicionar/alterar:** `tests/test_pdf_rendering.py::test_oversized_page_in_the_middle_creates_no_files` (PDF com 3 páginas, a última 60000×60000 pt; asserta pasta vazia e `ValueError`); `::test_progress_and_cancel_callbacks`.
- **Critério de aceite:** `QT_QPA_PLATFORM=offscreen pytest tests/test_pdf_rendering.py` passa (em ambiente com PySide6).
- **Risco de regressão / efeitos colaterais:** a pré-validação lê tamanhos de todas as páginas selecionadas (barato). Cancelamento exige integração com o worker (Parte 3).
- **Depende de / Conflita com:** nenhum; P2-014 e P2-015 editam o mesmo laço (aplicar depois).
- **Esforço:** M

#### [P2-014] PDF→imagens: gravação não atômica e escolha de nome sujeita a corrida
- **Severidade:** BAIXA
- **Categoria:** integridade-de-dados
- **Confiança:** PROVAVEL
- **Local:** `document_tools/pdf_rendering.py:86-104`
- **Descrição:** o nome livre é escolhido com `while destination.exists()` e só depois `image.save(...)` grava direto no destino. Um arquivo criado entre as duas operações (outro processo, sincronizador de nuvem, duas execuções) é **sobrescrito**; uma falha no meio (disco cheio) deixa arquivo parcial que não entra em `created` e não é removido. O README (l.23) promete "nomes que evitam sobrescrever arquivos existentes".
- **Evidência:** l.89-91 (`exists` em laço) e l.102 (`image.save(str(destination), …)`).
- **Como reproduzir:** hipotético (corrida); para o arquivo parcial, simular `QImage.save` com `monkeypatch` retornando `False` e confirmar que o arquivo vazio pode permanecer. (Não executado.)
- **Causa raiz:** verificação e gravação não atômicas; sem arquivo temporário.
- **Impacto:** baixo (janela pequena), mas contradiz a garantia documentada.
- **Correção proposta:** gravar em temporário na mesma pasta e publicar sem sobrescrever:
  ```python
  descriptor, temporary_name = tempfile.mkstemp(prefix=".pdf-hub-", suffix=suffix, dir=str(output))
  os.close(descriptor)
  temporary = Path(temporary_name)
  try:
      if not image.save(str(temporary), encoder, quality_value):
          raise OSError(...)
      number = 1
      while True:
          destination = output / (f"{base_name}{suffix}" if number == 1 else f"{base_name}-{number}{suffix}")
          try:
              os.link(temporary, destination)      # falha com FileExistsError se já existir
              break
          except FileExistsError:
              number += 1
  finally:
      temporary.unlink(missing_ok=True)
  ```
  (usar o mesmo fallback `O_EXCL` de `_atomic_pdf_save` quando `os.link` não for suportado; aplicar `os.chmod(…, file_mode)` se a função receber o modo — hoje ela não recebe, ver §8).
- **Testes a adicionar/alterar:** `tests/test_pdf_rendering.py::test_failed_save_leaves_no_partial_file`, `::test_existing_file_is_never_overwritten`.
- **Critério de aceite:** testes passam em ambiente com PySide6.
- **Risco de regressão / efeitos colaterais:** arquivos de saída passam a ser criados com permissão 0600 pelo `mkstemp` (hoje herdam `umask`); decidir e documentar.
- **Depende de / Conflita com:** depende de P2-013 (mesmo laço).
- **Esforço:** M

#### [P2-015] PDF→imagens: PNG possivelmente com fundo transparente, `QImage` nulo não verificado, memória dobrada no JPEG
- **Severidade:** BAIXA
- **Categoria:** recursos-memoria
- **Confiança:** HIPOTESE
- **Local:** `document_tools/pdf_rendering.py:82-103`
- **Descrição:** (1) só o caminho JPEG compõe sobre branco (l.94-101); se `QPdfDocument.render` devolver ARGB transparente para páginas sem fundo pintado, os PNG saem com fundo transparente — **verificar na versão fixada (PySide6 6.12)**. (2) O `QImage` criado para JPEG (l.97) não verifica `isNull()`; em falta de memória `fill`/`QPainter` operam sobre imagem nula e o erro vira "Não foi possível salvar a imagem…" (l.103), enganoso. (3) No limite (40 MP) `rendered` (160 MB) e a cópia RGB32 (160 MB) coexistem.
- **Evidência:** código citado; nenhuma execução (PySide6 ausente).
- **Como reproduzir:** exportar um PDF de fundo branco "não pintado" como PNG e abrir em visualizador com fundo xadrez; para (2) simular `QImage` nulo.
- **Causa raiz:** tratamento assimétrico dos formatos; sem checagem de alocação.
- **Impacto:** PNG com transparência inesperada; mensagem de erro imprecisa; pico de memória.
- **Correção proposta:** compor sobre branco sempre que `rendered.hasAlphaChannel()` (PNG e JPEG), checar `image.isNull()` (levantar `MemoryError` → mapeado por P2-009) e liberar `rendered` (`rendered = QImage()`) antes de `save`.
- **Testes a adicionar/alterar:** `tests/test_pdf_rendering.py::test_png_export_has_opaque_white_background` (ler pixel de canto: `QImage(path).pixelColor(0,0).alpha() == 255`).
- **Critério de aceite:** teste passa com PySide6 6.12.0; se o alfa já é 255 na versão fixada, registrar o achado como falso positivo e manter só o item (2).
- **Risco de regressão / efeitos colaterais:** nenhum esperado.
- **Depende de / Conflita com:** depende de P2-013.
- **Esforço:** P

#### [P2-016] `_flatten_to_rgb` copia a imagem duas vezes mesmo sem transparência (pico de 1,6 GB para 100 MP)
- **Severidade:** MÉDIA
- **Categoria:** recursos-memoria
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:221-235` (`_flatten_to_rgb`), usado em l.302 e l.759
- **Descrição:** toda imagem — inclusive RGB opaca — é convertida para RGBA (4 B/px) e depois colada em um novo RGB (3 B/px), somando-se à original e ao canvas A4. Entre 89,5 MP e 179 MP o Pillow apenas **avisa** (`DecompressionBombWarning`) e o processamento prossegue, consumindo muita memória; nenhum aviso chega ao usuário.
- **Evidência:**
  ```python
  224    rgba = normalized.convert("RGBA")
  225    flattened = Image.new("RGB", rgba.size, "white")
  227    flattened.paste(rgba, (0, 0), rgba.getchannel("A"))
  ```
  `repros/repro_p2_008_bomb_warning_memory.py` (PNG RGB 10000×10000 = 100 MP, 316 KB em disco): `images_to_pdf ok em 2.1s; avisos: ['DecompressionBombWarning']`; pico RSS **1662 MB** (422 MB antes).
- **Como reproduzir:** `python repros/repro_p2_008_bomb_warning_memory.py`.
- **Causa raiz:** caminho único para todas as imagens; sem atalho para imagens opacas.
- **Impacto:** em máquinas com 4–8 GB, imagens grandes (mapas, digitalizações) causam swap ou `MemoryError` (que hoje vira "detalhes ocultados", ver P2-009).
- **Correção proposta:** atalho para imagens sem alfa/transparência:
  ```python
  def _flatten_to_rgb(image: Image.Image) -> Image.Image:
      normalized = _normalise_high_bit_depth(image)
      try:
          has_alpha = normalized.mode in ALPHA_MODES or "transparency" in normalized.info
          if not has_alpha:
              return normalized.convert("RGB")     # já cria uma cópia independente
          rgba = normalized.convert("RGBA")
          ...                                      # corpo atual para o caso com transparência
      finally:
          if normalized is not image:
              normalized.close()
  ```
  Para o aviso de bomba: decidir política explícita — recomendado converter o aviso em erro amigável acima de um limite configurável (`MAX_SAFE_PIXELS`, ex.: 150 MP) ou, no mínimo, registrar no texto de sucesso. Não alterar `Image.MAX_IMAGE_PIXELS` global.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_flatten_opaque_rgb_does_not_create_rgba_copy` (patch `Image.Image.convert` e contar chamadas com `"RGBA"`), `::test_flatten_still_composites_transparency_over_white` (manter `test_images_to_pdf_flattens_transparency_over_white`).
- **Critério de aceite:** `pytest tests/test_pdf_ops.py -k flatten` passa; `repro_p2_008` mostra pico RSS inferior (esperado ≈ −35 %).
- **Risco de regressão / efeitos colaterais:** `convert("RGB")` de CMYK/LAB/P sem transparência — cobrir na matriz de `repro_p2_004`. Modo `P` com `transparency` continua pelo caminho com alfa.
- **Depende de / Conflita com:** nenhum; P2-005 e P2-004 editam o trecho seguinte (aplicar antes).
- **Esforço:** P

#### [P2-017] `PA` e `LAB` não são normalizados para PNG e falham com `OSError`
- **Severidade:** BAIXA
- **Categoria:** correcao-logica
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:766-769` (`_format_image_for_output`)
- **Descrição:** o ramo PNG só converte `CMYK`; modos `PA` e `LAB` seguem para `image.copy()` e o `save` falha. (`PA` está em `ALPHA_MODES`, então o código "sabe" que existe, mas não o trata para PNG.)
- **Evidência:** `repros/repro_p2_004_mode_matrix.py`: `[PA] … PNG:FALHA(OSError: cannot write mode PA as PNG)` e `[LAB] … PNG:FALHA(OSError: cannot write mode LAB as PNG)`; o usuário vê "detalhes internos ocultados".
- **Como reproduzir:** `python repros/repro_p2_004_mode_matrix.py`. (A linha `[YCbCr]` do script é artefato do arquivo de teste — descartar; ver §7.)
- **Causa raiz:** lista de modos aceitos para PNG incompleta.
- **Impacto:** raro (TIFF LAB, PNG paletizado com alfa de Pillow).
- **Correção proposta:**
  ```python
  PNG_NATIVE_MODES = {"1", "L", "LA", "P", "RGB", "RGBA", "I;16", "I"}   # I/I;16 já passam por _normalise
  ...
  if image_format == "PNG" and image.mode not in PNG_NATIVE_MODES:
      return image.convert("RGBA" if image.mode in ALPHA_MODES else "RGB")
  ```
  (manter o tratamento atual de CMYK/WEBP).
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_convert_image_handles_pa_and_lab_modes_to_png` (parametrizado).
- **Critério de aceite:** `python repros/repro_p2_004_mode_matrix.py` não mostra FALHA em `PA`/`LAB`; `pytest -k convert_image` passa.
- **Risco de regressão / efeitos colaterais:** nenhum para modos já suportados.
- **Depende de / Conflita com:** nenhum.
- **Esforço:** P

#### [P2-018] Limites dimensionais dos encoders (WebP 16383 px, JPEG 65500 px) não são validados
- **Severidade:** BAIXA
- **Categoria:** validacao-entrada
- **Confiança:** CONFIRMADO
- **Local:** `document_tools/pdf_ops.py:833-856` (`convert_image`)
- **Descrição:** imagens acima dos limites do encoder falham dentro do `save`. WebP: `ValueError` com texto técnico em inglês repassado ao usuário; JPEG: `OSError: broken data stream…` → "detalhes ocultados". Ambas ocorrem depois de decodificar a imagem inteira.
- **Evidência:** `repros/repro_p2_009_encoder_limits.py`: WebP 17000×20 → `encoding error 5: Image size exceeds WebP limit of 16383 pixels`; JPEG 70000×10 → `Maximum supported image dimension is 65500 pixels` + `OSError`.
- **Como reproduzir:** `python repros/repro_p2_009_encoder_limits.py`.
- **Causa raiz:** ausência de pré-validação.
- **Impacto:** erro tardio e pouco claro para panoramas/escaneamentos longos.
- **Correção proposta:** depois de `_format_image_for_output` (l.833) e antes de `save`:
  ```python
  encoder_limit = {"WEBP": 16383, "JPEG": 65500}.get(image_format)
  if encoder_limit and max(final_image.size) > encoder_limit:
      raise ValueError(
          f"O formato {image_format} aceita no máximo {encoder_limit} px por lado. "
          "Reduza a largura/altura máxima ou escolha PNG ou TIFF."
      )
  ```
  (mensagem com template traduzível, ver P2-012).
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_convert_image_rejects_dimensions_beyond_encoder_limits` (parametrizado WEBP/JPEG; imagem 1 px de altura).
- **Critério de aceite:** `python repros/repro_p2_009_encoder_limits.py` mostra a mensagem amigável nos dois casos; teste passa.
- **Risco de regressão / efeitos colaterais:** nenhum.
- **Depende de / Conflita com:** depende de P2-010 (para que a mensagem própria seja exibida e a de biblioteca não).
- **Esforço:** P

### Parte 3 — Casca da aplicação, build/CI e distribuição
**NÃO ANALISADA nesta execução.** (IDs `P3-001…` reservados.)

### Parte 4 — Abas de operação individual (GUI)
**NÃO ANALISADA nesta execução.** (IDs `P4-001…` reservados.)

### Parte 5 — Lote, perfis, histórico, PDF→imagens e Converter imagens
**NÃO ANALISADA nesta execução.** (IDs `P5-001…` reservados.) Observação: a lógica de nomes de saída da aba Converter imagens (`gui.py:4728-4737`) foi lida só para checar o contrato com `convert_image`; ver §7.

## 5. Achados transversais (T-001…)
Observados enquanto lia os pontos de contato com a Parte 2; **não verificados por execução** e pertencentes a outras partes — repassar à análise dessas partes.

#### [T-001] `_operation_failed` monta f-string antes de traduzir
- **Severidade:** BAIXA · **Categoria:** i18n · **Confiança:** PROVAVEL · **Local:** `gui.py:1991` (Parte 3)
- **Descrição/Evidência:** `self.status_label.setText(self._t(f"Não foi possível concluir a operação: {message}"))` — a f-string é avaliada antes de `_t`; a tabela nunca casa, então o rótulo de status fica em português em EN/ES. **Correção:** `self._t("Não foi possível concluir a operação: {message}").format(message=self._t(message))` e adicionar a chave às tabelas. **Teste:** `test_gui.py::test_operation_failed_status_is_translated`. **Critério de aceite:** com `_language="en"` o status não contém "Não foi possível". **Depende de:** P2-012.

#### [T-002] `OperationWorker` não oferece cancelamento
- **Severidade:** MÉDIA · **Categoria:** concorrencia · **Confiança:** HIPOTESE · **Local:** `gui.py:1344-1358` (Parte 3)
- **Descrição:** `export_pdf_pages_to_images` e `_convert_images` rodam sem forma de interromper (ver P2-013); fechar a janela durante uma exportação longa depende de `closeEvent`/`wait()` (a verificar na Parte 3). **Ação:** Parte 3 deve definir um mecanismo único (`requestInterruption()` + callback `should_cancel`) usado por P2-013.

#### [T-003] `--selftest` deve cobrir QtPdf e criptografia AES
- **Severidade:** BAIXA · **Categoria:** build-ci · **Confiança:** HIPOTESE · **Local:** `main.py` (Parte 3)
- **Descrição:** com P2-011, uma build sem `cryptography` passará a mostrar mensagem própria; o selftest do executável deveria abrir um PDF AES-256 e renderizar uma página via `QPdfDocument`. Verificar na Parte 3.

## 6. Cobertura de testes ausente
Cenários da Parte 2 sem teste hoje (nomes sugeridos):
- `test_pdf_ops.py::test_images_to_pdf_ignores_secondary_mpo_frames` (P2-001)
- `test_image_resolution.py::test_decompression_bomb_images_are_skipped` (P2-002)
- `test_image_resolution.py::test_orientation_swaps_dimensions_without_decoding_pixels` e `::test_size_cache_invalidates_when_file_changes` (P2-003)
- `test_image_resolution.py::test_exif_orientation_changes_recommended_dpi` (hoje não há teste de orientação EXIF em `recommend_dpi_from_images`)
- `test_pdf_ops.py::test_images_to_pdf_uses_flate_for_lossless_sources` / `::test_images_to_pdf_keeps_dct_for_jpeg_sources` (P2-004)
- `test_pdf_ops.py::test_images_to_pdf_converts_embedded_profile_to_srgb` (P2-005)
- `test_pdf_ops.py::test_convert_image_resizes_palette_images_with_smoothing` (P2-006)
- `test_pdf_ops.py::test_normalise_keeps_8_bit_values_in_i_mode`, `::test_normalise_is_independent_between_images` (P2-007)
- `test_pdf_ops.py::test_image_frame_count_*` e `::test_convert_image_uses_first_frame_of_animated_gif` (P2-008)
- `test_errors.py::test_truncated_image_message`, `::test_memory_error_message`, `::test_disk_full_message`, `::test_unicode_errors_are_not_echoed`, `::test_dependency_error_points_to_installation` (P2-009/010/011)
- `test_gui.py::test_part2_error_messages_have_translations` (P2-012)
- `test_pdf_rendering.py`: apenas 2 testes (arquivo inválido e página gigante). Faltam: PDF protegido por senha (senha correta/ausente/errada), `pages=` com intervalos, JPEG vs PNG, nomes que evitam sobrescrever (`-2`), página de tamanho misto, falha no meio (P2-013), arquivo parcial (P2-014), fundo opaco (P2-015).
- `test_pdf_ops.py::test_images_to_pdf_rejects_margin_equal_to_half_page` (margem 40 mm a 72 DPI fica válida; margem que zera o espaço levanta `ValueError`) e `::test_images_to_pdf_square_image_is_portrait` (consistência com `recommend_dpi`).
- `test_pdf_ops.py::test_convert_image_modes_matrix` parametrizado (modos `1, L, LA, P, PA, RGB, RGBA, CMYK, LAB, I, I;16, F` × 5 formatos) — base: `repros/repro_p2_004_mode_matrix.py`.
- `test_pdf_ops.py::test_convert_image_cleans_temporary_file_on_failure` e `::test_images_to_pdf_leaves_no_temp_files_on_failure` (verificado manualmente, sem teste).

## 7. Falsos positivos e itens verificados sem problema
- **Hipótese "`_same_existing_file` duplicada diverge"**: a cópia usada por `images_to_pdf`/`convert_image` (`pdf_ops.py:68`) trata arquivos iguais por `os.path.samefile` e inexistentes corretamente; a cópia de `gui.py` pertence à Parte 3 — não avaliada.
- **Ampliação indevida de imagens pequenas:** não ocorre; `thumbnail` só reduz (l.249, 831). Imagens pequenas ficam em tamanho nativo centralizadas no canvas A4 — é o desenho que justifica o DPI recomendado (README l.14). O DPI mínimo 72 pode deixar imagens muito pequenas menores que a página (por desenho).
- **Tamanho da página A4:** `images_to_pdf` gera 595,20 × 841,92 pt (a 150 DPI) contra 595,28 × 841,89 pt: diferença < 0,1 pt por arredondamento de pixels, sem impacto prático.
- **Orientação:** quadrada → retrato nos dois lugares (`width > height` em `_resize_to_a4` e `image_resolution.py:50`) — consistentes.
- **Margem ≥ página:** `_resize_to_a4` levanta `ValueError` quando `min(available) < 1`; `recommend_dpi_from_images` ignora a imagem — comportamentos coerentes.
- **Fechamento de arquivos e temporários:** execução com `-X dev` e `ResourceWarning` como erro não revelou handles abertos; falhas em `images_to_pdf`/`convert_image` não deixaram `.pdf-hub-*` na pasta.
- **Crescimento de memória com muitos quadros:** linear no tamanho do PDF resultante (4 → 48 páginas: pico 146 → 281 MB; `repros/repro_p2_010_many_frames_memory.py`), sem vazamento. Não há limite de quadros (GIF com milhares de quadros gera milhares de páginas) — ver §8.
- **Arquivos corrompidos em `recommend_dpi_from_images`:** PNG com CRC inválido, IHDR zerado, IDAT truncado/lixo foram todos ignorados sem exceção (`repro_p2_011`); só `DecompressionBombError` escapa (P2-002).
- **Transparência:** `P` com `transparency`, `LA`, `RGBA` compostos sobre branco corretamente em todos os formatos (matriz `repro_p2_004`).
- **Preservação de ICC em `convert_image`:** lógica de compatibilidade (modo igual, ou RGB/RGBA→RGB; BMP sem perfil) coerente e coberta por `test_convert_image_preserves_compatible_icc_profile`.
- **Colisão de nomes na aba Converter imagens (`gui.py:4733-4737`):** `foto.png` e `foto.jpg` → `foto.jpg` e `foto-2.jpg` (laço `exists()` roda depois de cada conversão); coberto na leitura. A corrida entre `exists()` e `os.replace` em `convert_image` (l.862) é teórica (BAIXA; ver §8).
- **Qualidade 1–100 e extensões `jpg/jpeg/tif/tiff`:** validação correta em `convert_image` (l.788-808).
- **Linha `[YCbCr]` da matriz:** erro "image file is truncated" é artefato do TIFF sintético YCbCr criado pelo script, não defeito do projeto (descartado).
- **`friendly_error_message` e vazamento de caminho:** `FileExistsError` e `FileNotFoundError` não incluem caminhos (teste existente cobre `FileExistsError`).
- **Não verificado por execução:** `pdf_rendering.py` (todas as linhas), comportamento de `QPdfDocument.load` com senha, e todos os testes de GUI.

## 8. Melhorias opcionais (máx. 10 linhas)
- Parâmetro `overwrite: bool = False` em `convert_image` (hoje `os.replace` substitui silenciosamente; a GUI evita colisões, mas a API não).
- Limite opcional de quadros/páginas em `images_to_pdf` (ex.: aviso acima de 500 quadros).
- `export_pdf_pages_to_images`: aceitar `file_mode` (como as demais funções) para permissões 0600/0644.
- `OperationWorker._friendly_error_message` (`gui.py:1360-1362`) é só um invólucro de `friendly_error_message`; remover o wrapper.
- Renomear a variável local `canvas` (pdf_ops.py l.250 e 307) que sombreia `reportlab.pdfgen.canvas`.
- Remover `except Exception: raise` sem efeito em `pdf_rendering.py:106-109` (manter só o comentário).
- Remover `opened.seek(0)` desnecessário em `image_resolution.py:37`.

## 9. Checklist final de verificação pós-correção
Executar com as **versões fixadas** instaladas (`pip install -r requirements.txt -r requirements-dev.txt`):

| Comando | Resultado esperado |
|---|---|
| `QT_QPA_PLATFORM=offscreen python -m pytest -q` | tudo verde (com a falha pré-existente de `test_gui.py::test_window_preserves_space_for_controls_and_aligned_file_pickers` tratada pela Parte 3) |
| `python -m pytest -q -W error::DeprecationWarning tests/test_pdf_ops.py tests/test_image_resolution.py tests/test_errors.py` | verde, sem avisos |
| `PDFHUB_REPO=. python repros/repro_p2_003_mpo_extra_pages.py` | `paginas no PDF (esperado 1): 1` |
| `PDFHUB_REPO=. python repros/repro_p2_001_recommend_dpi_exceptions.py` | `bomba -> retornou <int>` |
| `PDFHUB_REPO=. python repros/repro_p2_011_recommend_cost_and_crc.py` | `recommend_dpi (8 JPEG 24MP)` < 0,05 s |
| `PDFHUB_REPO=. python repros/repro_p2_006_pdf_output_properties.py` | `png_captura` com `/FlateDecode`; `jpeg_com_icc` com `/DCTDecode` |
| `PDFHUB_REPO=. python repros/repro_p2_007_palette_resize_and_frames.py` | `pal_out` com > 2 cores |
| `PDFHUB_REPO=. python repros/repro_p2_005_tone_normalisation.py` | `I 50,200 -> [50, 200]` |
| `PDFHUB_REPO=. python repros/repro_p2_002_errors_mapping.py` | nenhuma das linhas "PNG truncado / MemoryError / ENOSPC / IsADirectoryError" devolve "detalhes internos ocultados"; `UnicodeEncodeError` com mensagem amigável |
| `PDFHUB_REPO=. python repros/repro_p2_004_mode_matrix.py` | sem `FALHA` em `PA`/`LAB` |
| `PDFHUB_REPO=. python repros/repro_p2_009_encoder_limits.py` | mensagens amigáveis para WebP e JPEG |
| `PDFHUB_REPO=. python repros/repro_p2_012_i18n_coverage.py` | lista "ESTATICAS SEM TRADUCAO" vazia |
| `python -W error -c "import document_tools.pdf_ops, document_tools.errors, document_tools.image_resolution, document_tools.pdf_rendering"` | sem saída (sem avisos) |
| `python -X dev` + `repros/repro_p2_008_bomb_warning_memory.py` | pico RSS menor que 1662 MB para o mesmo arquivo |
