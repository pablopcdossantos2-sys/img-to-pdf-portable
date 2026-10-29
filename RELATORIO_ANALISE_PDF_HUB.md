# Relatório de Análise — PDF Hub v0.11.1

> **ESCOPO DESTE RELATÓRIO: SOMENTE A PARTE 3 (TERCEIRA) DE 5.**
> As Partes 1, 2, 4 e 5 **não foram analisadas** aqui (ver delimitações abaixo). As seções "Parte 1/2/4/5" da seção 4 estão marcadas como *não analisadas nesta execução*.

## Delimitação das 5 partes (limites reais, medidos no código do ZIP)

| Nº | Parte | Limites reais | Analisada aqui? |
|---|---|---|---|
| 1 | Núcleo de operações em PDF | `document_tools/pdf_ops.py` l.25–197 (`parse_page_ranges` … `_copy_metadata`), l.325–748 (`merge_pdfs` … `split_pdf`), l.872–1195 (`pdf_page_count`, `reorder_pdf_pages`, `optimize_pdf`, `stamp_pdf`, `process_pdf_pipeline`); testes: `tests/test_pdf_ops.py` | **Não** |
| 2 | Imagens, renderização e erros | `pdf_ops.py` l.198–324 (`_normalise_high_bit_depth`, `_flatten_to_rgb`, `_resize_to_a4`, `images_to_pdf`) e l.749–871 (`_format_image_for_output`, `convert_image`); `pdf_rendering.py`, `image_resolution.py`, `errors.py` completos | **Não** |
| **3** | **Casca da aplicação: infraestrutura da GUI, i18n, tema, workers, build/CI e distribuição** | **`document_tools/gui.py` l.1–2146** (imports → `_change_theme`; a aba Imagens→PDF começa na l.2147); **`main.py`** (120 l.); **arquivos de projeto**: `.github/workflows/build.yml`, `.github/dependabot.yml`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `instalar-e-iniciar.bat`, `executar-aplicativo.bat`, `.gitignore`, `LICENSE`, `LICENSES-THIRD-PARTY.md`, `README.md`, `README.en.md`, `README.es.md`; testes de referência: infraestrutura de `tests/test_gui.py` | **SIM — única parte trabalhada** |
| 4 | Abas de operação individual (GUI) | `gui.py` l.2147–3468 (`_build_image_pdf_tab` … `_optimize_pdf`, imediatamente antes de `_build_pipeline_tab` na l.3469) + helpers `_add_paths`, `_remove_selected`, `_duplicate_selected`, `_move_selected` | **Não** |
| 5 | Lote, perfis, histórico, PDF→imagens, conversão | `batch_processing.py`, `report_history.py`, `profiles.py` completos; `gui.py` l.3469–4773 (`_build_pipeline_tab` … `main()` l.4765) | **Não** |

**Ajustes de fronteira (decisões tomadas):** (i) `_add_paths` (l.1860) está dentro das linhas 1–2146 mas o prompt a atribui à Parte 4 — não analisada a fundo aqui; (ii) o teste que falha (§2 do prompt) aponta para `gui.py:3193` (região da Parte 4), mas o prompt manda investigá-lo na Parte 3 — registrado como **P3-001**; (iii) `BatchFolderWorker` (l.1365–1403) consta nas Partes 3 e 5 — aqui só foi examinado como *worker/ciclo de vida de thread*.

---

## 0. Instruções para a IA que vai corrigir (copie literalmente)
- Corrija UM achado por vez, na ordem da seção 3; após cada um rode `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
- Adicione/ajuste os testes indicados; não remova testes existentes sem justificar (exceto se o achado disser que o teste está errado).
- Não altere comportamento público documentado no README sem atualizar README (pt/en/es).
- Preserve compatibilidade com Python 3.11–3.14 e com as versões fixadas.
- Em caso de conflito entre achados, siga o campo "Depende de / Conflita com".
- Se uma correção proposta se mostrar inadequada, implemente a alternativa e documente o motivo no commit.

---

## 1. Resumo executivo

- **Parte analisada: 3 de 5** (gui.py l.1–2146, main.py, build/CI, `.bat`, licenças, READMEs). Partes 1, 2, 4, 5: **não analisadas**.
- **Ambiente:** Python 3.12.3, **sem rede**, **sem PySide6 e sem pytest** → a suíte (164 ok / 1 falha, linha de base do prompt) **não pôde ser reproduzida**; análise = leitura integral linha a linha + AST + importação de `gui.py` com *stub* do PySide6 + scripts em `repros/`.
- **Achados da Parte 3: 21** — CRÍTICA 0 · ALTA 1 · MÉDIA 10 · BAIXA 10. **Transversais: 1** (T-001, MÉDIA) + 1 lista de ponteiros para outras partes (T-002, não contabilizada).
- Por confiança: CONFIRMADO 6 · PROVAVEL 11 · HIPOTESE 4 (+ T-001 PROVAVEL).
- **5 riscos mais importantes:**
  1. **P3-001** — teste de regressão quebrado (`reorder_list.wordWrap()`), bloqueia o job `test` e, por `needs`, todos os pacotes e a release.
  2. **P3-002** — o diálogo de saída **troca o nome digitado** (`relatorio 28.10.2026` → `relatorio 28.10.pdf`) por usar `Path.with_suffix`.
  3. **P3-007/P3-008** — cadeia de suprimentos e integridade da release: actions sem pin por SHA (`softprops/action-gh-release@v2` com `contents: write`), tag não validada contra `__version__`, marcador `[create-release]` pode sobrescrever release existente.
  4. **P3-003/P3-004/P3-005/T-001** — i18n incompleta: erro com prefixo EN + corpo PT, chaves ES ausentes, chave com U+200B, status que não volta ao PT, ~50 mensagens de backend sem tradução.
  5. **P3-006** — a suíte de GUI escreve nas `QSettings` reais do desenvolvedor (perfis salvos podem ser perdidos se o teste for interrompido).

---

## 2. Ambiente e linha de base

**Ambiente usado:** Linux, Python 3.12.3; instalados no sandbox: pypdf 5.9.0, Pillow 12.1.1, reportlab 4.4.10, cryptography 46.0.6 (**diferem das versões fixadas** do projeto). **Ausentes:** PySide6, pytest, pyflakes, ruff, pip-audit, PyInstaller. **Rede:** indisponível (`pip download pyside6==6.12.0` → *No matching distribution*).

**Comandos executados e resultado**

| Comando | Resultado |
|---|---|
| `unzip -l` / extração do ZIP em pasta própria | OK (36 entradas; repositório **não** modificado — trabalho em cópia) |
| `python3 -m compileall -q .` | **OK** (sem erros de sintaxe) |
| `python -W error -c "import document_tools.gui"` | **Não executável** (sem PySide6). Substituído por importação com *stub* (`repros/qt_stub.py`): `import document_tools.gui` **OK**; `TRANSLATIONS` carregada (en=414, es=407 chaves) |
| `QT_QPA_PLATFORM=offscreen python -m pytest -q` | **NÃO EXECUTADO** (sem pytest/PySide6). A falha `test_window_preserves_space_for_controls_and_aligned_file_pickers` foi **deduzida estaticamente** (P3-001); os "164 passaram" do prompt **não foram verificados** |
| `pip-audit --local`, `ruff`/`pyflakes` | **NÃO EXECUTÁVEIS**. Substituído por AST: **0 imports não usados** em `gui.py`; 0 tokens `$X` não resolvidos no QSS (claro e escuro) |
| `pip index versions` das versões fixadas (PySide6 6.12.0, pypdf 6.21.2, cryptography 50.0.2, Pillow 13.0.0, reportlab 5.1.0, pytest 9.1.1, PyInstaller 6.22.3, pip-audit 2.10.1) e das actions `@v7/@v8` | **NÃO verificável (sem rede)** — **não** se afirma que estejam erradas. Ver seção 7 |
| `repros/repro_*.py` | executados com *stub*; saídas citadas nos achados |

**Limitações:** nenhum comportamento que dependa de Qt real (renderização, QSS, drag-and-drop, threads reais, diálogos) foi executado; achados dessa natureza estão como `PROVAVEL`/`HIPOTESE`. Nenhum job do GitHub Actions foi executado; o YAML foi analisado por leitura.

---

## 3. Plano de correção ordenado

Ordenação: severidade → dependências → esforço (P <30 min · M 30 min–2 h · G >2 h).

| Ordem | ID | Sev. | Esf. | Arquivo(s) | Depende de | Resumo |
|---|---|---|---|---|---|---|
| 1 | P3-001 | ALTA | P | `gui.py:3193`, `tests/test_gui.py:971` | — | Teste exige `wordWrap()` True; código define False → suíte vermelha |
| 2 | P3-002 | MÉDIA | P | `gui.py:1920-1922` | — | `with_suffix(".pdf")` troca parte do nome digitado |
| 3 | P3-003 | MÉDIA | P | `gui.py:1989-1992` | — | Status de falha: prefixo traduzido + corpo em PT |
| 4 | P3-004 | MÉDIA | P | `gui.py` TRANSLATIONS (l.236, 536 …) | — | Chaves ES ausentes, chave com U+200B, chaves com espaço nas bordas |
| 5 | P3-005 | MÉDIA | M | `gui.py:1531-1624, 1691` | P3-003 | Trocar para PT mantém status em EN; status dinâmico nunca retraduzido |
| 6 | T-001 | MÉDIA | G | `pdf_ops.py`, `batch_processing.py`, `pdf_rendering.py`, `image_resolution.py`, `report_history.py` + `gui.py` TRANSLATIONS | P3-004 | ~50 mensagens de backend sem tradução EN/ES |
| 7 | P3-006 | MÉDIA | M | `tests/` (novo `conftest.py`) | — | Testes de GUI usam `QSettings` e histórico reais |
| 8 | P3-007 | MÉDIA | M | `.github/workflows/build.yml` (todos os `uses:`) | — | Actions sem pin por SHA |
| 9 | P3-008 | MÉDIA | M | `build.yml:209-246` | P3-007 | Release: tag ≠ versão não detectada; marcador sobrescreve release existente |
| 10 | P3-009 | MÉDIA | P | `build.yml:194-199` | — | macOS: `.app` alterado após a assinatura ad-hoc |
| 11 | P3-010 | MÉDIA | M | `main.py:17-110` | — | `--selftest` não exercita plugin JPEG do Qt, WEBP/TIFF, PDF→imagens |
| 12 | P3-011 | MÉDIA | M | `build.yml` (empacotamento), `LICENSES-THIRD-PARTY.md` | — | Pacotes sem textos/avisos de licença das dependências |
| 13 | P3-012 | BAIXA | M | `gui.py:2033-2056` | — | `closeEvent` bloqueia sessão com lote pausado |
| 14 | P3-013 | BAIXA | P | `main.py:17`, `build.yml` (jobs) | P3-010 | `--selftest` sem `try/except`; jobs sem `timeout-minutes` |
| 15 | P3-014 | BAIXA | P | `build.yml:11-13` | P3-008 | `cancel-in-progress` pode cancelar execução de release |
| 16 | P3-015 | BAIXA | P | `gui.py:1704-1826` (QSS dark) | — | Contraste do botão primário no tema escuro < 4,5:1 |
| 17 | P3-016 | BAIXA | P | `gui.py` QSS `#primaryButton`/`#secondaryButton` | P3-015 | Botões primário/secundário desabilitados sem aparência de desabilitado |
| 18 | P3-017 | BAIXA | P | `*.bat`, novo `.gitattributes` | — | `.bat` com fim de linha LF |
| 19 | P3-018 | BAIXA | P | `instalar-e-iniciar.bat:42-47` | — | Instalador aborta sem rede mesmo com `.venv` válido |
| 20 | P3-019 | BAIXA | P | `README*.md` | P3-008 | Faltam: libxcb-cursor0 (Linux), fluxo `[create-release]`, exit code do selftest no Windows |
| 21 | P3-020 | BAIXA | P | `pyproject.toml`, `requirements.txt`, `tests/` | — | Pins duplicados sem verificação de sincronia |
| 22 | P3-021 | BAIXA | P | `gui.py:88-94`, `pdf_ops.py:68-75` | — | `_same_existing_file` duplicada |

**Conflitos de arquivo previstos:** P3-003, P3-004 e P3-005 editam `gui.py` na região de i18n (aplicar nessa ordem). P3-007, P3-008, P3-009, P3-013, P3-014 editam `build.yml` (aplicar na ordem da tabela; P3-011 também altera passos de empacotamento).

---

## 4. Achados por parte

### Parte 1 — Núcleo de operações em PDF
*Não analisada nesta execução (escopo: apenas a Parte 3).*

### Parte 2 — Imagens, renderização e tratamento de erros
*Não analisada nesta execução (escopo: apenas a Parte 3).*

### Parte 3 — Casca da aplicação (gui.py l.1–2146, main.py, build/CI, distribuição)

**O que foi lido integralmente, linha a linha:** `gui.py` l.1–2146 (imports, `TRANSLATIONS` en/es, ícones, `ReorderPageDelegate`, `ReorderablePageList`, `ImageDropList`, `SideNavigationWidget`, `PageThumbnailWorker`, `OperationWorker`, `BatchFolderWorker`, `DocumentToolsWindow.__init__`, `_t`, `_capture_ui_texts`, `_apply_language`, `_stylesheet`, helpers de escolha de arquivo, `_run_task`, `_operation_*`, `closeEvent`, aba Configurações); `main.py`; `build.yml`; `dependabot.yml`; `pyproject.toml`; `requirements*.txt`; ambos `.bat`; `.gitignore`; `LICENSE` (cabeçalho/tamanho); `LICENSES-THIRD-PARTY.md`; os três READMEs (estrutura, símbolos de código e afirmações-chave comparados); `tests/test_gui.py` (nomes, fixtures, uso de `QSettings`).

#### [P3-001] Teste de regressão falha: `reorder_list.wordWrap()` é `False` no código, o teste exige `True`
- **Severidade:** ALTA
- **Categoria:** `testes`
- **Confiança:** PROVAVEL (contradição determinística código × teste; a execução do pytest não foi possível aqui, mas a linha de base do prompt relata exatamente esta falha)
- **Local:** `document_tools/gui.py:3193` (método `_build_reorder_tab`, região da Parte 4, atribuído à Parte 3 pelo prompt) e `tests/test_gui.py:970-971` (`test_window_preserves_space_for_controls_and_aligned_file_pickers`)
- **Descrição:** o teste afirma `window.reorder_list.wordWrap()` mas `_build_reorder_tab` chama `self.reorder_list.setWordWrap(False)`. A legenda de cada miniatura (`"Página 07"`) é uma única linha, mas o par `setWordWrap(False)` + `setTextElideMode(ElideNone)` **recorta** a legenda sem reticências quando a fonte do sistema é grande, o idioma gera legenda mais longa ou o DPI é alto; `wordWrap(True)` com a célula de 124×184 px (espaço sobrando) é a intenção do nome do teste ("preserves space for controls").
- **Evidência:**
  ```
  gui.py:3193        self.reorder_list.setWordWrap(False)
  gui.py:3194        self.reorder_list.setTextElideMode(Qt.TextElideMode.ElideNone)
  test_gui.py:970        assert window.reorder_list.gridSize().height() >= 160
  test_gui.py:971        assert window.reorder_list.wordWrap()
  ```
- **Como reproduzir:** `QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_gui.py::test_window_preserves_space_for_controls_and_aligned_file_pickers` → esperado: passa; observado (linha de base do prompt): `AssertionError` em `wordWrap()`. *Não reproduzido por mim: sem PySide6/pytest.*
- **Causa raiz:** alteração posterior do código (desligar o quebra-de-linha, junto com `ElideNone`) sem atualizar o teste; os dois não concordam sobre a intenção. O código é o lado frágil: `ElideNone` sem quebra de linha corta texto em silêncio.
- **Impacto:** suíte vermelha → job `test` falha → `needs: test` impede os 3 pacotes e a release. Visualmente, legendas longas (fonte grande, idiomas com texto maior) podem aparecer cortadas.
- **Correção proposta:** (recomendada) restaurar a intenção do teste no código:
  ```diff
  -        self.reorder_list.setWordWrap(False)
  +        self.reorder_list.setWordWrap(True)
  ```
  Alternativa (não recomendada): trocar o teste para `assert not window.reorder_list.wordWrap()` — mantém o risco de recorte.
- **Testes a adicionar/alterar:** nenhum novo; o teste existente passa a ser o critério. Revalidar `test_reorder_titles_are_below_thumbnails_and_layout_is_stable` (tests/test_gui.py:167) e `test_reorder_grid_renders_page_thumbnails` (:482).
- **Critério de aceite:** `QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_gui.py` → 0 falhas.
- **Risco de regressão / efeitos colaterais:** com quebra de linha ativa, uma legenda pode ocupar 2 linhas; a célula (124×184, `setSizeHint(116,172)` na l.3074) comporta; conferir que a legenda continua **abaixo** da miniatura (`ReorderPageDelegate`).
- **Depende de / Conflita com:** nenhum (coordenar com correções da Parte 4 em `_build_reorder_tab`).
- **Esforço:** P

#### [P3-002] Diálogo de saída substitui parte do nome digitado ao acrescentar `.pdf`
- **Severidade:** MÉDIA
- **Categoria:** `integridade-de-dados`
- **Confiança:** CONFIRMADO (reprodução do comportamento de `pathlib`, `repros/repro_t_behaviour.py`, item 5)
- **Local:** `document_tools/gui.py:1920-1922` (`_choose_output_pdf`); **mesmo padrão** em `gui.py:3818` (`.json`) e `gui.py:4469` (`.csv`) — Parte 5, mesma correção
- **Descrição:** se o nome digitado já contém um ponto (`relatorio 28.10.2026`, `contrato.v2`), `Path.suffix` o interpreta como extensão e `with_suffix(".pdf")` **substitui** esse trecho em vez de acrescentar `.pdf`. `setDefaultSuffix("pdf")` não ajuda: o Qt só o aplica quando não há nenhum sufixo.
- **Evidência:**
  ```python
  output = Path(dialog.selectedFiles()[0]).expanduser()
  if output.suffix.lower() != ".pdf":
      output = output.with_suffix(".pdf")
  ```
  Saída de `python3 repros/repro_t_behaviour.py`:
  ```
  digitado 'relatorio 28.10.2026' -> gravado 'relatorio 28.10.pdf'   (correto: 'relatorio 28.10.2026.pdf')
  digitado 'contrato.v2'          -> gravado 'contrato.pdf'          (correto: 'contrato.v2.pdf')
  digitado 'nota.final'           -> gravado 'nota.pdf'              (correto: 'nota.final.pdf')
  ```
- **Como reproduzir:** `python3 repros/repro_t_behaviour.py` (item 5), ou na GUI: qualquer aba → salvar como `relatorio 28.10.2026` → o arquivo e a confirmação de substituição passam a usar `relatorio 28.10.pdf`.
- **Causa raiz:** uso de `with_suffix` (troca a última "extensão" textual) onde se deseja *acrescentar* uma extensão.
- **Impacto:** o usuário recebe arquivo com nome diferente do digitado; dois relatórios com datas distintas colapsam no mesmo nome (`… 28.10.pdf`) e o segundo só é protegido pelo prompt de confirmação (que já exibe o nome alterado). Datas e versões com ponto no nome são comuns.
- **Correção proposta:** helper em nível de módulo, usado nos três pontos:
  ```python
  def _ensure_suffix(path: Path, suffix: str) -> Path:
      """Append the required extension without replacing dotted parts of the name."""
      return path if path.suffix.lower() == suffix else path.with_name(path.name + suffix)
  ```
  ```diff
  -        if output.suffix.lower() != ".pdf":
  -            output = output.with_suffix(".pdf")
  +        output = _ensure_suffix(output, ".pdf")
  ```
  Aplicar também em `gui.py:3818` (`".json"`) e `gui.py:4469` (`".csv"`).
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_choose_output_pdf_appends_extension_without_replacing_dotted_names` — `monkeypatch.setattr(QFileDialog, "exec", lambda self: QFileDialog.DialogCode.Accepted)` e `monkeypatch.setattr(QFileDialog, "selectedFiles", lambda self: [str(tmp_path / "rel 28.10.2026")])`; `assert window._choose_output_pdf("x.pdf") == str((tmp_path / "rel 28.10.2026.pdf").resolve())`. Mais um teste de unidade de `_ensure_suffix` com `"a.PDF"` (mantém), `"a"`, `"a.b"`.
- **Critério de aceite:** `pytest tests/test_gui.py -k "ensure_suffix or dotted_names"` passa; `grep -n "with_suffix" document_tools/gui.py` não retorna uso para `.pdf/.json/.csv`.
- **Risco de regressão / efeitos colaterais:** nomes terminados em `.PDF` (maiúsculo) continuam aceitos (comparação em minúsculas). Revalidar prompt de substituição (usa `output.name`).
- **Depende de / Conflita com:** nenhum (coordenar com a Parte 5 para os usos em 3818/4469).
- **Esforço:** P

#### [P3-003] Falha de operação: barra de status mistura prefixo traduzido com corpo em português
- **Severidade:** MÉDIA
- **Categoria:** `i18n`
- **Confiança:** CONFIRMADO (`repros/repro_t_behaviour.py`, item 2)
- **Local:** `document_tools/gui.py:1989-1992` (`_operation_failed`) e `gui.py:1620-1624` (laço `{message}` de `_t`)
- **Descrição:** `_operation_failed` monta um f-string **antes** de traduzir; `_t` só traduz o prefixo (`"Não foi possível concluir a operação: "`) e devolve o corpo (a mensagem amigável em PT) sem tradução. O diálogo logo abaixo traduz o corpo corretamente, de modo que status e diálogo ficam em idiomas diferentes.
- **Evidência:**
  ```python
  self.status_label.setText(self._t(f"Não foi possível concluir a operação: {message}"))
  QMessageBox.warning(self, self._t("Operação não concluída"), self._t(message))
  ```
  Saída:
  ```
  status em EN: Could not complete operation: O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente.
  corpo no diálogo: The file or folder could not be found. Check the path and try again.
  ```
- **Como reproduzir:** `python3 repros/repro_t_behaviour.py` ou, na GUI em EN/ES, provocar erro de arquivo inexistente.
- **Causa raiz:** montagem de texto antes da tradução (a chave `"… {message}"` existe em `TRANSLATIONS`, mas é usada via heurística de prefixo, que não traduz o `{message}`).
- **Impacto:** usuários EN/ES veem frase meio traduzida na barra de status em todo erro de operação.
- **Correção proposta:**
  ```python
  def _operation_failed(self, message: str) -> None:
      self.open_directory_button.hide()
      self.status_label.setText(
          self._t("Não foi possível concluir a operação: {message}").format(message=self._t(message))
      )
      QMessageBox.warning(self, self._t("Operação não concluída"), self._t(message))
  ```
  (em PT `_t` devolve o modelo intacto e `.format` o preenche). O laço `{message}` de `_t` (l.1620-1624) pode ser removido depois que nenhum chamador monte o texto por f-string — verificar com `grep -n '_t(f"' document_tools/gui.py`.
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_failed_operation_status_is_fully_translated` — `monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)`; idioma `en`; `window._operation_failed("O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente.")`; `assert window.status_label.text() == "Could not complete operation: The file or folder could not be found. Check the path and try again."`; repetir para `es`.
- **Critério de aceite:** o teste acima passa em `en` e `es`; `grep -n '_t(f"' document_tools/gui.py` sem resultados que contenham mensagens de erro.
- **Risco de regressão / efeitos colaterais:** `BatchFolderWorker.failed` também chama `_operation_failed` — revalidar o fluxo de lote.
- **Depende de / Conflita com:** conflita com P3-005 (mesma região de `_t`); aplicar P3-003 primeiro.
- **Esforço:** P

#### [P3-004] Tabelas `TRANSLATIONS`: chaves ES ausentes, chave com U+200B e chaves com espaço nas bordas (inalcançáveis)
- **Severidade:** MÉDIA
- **Categoria:** `i18n`
- **Confiança:** CONFIRMADO (`repros/repro_i18n_coverage.py` e verificação em *stub*)
- **Local:** `document_tools/gui.py` — chave `es` com U+200B na **l.536**; diálogo sem chave ES na **l.2031** (`_open_output_directory`); chaves com espaço nas bordas nas tabelas `en`/`es` (`"PDFs misturados: "`, `"PDF com páginas inseridas: "`, `" Falhas: {count}."`); 8 chaves presentes só em `en`
- **Descrição:** (a) a chave ES `"Salv\u200bar somente as páginas necessárias"` contém um caractere de largura zero e nunca casa — é lixo ao lado da chave correta; (b) 8 chaves só existem em `en`: `"Abra esta pasta manualmente:\n{path}"` (usada na l.2031), `"Criando PDF a partir das imagens…"` (usada na l.2305), `"Criando PDF a partir das imagens"`, `"Escolha otimização sem perdas ou equilibrada."`, `"Escolha uma senha por PDF ou deixe a senha como None."`, `"Processamento local:"`, `"Qualidade JPEG precisa ficar entre 50 e 95."`, `"Selecione pelo menos um arquivo de origem."`; (c) `_t` procura `core = text.strip()`; chaves com espaço nas bordas **jamais** casam. `" Falhas: {count}."` (usada na l.4757) fica sem tradução em EN **e** ES; as duas primeiras só funcionam por acaso via `dynamic_prefixes`.
- **Evidência (execução com *stub*):**
  ```
  only in en: ['Abra esta pasta manualmente:\n{path}', 'Criando PDF a partir das imagens', 'Criando PDF a partir das imagens…',
               'Escolha otimização sem perdas ou equilibrada.', 'Escolha uma senha por PDF ou deixe a senha como None.',
               'Processamento local:', 'Qualidade JPEG precisa ficar entre 50 e 95.', 'Selecione pelo menos um arquivo de origem.']
  only in es: ['Salv\u200bar somente as páginas necessárias']
  INVISIBLE CHAR in es key: 'Salv\u200bar somente as páginas necessárias'
  chaves com espaço nas bordas: 'PDFs misturados: ', 'PDF com páginas inseridas: ', ' Falhas: {count}.'
  _t(" Falhas: {count}.") em 'en' -> ' Falhas: {count}.'   (esperado: ' Failures: {count}.')
  ```
- **Como reproduzir:** `python3 repros/repro_i18n_coverage.py` e `python3 repros/repro_t_behaviour.py`.
- **Causa raiz:** tabelas mantidas à mão em três blocos (`TRANSLATIONS` + dois `.update(...)`), sem teste de paridade; `_t` normaliza o texto de entrada mas não as chaves.
- **Impacto:** em ES, o diálogo "Abra esta pasta manualmente" e o status "Criando PDF…" aparecem em português; em EN/ES o resumo de conversão de imagens exibe " Falhas: n" em português.
- **Correção proposta:** (1) apagar a chave da l.536 (a versão correta, sem U+200B, já existe na linha seguinte); (2) acrescentar em `es`: `"Abra esta pasta manualmente:\n{path}": "Abre esta carpeta manualmente:\n{path}"`, `"Criando PDF a partir das imagens…": "Creando PDF a partir de las imágenes…"` (e a variante sem reticências), `"Escolha otimização sem perdas ou equilibrada.": "Elige optimización sin pérdida o equilibrada."`, `"Escolha uma senha por PDF ou deixe a senha como None.": "Indica una contraseña por PDF o deja la contraseña como None."`, `"Processamento local:": "Procesamiento local:"`, `"Qualidade JPEG precisa ficar entre 50 e 95.": "La calidad JPEG debe estar entre 50 y 95."`, `"Selecione pelo menos um arquivo de origem.": "Selecciona al menos un archivo de origen."`; (3) normalizar chaves no carregamento (logo após os três blocos) e remover os espaços das chaves problemáticas:
  ```python
  for _lang, _table in TRANSLATIONS.items():
      TRANSLATIONS[_lang] = {k.strip(): v.strip() if k != k.strip() else v for k, v in _table.items()}
  ```
  e, na l.4757, trocar `self._t(" Falhas: {count}.")` por `" " + self._t("Falhas: {count}.")` com a chave `"Falhas: {count}."` (sem espaço) em `en`/`es`.
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_translation_tables_are_in_parity_and_clean` — `set(TRANSLATIONS["en"]) == set(TRANSLATIONS["es"])`; nenhuma chave com `\u200b`/`\u200c`/`\u200d`/`\ufeff`; `all(k == k.strip() for k in …)`.
- **Critério de aceite:** o teste acima passa; `python3 repros/repro_i18n_coverage.py` mostra "chaves com caractere invisível: []".
- **Risco de regressão / efeitos colaterais:** a normalização de chaves não pode alterar chaves com `\n` interno (usa só `strip`). Textos ES são sugestões — revisar por falante nativo.
- **Depende de / Conflita com:** precedência sobre T-001; conflita (mesma região) com P3-003/P3-005.
- **Esforço:** P

#### [P3-005] Trocar o idioma para PT não reverte o status; mensagens com valores/caminhos nunca são retraduzidas
- **Severidade:** MÉDIA
- **Categoria:** `i18n`
- **Confiança:** CONFIRMADO (`repros/repro_t_behaviour.py`, itens 1 e 3)
- **Local:** `document_tools/gui.py:1533-1534` (`_t`, retorno antecipado para `pt`), `gui.py:1691` (`_apply_language`), `gui.py:1550` (busca reversa)
- **Descrição:** `_apply_language` tenta "atualizar" o status com `self._t(self.status_label.text())`. (a) Para `pt`, `_t` retorna o texto sem mexer; um status já traduzido para EN/ES **permanece** em EN/ES. (b) Em EN/ES, mensagens com valores interpolados (`"PDF carimbado: /x.pdf"`, `"PDF otimizado: 1 KB → 1 KB (10% menor)"`, `"3 páginas salvas em: …"`) não estão na lista `dynamic_prefixes` e ficam no idioma anterior. A busca reversa (l.1550) reconstrói dois dicionários a cada chamada.
- **Evidência:**
  ```python
  if self._language == "pt":
      return text
  ```
  ```
  1a) EN: Ready. Choose a tool from the left menu.
  1b) após voltar p/ PT, _t(status) = 'Ready. Choose a tool from the left menu.'  (esperado: texto em português)
  3) 'PDF carimbado: /tmp/a.pdf' -> 'PDF carimbado: /tmp/a.pdf'   (em 'en')
  ```
- **Como reproduzir:** abrir em EN (ou escolher EN), voltar a "Português (Brasil)": o rodapé segue em inglês. `python3 repros/repro_t_behaviour.py`.
- **Causa raiz:** o status é armazenado já traduzido, e a "origem em PT" não é guardada; `_t` tenta reconstruir a origem por heurística.
- **Impacto:** após trocar idioma, o rodapé exibe texto no idioma errado até a próxima ação.
- **Correção proposta:** guardar a origem em PT e re-renderizar:
  ```python
  # __init__ (após criar status_label)
  self._status_source = self.status_label.text()

  def _set_status(self, source_pt: str) -> None:
      self._status_source = source_pt
      self.status_label.setText(self._t(source_pt))
  ```
  e em `_apply_language` substituir a l.1690-1691 por `self.status_label.setText(self._t(self._status_source))`. Migrar os chamadores `self.status_label.setText(self._t(X))` para `self._set_status(X)`; nos casos com `.format(...)` passar o texto PT já formatado (`self._set_status(template_pt.format(...))` — a tradução ocorre dentro de `_set_status` apenas se o texto for exatamente uma chave; para textos com valores, preferir guardar `(template_pt, kwargs)` e traduzir o *modelo* antes do `.format`).
  Alternativa mínima (menos robusta): em `_t`, antes do retorno para `pt`, aplicar a busca reversa para chaves estáticas.
  Mover a construção dos dicionários reversos para o carregamento do módulo (`_REVERSE = {lang: {v: k …}}`).
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_status_text_follows_language_round_trip` — status "Pronto. Selecione uma ferramenta no menu lateral." → `en` → `pt` → `assert window.status_label.text() == "Pronto. Selecione uma ferramenta no menu lateral."`; e um status com valores (ex.: `"Perfil salvo: X"`) em `pt→en→es→pt`.
- **Critério de aceite:** o teste acima passa; `pytest tests/test_gui.py -k "language"` verde.
- **Risco de regressão / efeitos colaterais:** a migração dos ~40 chamadores de `status_label.setText` está nas Partes 4/5 (conflito de arquivo); fazer em um commit só, depois de P3-003. Revalidar `batch_pause_button` e `_refresh_batch_history_combo` em `_apply_language`.
- **Depende de / Conflita com:** depende de P3-003; conflita com Partes 4/5 (mesmo arquivo).
- **Esforço:** M

#### [P3-006] Testes de GUI usam as `QSettings` e o histórico de lotes reais do usuário
- **Severidade:** MÉDIA
- **Categoria:** `testes`
- **Confiança:** PROVAVEL (leitura: não há `conftest.py` nem isolamento; não executado)
- **Local:** `tests/test_gui.py` (ex.: l.172-197, 526-585, 595-645, 656-696, 739-787, 1004-1038, 1075-1091); `document_tools/gui.py:1418` (`QSettings("PDFHub", "PDF Hub")`) e `gui.py:1419-1420` (diretório `batch-reports` em `AppDataLocation`)
- **Descrição:** cada teste cria `DocumentToolsWindow()` que abre as `QSettings` **reais** e lê o histórico real de relatórios. Vários testes sobrescrevem chaves reais (`pipeline_profiles` → `"{}"`, `theme`, `language`) e só as restauram em `finally`. O `--selftest` do próprio `main.py` já isola as configurações (l.35-47), mas a suíte não.
- **Evidência:**
  ```python
  # tests/test_gui.py:526-529
  window = DocumentToolsWindow()
  previous_profiles = window.settings.value("pipeline_profiles", None)
  try:
      window.settings.setValue("pipeline_profiles", "{}")
  ```
  `ls tests/` → não existe `conftest.py`.
- **Como reproduzir:** em máquina com perfis salvos, rodar a suíte e interromper (Ctrl+C / kill) durante `test_pipeline_profile_saves_loads_and_deletes_options_without_paths_or_passwords` → `pipeline_profiles` permanece `"{}"`/estado de teste. Também: `test_language_selector_translates_tabs…` termina forçando `pt` mesmo que o usuário usasse `en`.
- **Causa raiz:** ausência de fixture de isolamento; restauração manual via `try/finally` não protege contra interrupção.
- **Impacto:** desenvolvedor pode perder perfis de fluxo/preferências locais; testes dependem do estado da máquina (não reprodutíveis em CI vs. local).
- **Correção proposta:** criar `tests/conftest.py`:
  ```python
  import os
  import pytest

  os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


  @pytest.fixture(autouse=True, scope="session")
  def _isolated_user_state(tmp_path_factory):
      root = tmp_path_factory.mktemp("user-state")
      for name in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "APPDATA", "LOCALAPPDATA"):
          os.environ[name] = str(root)
      from PySide6.QtCore import QSettings
      QSettings.setDefaultFormat(QSettings.Format.IniFormat)
      QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(root))
      yield
  ```
  (variáveis de ambiente definidas **antes** de qualquer `QStandardPaths`; o módulo `conftest` é importado antes dos testes). Manter os `try/finally` existentes.
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_test_suite_does_not_touch_real_user_settings` — `assert Path(window.settings.fileName()).is_relative_to(Path(os.environ["HOME"]))` e `window._batch_history_directory` idem.
- **Critério de aceite:** com `HOME` apontando para um diretório com `pipeline_profiles` conhecido, `pytest -q` não altera esse arquivo (`sha256sum` antes/depois idêntico).
- **Risco de regressão / efeitos colaterais:** testes que dependem de `Desktop` (`test_desktop_is_the_default_folder_for_save_dialogs`, l.822) podem precisar do `monkeypatch` já existente; revalidar. Windows usa `APPDATA`/`LOCALAPPDATA` (cobertos).
- **Depende de / Conflita com:** nenhum.
- **Esforço:** M

#### [P3-007] Actions de terceiros referenciadas por tag móvel, sem pin por SHA
- **Severidade:** MÉDIA
- **Categoria:** `build-ci`
- **Confiança:** PROVAVEL (leitura do YAML; a existência das versões `@v7/@v8` **não pôde ser verificada sem rede** — ver seção 7)
- **Local:** `.github/workflows/build.yml:30,38,66,68,105,120,127,155,170,172,201,223,231,236` (todas as linhas `uses:`)
- **Descrição:** todas as actions usam tags móveis (`actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`, `softprops/action-gh-release@v2`). O job `publish-release` roda com `contents: write` e usa uma action de terceiros (`softprops`) — uma tag reescrita no upstream executaria código arbitrário com permissão de escrita no repositório.
- **Evidência:**
  ```yaml
  # build.yml:219-221 e 236
  permissions:
    contents: write
  ...
  uses: softprops/action-gh-release@v2
  ```
- **Como reproduzir:** `grep -nE "uses: .+@v[0-9]" .github/workflows/build.yml` → 14 ocorrências.
- **Causa raiz:** pin por tag; Dependabot (`.github/dependabot.yml`) já está configurado para `github-actions` e saberia atualizar SHAs.
- **Impacto:** risco de cadeia de suprimentos sobre o job que publica binários; (ações `actions/*` têm risco menor que `softprops`).
- **Correção proposta:** (1) verificar que cada tag existe: `gh api repos/actions/checkout/git/ref/tags/v7 --jq .object` (repetir para as demais; se a tag for anotada, resolver o commit com `gh api repos/<owner>/<repo>/git/tags/<sha>`); (2) trocar por SHA de 40 hex com comentário: `uses: actions/checkout@<SHA-de-40-hex> # v7`; (3) manter `dependabot.yml` para atualizar SHAs. **Não** inventar SHAs: obter via `gh`/API.
- **Testes a adicionar/alterar:** N/A (verificação de workflow). Opcional: `tests/test_project_metadata.py::test_workflow_actions_are_pinned_to_sha` com regex `uses:\s+\S+@[0-9a-f]{40}`.
- **Critério de aceite:** `grep -nE "uses: .+@v[0-9]" .github/workflows/build.yml` retorna vazio; o workflow continua válido (`python -c "import yaml,sys;yaml.safe_load(open('.github/workflows/build.yml'))"`).
- **Risco de regressão / efeitos colaterais:** se uma tag citada não existir, o workflow falha na resolução — corrigir a versão antes do pin.
- **Depende de / Conflita com:** precede P3-008 (mesmo arquivo).
- **Esforço:** M

#### [P3-008] Release: a tag não é validada contra `__version__` e o marcador `[create-release]` pode sobrescrever uma release existente
- **Severidade:** MÉDIA
- **Categoria:** `build-ci`
- **Confiança:** PROVAVEL (leitura do YAML; comportamento exato de `softprops/action-gh-release@v2` sobre releases/asset existentes deve ser confirmado em sua documentação)
- **Local:** `.github/workflows/build.yml:209-246` (job `publish-release`)
- **Descrição:** (a) qualquer tag `v*` publica, e `tag_name` usa `github.ref_name`; **nada** compara a tag com `document_tools.__version__` → uma tag `v0.12.0` empacota binários `0.11.1`. (b) No fluxo `[create-release]` na `main`, a tag é `v{__version__}`; se a versão não foi incrementada, o mesmo `tag_name` já existe e a action atualiza a release existente (e, por padrão, substitui assets de mesmo nome), com binários de outro commit — o tag continua apontando para o commit antigo.
- **Evidência:**
  ```yaml
  # build.yml:213-216, 238
  if: >-
    startsWith(github.ref, 'refs/tags/v') ||
    (github.ref == 'refs/heads/main' &&
    contains(github.event.head_commit.message, '[create-release]'))
  ...
  tag_name: ${{ github.ref == 'refs/heads/main' && contains(...,'[create-release]') && format('v{0}', steps.app-version.outputs.version) || github.ref_name }}
  ```
- **Como reproduzir:** (1) criar a tag `v9.9.9` num commit com `__version__ = "0.11.1"` → o job publica `PDF Hub v9.9.9` com binários 0.11.1. (2) Dois commits na `main` com `[create-release]` e a mesma `__version__`.
- **Causa raiz:** falta de passo de validação; `tag_name`/`target_commitish` assumem coerência.
- **Impacto:** releases com número de versão incorreto; substituição silenciosa de assets de uma release já distribuída.
- **Correção proposta:** inserir após "Read application version" (e usar `python3`, não `python`):
  ```yaml
        - name: Read application version
          id: app-version
          shell: bash
          run: echo "version=$(python3 -c 'from document_tools import __version__; print(__version__)')" >> "$GITHUB_OUTPUT"

        - name: Validate tag against application version
          if: startsWith(github.ref, 'refs/tags/v')
          shell: bash
          run: |
            expected="v${{ steps.app-version.outputs.version }}"
            test "$GITHUB_REF_NAME" = "$expected" || { echo "::error::Tag $GITHUB_REF_NAME != $expected"; exit 1; }

        - name: Refuse to replace an existing release (marker flow)
          if: github.ref == 'refs/heads/main'
          shell: bash
          env:
            GH_TOKEN: ${{ github.token }}
          run: |
            if gh release view "v${{ steps.app-version.outputs.version }}" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
              echo "::error::Release v${{ steps.app-version.outputs.version }} already exists; bump __version__."
              exit 1
            fi
  ```
  e, se a documentação da action confirmar o input, acrescentar `overwrite_files: false` ao passo de publicação.
- **Testes a adicionar/alterar:** N/A (CI). Validar com `workflow_dispatch` em um fork e uma tag de teste.
- **Critério de aceite:** tag `v0.11.2` sobre `__version__ = "0.11.1"` → job falha com `::error::`; segunda execução do marcador com versão repetida → falha.
- **Risco de regressão / efeitos colaterais:** o fluxo por tag passa a exigir que `__version__` seja alterado **antes** de taguear (documentar no README — P3-019).
- **Depende de / Conflita com:** depende de P3-007 (mesma região); conflita com P3-014/P3-011 no mesmo arquivo.
- **Esforço:** M

#### [P3-009] macOS: arquivos de licença copiados para dentro do `.app` após a assinatura ad-hoc
- **Severidade:** MÉDIA
- **Categoria:** `build-ci`
- **Confiança:** HIPOTESE (comportamento do `codesign` não verificável aqui; depende de o PyInstaller ter assinado o bundle, o que faz em arm64)
- **Local:** `.github/workflows/build.yml:194-199` (passo "Package and checksum" do `package-macos`)
- **Descrição:** o passo copia `LICENSE` e `LICENSES-THIRD-PARTY.md` para `PDF Hub.app/Contents/Resources/` **depois** de o PyInstaller construir (e assinar ad-hoc) o bundle, e depois do smoke test. Adicionar arquivos a `Contents/Resources` invalida o selo de recursos (`_CodeSignature/CodeResources`); o pacote baixado (com atributo de quarentena) pode ser recusado pelo Gatekeeper como "danificado".
- **Evidência:**
  ```yaml
  mkdir -p "dist/PDF Hub.app/Contents/Resources"
  cp LICENSE LICENSES-THIRD-PARTY.md "dist/PDF Hub.app/Contents/Resources/"
  ditto -c -k --sequesterRsrc --keepParent "dist/PDF Hub.app" "dist/PDF-Hub-macOS-arm64.zip"
  ```
- **Como reproduzir:** em macOS arm64: `codesign --verify --deep --strict --verbose=2 "dist/PDF Hub.app"` **antes** e **depois** da cópia; esperado após: erro "a sealed resource is missing or invalid / file added".
- **Causa raiz:** modificação do bundle após a assinatura.
- **Impacto:** possível falha de abertura em macOS para o usuário final (além do aviso já documentado de app não notarizado).
- **Correção proposta:** não alterar o `.app`; empacotar as licenças ao lado dele:
  ```yaml
        - name: Package and checksum
          run: |
            codesign --verify --deep --strict --verbose=2 "dist/PDF Hub.app"
            rm -rf stage && mkdir -p stage
            ditto "dist/PDF Hub.app" "stage/PDF Hub.app"
            cp LICENSE LICENSES-THIRD-PARTY.md stage/
            (cd stage && ditto -c -k --sequesterRsrc . "../dist/PDF-Hub-macOS-arm64.zip")
            (cd dist && shasum -a 256 PDF-Hub-macOS-arm64.zip > PDF-Hub-macOS-arm64.zip.sha256)
  ```
  Alternativa: ressignar ad-hoc após a cópia: `codesign --force --deep --sign - "dist/PDF Hub.app"` e repetir o smoke test.
- **Testes a adicionar/alterar:** N/A (CI); o `codesign --verify` acima funciona como teste.
- **Critério de aceite:** o passo `codesign --verify` termina com código 0 no job `package-macos`.
- **Risco de regressão / efeitos colaterais:** o zip passa a ter `PDF Hub.app` + 2 arquivos na raiz; atualizar README (instrução "abra `PDF Hub.app`") se necessário.
- **Depende de / Conflita com:** conflita com P3-011 (passo de empacotamento) — aplicar em conjunto.
- **Esforço:** P

#### [P3-010] `--selftest` não exercita o plugin JPEG do Qt, WEBP/TIFF do Pillow nem PDF→imagens
- **Severidade:** MÉDIA
- **Categoria:** `testes`
- **Confiança:** HIPOTESE (a omissão é certa; se o executável congelado realmente perde esses plugins só se vê no build)
- **Local:** `main.py:17-110` (`selftest`); consumidores: `document_tools/pdf_rendering.py:102` (`image.save(..., "JPEG")` via plugin `qjpeg` do Qt) e `document_tools/pdf_ops.py:772-871` (`convert_image` → JPEG/WEBP/TIFF)
- **Descrição:** o selftest valida: UI, miniatura (QtPdf), PNG→PDF, reordenar, carimbar, otimizar, pipeline e AES-256 (cryptography). **Não** valida: `QImage.save(..., "JPEG")` (depende do plugin `imageformats/qjpeg` empacotado), `convert_image` para JPEG/WEBP/TIFF (codecs/plug-ins do Pillow), nem `export_pdf_pages_to_images`. Um pacote sem esses plugins passaria no CI e falharia no uso (PDF→JPEG; conversão para WEBP).
- **Evidência:** `grep -n "export_pdf_pages_to_images\|convert_image" main.py` → sem resultados; `pdf_rendering.py:102`: `if not image.save(str(destination), encoder, int(quality) if encoder == "JPEG" else -1)`.
- **Como reproduzir:** `grep -nE "export_pdf_pages_to_images|convert_image|JPEG|WEBP|TIFF" main.py` (vazio). Prova real: build congelado sem o plugin → `export_pdf_pages_to_images(..., image_format="JPEG")` levanta `ValueError`/falha ao salvar.
- **Causa raiz:** cobertura do smoke test limitada às operações PDF.
- **Impacto:** regressões de empacotamento em recursos de imagem só seriam notadas por usuários.
- **Correção proposta:** estender o selftest (códigos de saída novos 7 e 8):
  ```python
  from document_tools.pdf_ops import convert_image
  from document_tools.pdf_rendering import export_pdf_pages_to_images
  ...
  for image_format, extension in (("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp"), ("TIFF", ".tif")):
      converted = convert_image(image_path, root / f"converted{extension}", image_format, quality=80)
      with Image.open(converted) as check:
          check.load()
  pages_dir = root / "pages"; pages_dir.mkdir()
  for fmt in ("PNG", "JPEG"):
      files = export_pdf_pages_to_images(image_pdf, pages_dir, image_format=fmt, dpi=72)
      if len(files) != 1 or not files[0].is_file() or files[0].stat().st_size == 0:
          return _selftest_failure(7, f"PDF page export ({fmt})")
  ```
  (embrulhar a conversão em `try/except` retornando `_selftest_failure(8, "image conversion")`).
- **Testes a adicionar/alterar:** `tests/test_gui.py` ou novo `tests/test_main.py::test_selftest_returns_zero` — `monkeypatch.setenv("QT_QPA_PLATFORM","offscreen")`; `assert main.selftest() == 0`.
- **Critério de aceite:** `QT_QPA_PLATFORM=offscreen python main.py --selftest; echo $?` → `0`; nos três jobs de pacote, o selftest do executável congelado continua verde.
- **Risco de regressão / efeitos colaterais:** WEBP/TIFF dependem das bibliotecas incluídas na wheel do Pillow; se o selftest falhar em algum SO, investigar hooks do PyInstaller (`--collect-all PIL`).
- **Depende de / Conflita com:** relacionado a P3-013 (mesma função).
- **Esforço:** M

#### [P3-011] Pacotes distribuídos sem os avisos/textos de licença das dependências incluídas
- **Severidade:** MÉDIA
- **Categoria:** `dependencias-licencas`
- **Confiança:** PROVAVEL (risco de conformidade; **não é aconselhamento jurídico** — validar com quem responde pela licença do projeto)
- **Local:** `.github/workflows/build.yml:101` (zip Windows), `:151-152` (tar Linux), `:197` (macOS); `LICENSES-THIRD-PARTY.md` (resumo informativo)
- **Descrição:** os binários (PyInstaller) embutem PySide6/Qt (LGPL-3.0/GPL), pypdf (BSD-3), cryptography (Apache-2.0/BSD-3), Pillow (MIT-CMU), reportlab (BSD). O pacote leva apenas o `LICENSE` (AGPL do projeto) e `LICENSES-THIRD-PARTY.md`, que **lista nomes de licença** e declara não substituir os textos. BSD/MIT/Apache exigem reproduzir o aviso de copyright/licença na redistribuição em binário; a LGPL exige incluir o texto e permitir a substituição das bibliotecas Qt (relevante para `--onefile`).
- **Evidência:**
  ```
  Compress-Archive -Path .\dist\PDFHub.exe, .\dist\PDFHub.exe.sha256, .\LICENSE, .\LICENSES-THIRD-PARTY.md ...
  LICENSES-THIRD-PARTY.md: "This summary is informational and does not replace the complete license texts…"
  ```
- **Como reproduzir:** extrair `PDF-Hub-Windows-x64.zip` → 4 arquivos; nenhum contém o texto das licenças das dependências.
- **Causa raiz:** o processo de empacotamento não coleta os `LICENSE`/`NOTICE` das dependências.
- **Impacto:** exposição de conformidade ao redistribuir binários; o próprio documento já alerta para isso.
- **Correção proposta:** gerar no CI um `THIRD-PARTY-NOTICES.txt` com os textos de licença das dependências **efetivamente instaladas** (ex.: `pip-licenses --format=plain-vertical --with-license-file --no-license-path --output-file THIRD-PARTY-NOTICES.txt`, fixando a versão da ferramenta), incluir o texto da LGPL-3.0 do Qt for Python e a indicação de onde obter o código-fonte das bibliotecas Qt, e empacotá-lo nos três artefatos junto de `LICENSE`. Manter `LICENSES-THIRD-PARTY.md` como índice e uniformizar o idioma do arquivo (hoje mistura PT e EN).
- **Testes a adicionar/alterar:** N/A (CI). Opcional: passo que falha se `THIRD-PARTY-NOTICES.txt` estiver vazio.
- **Critério de aceite:** os três artefatos contêm `THIRD-PARTY-NOTICES.txt` com o texto de licença de PySide6, pypdf, cryptography, Pillow e reportlab.
- **Risco de regressão / efeitos colaterais:** aumento pequeno do tamanho do pacote; macOS: aplicar junto de P3-009 (colocar ao lado do `.app`, não dentro).
- **Depende de / Conflita com:** conflita com P3-009 (empacotamento macOS).
- **Esforço:** M

#### [P3-012] `closeEvent` recusa fechar com lote pausado e não oferece cancelar
- **Severidade:** BAIXA
- **Categoria:** `ui-ux`
- **Confiança:** PROVAVEL (leitura de `closeEvent` e `BatchControl`; não executado com Qt)
- **Local:** `document_tools/gui.py:2033-2043` (`closeEvent`); `document_tools/batch_processing.py:59-64` (`wait_until_resumed`)
- **Descrição:** com qualquer worker ativo, `closeEvent` mostra "Aguarde a conclusão…" e chama `event.ignore()`. Num lote **pausado**, o worker fica bloqueado em `Condition.wait()` (thread viva): a janela só fecha após o usuário retomar/cancelar manualmente. O texto "aguarde" é enganoso e o veto também barra o encerramento da sessão do SO (logoff/shutdown no Windows) enquanto o lote estiver pausado.
- **Evidência:**
  ```python
  worker = self._worker
  if worker is not None and worker.isRunning():
      QMessageBox.information(self, APP_NAME, self._t("Uma operação está em andamento. Aguarde a conclusão antes de fechar o aplicativo."))
      event.ignore()
      return
  ```
- **Como reproduzir:** iniciar um lote, clicar em "Pausar lote", tentar fechar a janela → mensagem "aguarde" e a janela permanece.
- **Causa raiz:** o veto não distingue lote (que tem `BatchControl.cancel()`) de operações únicas.
- **Impacto:** UX confusa e bloqueio de logoff com lote pausado; sem perda de dados (o checkpoint é preservado no cancelamento).
- **Correção proposta:** para lote em andamento, perguntar e cancelar:
  ```python
  if worker is not None and worker.isRunning():
      control = self._batch_control
      if self._folder_batch_running and control is not None:
          answer = QMessageBox.question(
              self, APP_NAME,
              self._t("Há um lote em andamento. Cancelar o lote e sair?"),
              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
              QMessageBox.StandardButton.No,
          )
          if answer == QMessageBox.StandardButton.Yes:
              control.cancel()
              self._close_when_idle = True
          event.ignore()
          return
      ...mensagem atual...
  ```
  e, no fim de `_operation_finished`: `if getattr(self, "_close_when_idle", False): QTimer.singleShot(0, self.close)` (importar `QTimer` de `PySide6.QtCore`). Adicionar a nova chave em `en`/`es`.
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_close_with_paused_batch_offers_cancel` — simular `window._folder_batch_running=True`, `window._batch_control=BatchControl()`, worker falso com `isRunning()==True`; `monkeypatch` de `QMessageBox.question` → `Yes`; chamar `window.close()`; assert `window._batch_control` foi cancelado (`control._cancel_requested`).
- **Critério de aceite:** o teste acima passa; fechar com operação *única* em andamento continua mostrando a mensagem atual.
- **Risco de regressão / efeitos colaterais:** o cancelamento só efetiva após o PDF atual (documentado no README); revalidar `_operation_finished` (ramo de lote) e `test_gui` de lote.
- **Depende de / Conflita com:** nenhum (toca `_operation_finished`, comum a P3-003).
- **Esforço:** M

#### [P3-013] `--selftest` sem tratamento de exceção e jobs sem `timeout-minutes` (risco de travar o CI)
- **Severidade:** BAIXA
- **Categoria:** `build-ci`
- **Confiança:** HIPOTESE (comportamento do bootloader `--windowed` do PyInstaller em exceção não tratada não verificado aqui)
- **Local:** `main.py:17-108` (`selftest`) e `main.py:110-112` (`main`); `.github/workflows/build.yml` (nenhum job define `timeout-minutes`; o padrão do GitHub é 360 min)
- **Descrição:** `selftest()` não captura exceções (um `ImportError` ou erro de plugin escapa). No executável Windows `--windowed`, uma exceção não tratada tende a abrir uma caixa de diálogo modal do bootloader; o passo `Start-Process -Wait` aguardaria o clique até o *timeout* de 6 h do job. Além disso, em build `--windowed` `sys.stderr` pode ser `None`, então `_selftest_failure` (que imprime em `sys.stderr`) não deixa rastro.
- **Evidência:**
  ```python
  def _selftest_failure(code: int, stage: str) -> int:
      print(f"PDF Hub selftest failed ({code}): {stage}", file=sys.stderr)
  ...
  def main() -> int:
      if "--selftest" in sys.argv:
          return selftest()
  ```
- **Como reproduzir:** no Windows, gerar o `.exe` e fazê-lo falhar (ex.: remover um plugin) com `Start-Process -Wait` → processo preso em diálogo (a confirmar).
- **Causa raiz:** ausência de `try/except` global no modo selftest e de limites de tempo no workflow.
- **Impacto:** runner ocupado por horas e diagnóstico perdido quando o selftest falha no Windows.
- **Correção proposta:**
  ```python
  def main() -> int:
      if "--selftest" in sys.argv:
          try:
              return selftest()
          except BaseException:  # noqa: BLE001 - smoke test must always return a code
              import traceback
              log = Path(tempfile.gettempdir()) / "pdf-hub-selftest.log"
              log.write_text(traceback.format_exc(), encoding="utf-8")
              if sys.stderr is not None:
                  traceback.print_exc()
              return 1
  ```
  e no workflow: `timeout-minutes: 30` em cada job e `timeout-minutes: 5` nos passos "Smoke-test"; no Windows, imprimir o log em caso de falha (`if: failure()` com `Get-Content $env:TEMP\pdf-hub-selftest.log`).
- **Testes a adicionar/alterar:** `tests/test_main.py::test_selftest_failure_returns_nonzero_and_logs` — `monkeypatch.setattr(main, "selftest", lambda: (_ for _ in ()).throw(RuntimeError("x")))`; `main.main()` com `sys.argv=["x","--selftest"]` → retorno `1` e log criado.
- **Critério de aceite:** teste acima passa; `grep -c "timeout-minutes" .github/workflows/build.yml` ≥ 5.
- **Risco de regressão / efeitos colaterais:** `BaseException` captura `KeyboardInterrupt` apenas no modo selftest (aceitável).
- **Depende de / Conflita com:** relacionado a P3-010 (mesma função); conflita com P3-007/P3-008/P3-014 no `build.yml`.
- **Esforço:** P

#### [P3-014] `concurrency.cancel-in-progress: true` pode cancelar a execução que publica a release
- **Severidade:** BAIXA
- **Categoria:** `build-ci`
- **Confiança:** PROVAVEL
- **Local:** `.github/workflows/build.yml:11-13`
- **Descrição:** o grupo é `pdf-hub-build-${{ github.ref }}` com cancelamento ativo em **todos** os eventos. Um novo *push* na `main` enquanto a execução de um commit com `[create-release]` ainda empacota cancela essa execução (incluindo `publish-release`); a release do marcador nunca é criada e não há aviso.
- **Evidência:**
  ```yaml
  concurrency:
    group: pdf-hub-build-${{ github.ref }}
    cancel-in-progress: true
  ```
- **Como reproduzir:** dois commits seguidos na `main`, o primeiro com `[create-release]`.
- **Causa raiz:** cancelamento incondicional.
- **Impacto:** release deixada de publicar; recurso desperdiçado ao recomeçar.
- **Correção proposta:**
  ```yaml
  concurrency:
    group: pdf-hub-build-${{ github.ref }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```
- **Testes a adicionar/alterar:** N/A.
- **Critério de aceite:** dois *pushes* consecutivos na `main` enfileiram (não cancelam) a execução anterior.
- **Risco de regressão / efeitos colaterais:** mais execuções simultâneas/enfileiradas na `main`.
- **Depende de / Conflita com:** relaciona-se a P3-008.
- **Esforço:** P

#### [P3-015] Tema escuro: texto branco sobre o botão primário abaixo de 4,5:1
- **Severidade:** BAIXA
- **Categoria:** `ui-ux`
- **Confiança:** CONFIRMADO (razões de contraste calculadas pela fórmula WCAG 2.x a partir das cores do QSS)
- **Local:** `document_tools/gui.py:1704-1826` (paleta `dark`: `PRIMARY`, `PRIMARY_HOVER`) e regra `QPushButton#primaryButton`
- **Descrição:** o texto `#FFFFFF` dos botões primários (13 px, negrito) tem razão **3,94:1** em `#5477F5` e **3,21:1** em `#6C89F6` (hover, que **clareia** o botão) — abaixo do mínimo de 4,5:1 para texto normal. No tema claro: 4,98:1 (ok). Também no tema claro: `MUTED` `#64748B` sobre `WINDOW` `#F3F6FB` = 4,39:1 (texto de status 12 px).
- **Evidência:**
  ```
  light white/PRIMARY       4.98:1      dark white/PRIMARY        3.94:1  <4.5
  light MUTED/WINDOW        4.39:1  <4.5  dark white/PRIMARY_HOVER  3.21:1  <4.5
  ```
- **Como reproduzir:** cálculo acima (script inline; fórmula WCAG).
- **Causa raiz:** cores escolhidas pelo matiz sem verificar contraste.
- **Impacto:** legibilidade reduzida do botão principal no tema escuro.
- **Correção proposta:** no tema escuro usar `"PRIMARY": "#4766F0"` (branco 4,74:1; 3,09:1 contra `PANEL`) e `"PRIMARY_HOVER": "#3F5FE0"` (branco 5,35:1); no claro, `MUTED` `#5B6B82` (≥4,5:1 sobre `#F3F6FB`; recalcular antes de aplicar).
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_palette_text_contrast_meets_wcag_aa` calculando a razão para os pares (`HEADER_TEXT/HEADER`, `#FFFFFF/PRIMARY`, `#FFFFFF/PRIMARY_HOVER`, `TEXT/WINDOW`, `MUTED/WINDOW`) nos dois temas e exigindo ≥ 4,5.
- **Critério de aceite:** o teste acima passa; `test_stylesheet_preserves_complete_palette_tokens_and_thumbnail_tiles` continua verde.
- **Risco de regressão / efeitos colaterais:** mudança visual sutil; revisar capturas (`window.grab()`).
- **Depende de / Conflita com:** precede P3-016 (mesma paleta).
- **Esforço:** P

#### [P3-016] Botões `primaryButton`/`secondaryButton` desabilitados mantêm a aparência de habilitados
- **Severidade:** BAIXA
- **Categoria:** `ui-ux`
- **Confiança:** HIPOTESE (depende da resolução de especificidade do QSS do Qt; não renderizado aqui)
- **Local:** `document_tools/gui.py:1787-1793` (regras `QPushButton:disabled`, `QPushButton#primaryButton`, `QPushButton#secondaryButton`)
- **Descrição:** `QPushButton:disabled` (especificidade de pseudo-classe) é menos específica que `QPushButton#primaryButton` (seletor de ID) e `QPushButton#secondaryButton`; como estes definem `background`/`color`, o estado desabilitado não os altera. Durante operações, `_run_task` faz `self.tabs.setEnabled(False)` e o lote desabilita botões; os botões primários continuam azuis, sem indício de desabilitação.
- **Evidência:**
  ```
  QPushButton:disabled { color: $MUTED; background: $DISABLED; }
  QPushButton#primaryButton { background: $PRIMARY; color: #FFFFFF; ... }
  ```
- **Como reproduzir:** `window = DocumentToolsWindow(); b = window.batch_run_button; b.setEnabled(False); window.grab().save("/tmp/x.png")` e comparar a cor do botão com a de um secundário habilitado.
- **Causa raiz:** ausência de regras `:disabled` específicas.
- **Impacto:** feedback visual fraco durante processamento (o botão parece clicável).
- **Correção proposta:** acrescentar ao QSS:
  ```
  QPushButton#primaryButton:disabled, QPushButton#secondaryButton:disabled {
      background: $DISABLED; color: $MUTED; border-color: $BORDER;
  }
  ```
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_stylesheet_defines_disabled_state_for_primary_buttons` — `assert "QPushButton#primaryButton:disabled" in DocumentToolsWindow._stylesheet("dark")`.
- **Critério de aceite:** teste acima passa; verificação visual por captura.
- **Risco de regressão / efeitos colaterais:** nenhum funcional.
- **Depende de / Conflita com:** depois de P3-015.
- **Esforço:** P

#### [P3-017] Scripts `.bat` com fim de linha LF e sem `.gitattributes`
- **Severidade:** BAIXA
- **Categoria:** `compatibilidade-plataforma`
- **Confiança:** PROVAVEL (o `cmd.exe` é conhecido por se comportar de forma imprevisível com `.bat` em LF, principalmente com blocos entre parênteses e rótulos; não executado no Windows)
- **Local:** `instalar-e-iniciar.bat` (todo), `executar-aplicativo.bat` (todo); ausência de `.gitattributes`
- **Descrição:** os dois arquivos estão com `LF` puro (`file` → "DOS batch file, ASCII text", sem "with CRLF line terminators"; `cat -A` sem `^M`). Não há `.gitattributes` que force CRLF para `*.bat`; o ZIP do GitHub e clones em Linux/macOS mantêm LF.
- **Evidência:**
  ```
  $ file instalar-e-iniciar.bat → DOS batch file, ASCII text
  $ cat -A executar-aplicativo.bat | head -2 → "@echo off$" "setlocal$"
  ```
- **Como reproduzir:** `grep -c $'\r' *.bat` → `0` nos dois arquivos.
- **Causa raiz:** arquivos editados/commitados fora do Windows sem normalização.
- **Impacto:** instalação/execução pode falhar de forma intermitente em Windows (primeira linha de comando lida incorretamente; blocos `if (...)` multilinha).
- **Correção proposta:** (1) criar `.gitattributes` com `*.bat text eol=crlf`; (2) converter os arquivos para CRLF e commitá-los (`sed -i 's/$/\r/' *.bat` ou `unix2dos`).
- **Testes a adicionar/alterar:** `tests/test_project_metadata.py::test_bat_files_use_crlf` — `Path(p).read_bytes().count(b"\n") == Path(p).read_bytes().count(b"\r\n")`.
- **Critério de aceite:** teste acima passa; `grep -c $'\r' *.bat` > 0.
- **Risco de regressão / efeitos colaterais:** nenhum; revalidar execução no Windows.
- **Depende de / Conflita com:** conflita com P3-018 (mesmo arquivo) — aplicar P3-017 por último ou reconverter após editar.
- **Esforço:** P

#### [P3-018] `instalar-e-iniciar.bat` aborta sem internet mesmo com `.venv` já válido
- **Severidade:** BAIXA
- **Categoria:** `compatibilidade-plataforma`
- **Confiança:** PROVAVEL (leitura do script)
- **Local:** `instalar-e-iniciar.bat:52-64`
- **Descrição:** a atualização do `pip` e o `pip install -r requirements.txt` rodam sempre, e **qualquer** falha encerra com `exit /b 1`. Sem rede, o usuário que reexecuta `instalar-e-iniciar.bat` (inclusive por seguir a mensagem "execute este instalador") não consegue iniciar o app, embora `executar-aplicativo.bat` funcionasse.
- **Evidência:**
  ```bat
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 (
      echo Falha ao atualizar o pip.
      pause
      exit /b 1
  )
  ```
- **Como reproduzir:** com `.venv` válido e sem rede, executar `instalar-e-iniciar.bat` → "Falha ao atualizar o pip." e saída com código 1.
- **Causa raiz:** falha de rede tratada como fatal mesmo quando o ambiente já está completo.
- **Impacto:** inconveniência; README já orienta usar `executar-aplicativo.bat` nas execuções seguintes.
- **Correção proposta:** tornar a atualização do `pip` não fatal e aceitar o ambiente existente quando a instalação falhar:
  ```bat
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 echo Aviso: nao foi possivel atualizar o pip; continuando.
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
      ".venv\Scripts\python.exe" -c "import PySide6, pypdf, PIL, cryptography, reportlab" >nul 2>nul
      if errorlevel 1 (
          echo Falha ao instalar as dependencias.
          echo Confira a conexao com a internet e tente novamente.
          pause
          exit /b 1
      )
      echo Sem conexao: usando as dependencias ja instaladas.
  )
  ```
- **Testes a adicionar/alterar:** N/A (script Windows) — validar manualmente com a rede desativada.
- **Critério de aceite:** sem rede e com `.venv` válido, o instalador abre o aplicativo; sem rede e sem `.venv`, termina com `exit /b 1`.
- **Risco de regressão / efeitos colaterais:** deixa de garantir as versões fixadas quando offline (aviso exibido).
- **Depende de / Conflita com:** aplicar antes de P3-017 (conversão CRLF).
- **Esforço:** P

#### [P3-019] READMEs (pt/en/es) omitem dependência do Linux, o fluxo `[create-release]` e como obter o código de saída do selftest no Windows
- **Severidade:** BAIXA
- **Categoria:** `documentacao`
- **Confiança:** PROVAVEL
- **Local:** `README.md:53,63,65-80,107-113` e os trechos equivalentes de `README.en.md` e `README.es.md` (estrutura idêntica: 113/115/115 linhas, 31 itens, 4 `##`, 3 `###`)
- **Descrição:** (a) o CI instala `libxcb-cursor0` (e outras libs xcb) para o pacote Linux (`build.yml:125`), mas nenhum README informa que o binário/Qt 6 em X11 exige `libxcb-cursor0` no sistema do usuário (o PyInstaller não empacota libs `libxcb*` do sistema); (b) os READMEs dizem que releases "são geradas a partir de tags `v*`", mas o workflow também publica a partir de commits na `main` com `[create-release]` (`build.yml:213-216`); (c) a instrução `.\dist\PDFHub.exe --selftest` em um executável `--windowed` retorna imediatamente no PowerShell sem expor o código de saída.
- **Evidência:**
  ```
  README.md:53  "releases permanentes são geradas a partir de tags `v*`."
  build.yml:216  contains(github.event.head_commit.message, '[create-release]'))
  README.md:110  .\dist\PDFHub.exe --selftest
  ```
- **Como reproduzir:** `grep -n "xcb\|create-release" README*.md` → sem resultados.
- **Causa raiz:** documentação não acompanhou o workflow.
- **Impacto:** usuários Linux podem ver "Could not load the Qt platform plugin xcb"; mantenedores não sabem do marcador.
- **Correção proposta:** adicionar nos três idiomas: nota Linux (`sudo apt install libxcb-cursor0` em distros Debian/Ubuntu; equivalente em outras); parágrafo sobre `[create-release]` e a exigência de incrementar `__version__` (ver P3-008); e o comando `$p = Start-Process -Wait -PassThru -FilePath .\dist\PDFHub.exe -ArgumentList '--selftest'; $p.ExitCode`.
- **Testes a adicionar/alterar:** opcional `tests/test_project_metadata.py::test_readmes_have_same_structure` (mesmo nº de `##`, `###`, itens e blocos de código nos três arquivos).
- **Critério de aceite:** os três READMEs mencionam `libxcb-cursor0` e `[create-release]`; teste de estrutura passa.
- **Risco de regressão / efeitos colaterais:** nenhum.
- **Depende de / Conflita com:** depende de P3-008 (texto do fluxo de release).
- **Esforço:** P

#### [P3-020] Versões fixadas duplicadas em `pyproject.toml` e `requirements.txt` sem verificação de sincronia
- **Severidade:** BAIXA
- **Categoria:** `dependencias-licencas`
- **Confiança:** PROVAVEL (risco futuro; hoje **estão sincronizados** — verificado)
- **Local:** `pyproject.toml:10-16`, `requirements.txt:2-6`, `.github/dependabot.yml`
- **Descrição:** as cinco dependências de runtime estão fixadas nos dois arquivos. Verificado: `set(pyproject.dependencies) == set(requirements.txt)` → `True`. Mas nada no CI garante isso, e o Dependabot (ecossistema `pip`) pode abrir atualizações separadas e deixar os arquivos divergentes (o CI instala de `pyproject`; o `.bat` e o README instalam de `requirements.txt`).
- **Evidência:**
  ```
  pyproject == requirements.txt: True
  ```
- **Como reproduzir:** `python - <<'EOF'` com `tomllib` (ver seção 2) ou o teste abaixo.
- **Causa raiz:** duplicação manual da lista de dependências.
- **Impacto:** o usuário do `.bat` poderia receber versões diferentes das testadas no CI.
- **Correção proposta:** teste de sincronia (ou gerar `requirements.txt` a partir do `pyproject`):
  ```python
  # tests/test_project_metadata.py
  import tomllib
  from pathlib import Path

  def test_requirements_match_pyproject() -> None:
      root = Path(__file__).resolve().parents[1]
      declared = set(tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"])
      pinned = {l.strip() for l in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")}
      assert declared == pinned
  ```
- **Testes a adicionar/alterar:** o teste acima.
- **Critério de aceite:** `pytest tests/test_project_metadata.py -q` passa; alterar um pin só em um arquivo faz o teste falhar.
- **Risco de regressão / efeitos colaterais:** nenhum.
- **Depende de / Conflita com:** nenhum (arquivo de teste novo compartilhado com P3-007/P3-017/P3-019).
- **Esforço:** P

#### [P3-021] `_same_existing_file` duplicada em `gui.py` e `pdf_ops.py`
- **Severidade:** BAIXA
- **Categoria:** `correcao-logica`
- **Confiança:** CONFIRMADO (as duas implementações são **idênticas hoje**; o risco é de divergência futura)
- **Local:** `document_tools/gui.py:88-94` e `document_tools/pdf_ops.py:68-75`
- **Descrição:** a hipótese do prompt ("divergência de comportamento") **não se confirma**: ambas fazem `first == second or (exists and exists and os.path.samefile)` com `except OSError → False`. Permanece a duplicação, que é onde a divergência nasceria (ex.: normalização de maiúsculas/minúsculas ou links no Windows corrigida só em um lado).
- **Evidência:**
  ```python
  def _same_existing_file(first: Path, second: Path) -> bool:
      if first == second:
          return True
      try:
          return first.exists() and second.exists() and os.path.samefile(first, second)
      except OSError:
          return False
  ```
- **Como reproduzir:** comparar as duas funções por AST sem docstring (`gui.py:88-94` × `pdf_ops.py:68-75`) → `True` (executado; ver seção 7).
- **Causa raiz:** cópia da função.
- **Impacto:** nenhum hoje; risco de comportamentos distintos entre a checagem da GUI e a do backend.
- **Correção proposta:** tornar pública em `pdf_ops.py` (`same_existing_file`, mantendo `_same_existing_file = same_existing_file` como alias para compatibilidade) e, em `gui.py`, remover a cópia e importar `from document_tools.pdf_ops import same_existing_file as _same_existing_file`.
- **Testes a adicionar/alterar:** `tests/test_pdf_ops.py::test_same_existing_file_detects_symlink_and_hardlink` (arquivo, link simbólico e *hard link* para o mesmo alvo → `True`; arquivos distintos → `False`; caminho inexistente → `False`).
- **Critério de aceite:** `grep -n "def _same_existing_file" document_tools/*.py` retorna no máximo uma definição; suíte verde.
- **Risco de regressão / efeitos colaterais:** `pdf_ops.py` é da Parte 1 — coordenar para não colidir com correções nessa região.
- **Depende de / Conflita com:** conflita com correções da Parte 1 em `pdf_ops.py:68-75`.
- **Esforço:** P

### Parte 4 — Abas de operação individual (GUI)
*Não analisada nesta execução (escopo: apenas a Parte 3).*

### Parte 5 — Lote, perfis, histórico, PDF→imagens e conversão de imagens
*Não analisada nesta execução (escopo: apenas a Parte 3).*

---

## 5. Achados transversais

#### [T-001] ~50 mensagens de erro do backend em PT não têm chave de tradução em EN/ES
- **Severidade:** MÉDIA
- **Categoria:** `i18n`
- **Confiança:** PROVAVEL (varredura por AST das cláusulas `raise …Error("…")` × `TRANSLATIONS`; a lista pode incluir mensagens inalcançáveis pela GUI e, para f-strings, usa casamento aproximado)
- **Local:** `document_tools/pdf_ops.py` (≈35 mensagens, ex.: l.33, 41, 87-100, 248, 273-287, 337-339, 537, 599-601, 724, 787-808, 859, 876-878, 902, 936, 1016-1022, 1151, 1185), `batch_processing.py:234,270,273,296`, `pdf_rendering.py:34,74,103`, `image_resolution.py:29`, `report_history.py:29,130`; tabelas em `gui.py` (blocos `en`/`es`)
- **Descrição:** `OperationWorker` repassa `friendly_error_message(error)` e a GUI chama `_t(message)`. Mensagens que não são chaves exatas (nem casam com os poucos `re.match` de `_t`) aparecem em português em EN/ES — por exemplo "O PDF não possui páginas.", "A pasta de destino não existe.", "Arquivo não encontrado: {…}", "O arquivo de saída não pode substituir um arquivo de origem.". O README afirma que "diálogos principais … e erros comuns" acompanham o idioma; a cobertura é parcial.
- **Evidência (saída de `repros/repro_backend_messages_i18n.py`):**
  ```
  == mensagens de backend sem tradução em 'en': 50
    document_tools/pdf_ops.py:33: 'O PDF não possui páginas.'
    document_tools/pdf_ops.py:89: 'A pasta de destino não existe.'
    document_tools/pdf_ops.py:91: 'O arquivo de saída não pode substituir um arquivo de origem.'
  == mensagens de backend sem tradução em 'es': 53
  ```
- **Como reproduzir:** na raiz do repositório, `python3 repros/repro_backend_messages_i18n.py` (usa `repros/qt_stub.py` se não houver PySide6).
- **Causa raiz:** tradução por texto exato, mantida à mão; nenhum teste verifica que toda mensagem levantada pelo backend tem chave.
- **Impacto:** usuários EN/ES recebem erros em português (diálogo e barra de status).
- **Correção proposta:** (1) acrescentar as chaves faltantes em `en` e `es` (mensagens com valores: usar modelos com `{name}`/`{path}` e tratá-los em `_t` com o mesmo padrão de `required_password`/`conflict`, l.1609-1619); (2) alternativa de longo prazo: erros do backend com código estável (ex.: `PdfHubError(code, **params)`) e tradução por código — fora do escopo mínimo; (3) incluir o teste abaixo para impedir regressão.
- **Testes a adicionar/alterar:** `tests/test_gui.py::test_backend_error_messages_have_translations` — percorrer com `ast` os arquivos de `document_tools/` (exceto `gui.py`), coletar literais PT de `raise …Error("…")` e exigir chave em `TRANSLATIONS["en"]` e `["es"]` (modelos de f-string: usar regex com `{…}` → `.+`), com *allowlist* explícita para mensagens deliberadamente internas.
- **Critério de aceite:** o teste passa; `python3 repros/repro_backend_messages_i18n.py` mostra `0` nas duas listas (ou apenas itens da *allowlist*).
- **Risco de regressão / efeitos colaterais:** alterar texto de mensagem em `pdf_ops.py` (Parte 1/2) quebra a chave — o teste acima protege; coordenar com as Partes 1, 2 e 5.
- **Depende de / Conflita com:** depende de P3-004 (normalização/paridade de chaves); conflita com P3-003/P3-005 na região de `_t`.
- **Esforço:** G

#### [T-002] Ponteiros para as Partes 4 e 5 (observados durante a leitura da Parte 3; **não** analisados a fundo, **não** contabilizados)
- `gui.py:3048-3053` (`_select_reorder_pdf`, Parte 4): após `requestInterruption()`+`wait()` do worker antigo e `_reorder_items_by_page.clear()`, sinais `thumbnail_ready` já enfileirados podem ser entregues a `_set_reorder_thumbnail` e aplicar miniaturas do PDF anterior aos itens do novo (mesmo número de página). **HIPOTESE** — verificar com dois PDFs de tamanhos diferentes e geração lenta.
- `gui.py:1860-1877` (`_add_paths`, Parte 4): deduplica por `str(path.resolve()).casefold()`; em sistemas de arquivos que diferenciam maiúsculas (Linux), `A.pdf` e `a.pdf` distintos seriam tratados como duplicados e o segundo seria ignorado em silêncio. **HIPOTESE**.
- `gui.py:3818` e `gui.py:4469` (Parte 5): mesmo defeito de `with_suffix` de **P3-002**; `gui.py:4757` (Parte 5): chave `" Falhas: {count}."` inalcançável (**P3-004**).

---

## 6. Cobertura de testes ausente (Parte 3)

| Cenário sem teste | Nome sugerido | Achado |
|---|---|---|
| Paridade e higiene das tabelas `TRANSLATIONS` (en == es, sem U+200B, sem espaço nas bordas) | `tests/test_gui.py::test_translation_tables_are_in_parity_and_clean` | P3-004 |
| Status de erro totalmente traduzido (`_operation_failed`) | `test_failed_operation_status_is_fully_translated` | P3-003 |
| Ida e volta de idioma pt→en→es→pt mantém o status | `test_status_text_follows_language_round_trip` | P3-005 |
| Extensão `.pdf` acrescentada sem trocar partes do nome | `test_choose_output_pdf_appends_extension_without_replacing_dotted_names` | P3-002 |
| Confirmação de substituição e bloqueio de destino = origem em `_choose_output_pdf` | `test_choose_output_pdf_blocks_source_and_confirms_overwrite` (monkeypatch de `QFileDialog` e `QMessageBox`) | P3-002 |
| `closeEvent` com lote pausado / operação única | `test_close_with_paused_batch_offers_cancel`, `test_close_blocks_single_running_operation` | P3-012 |
| Reentrância de `_run_task` (segunda chamada com worker ativo é ignorada) | `test_run_task_ignores_second_call_while_running` | — |
| `OperationWorker` emite `failed` para exceção e `finished` sempre | `test_operation_worker_emits_failed_and_finished` | — |
| Valores inesperados de `QSettings` (`theme="x"`, `language="xx"`, `output_file_mode="abc"`) caem em padrões seguros | `test_invalid_settings_fall_back_to_defaults` | — |
| Isolamento de `QSettings`/histórico na suíte | `test_test_suite_does_not_touch_real_user_settings` | P3-006 |
| Contraste mínimo da paleta nos dois temas; estado `:disabled` dos botões primários | `test_palette_text_contrast_meets_wcag_aa`, `test_stylesheet_defines_disabled_state_for_primary_buttons` | P3-015, P3-016 |
| `--selftest` retorna 0 e retorna ≠0 em falha, com log | `tests/test_main.py::test_selftest_returns_zero`, `test_selftest_failure_returns_nonzero_and_logs` | P3-010, P3-013 |
| Sincronia `pyproject` × `requirements.txt`; `.bat` em CRLF; READMEs com a mesma estrutura; actions fixadas por SHA | `tests/test_project_metadata.py::{test_requirements_match_pyproject,test_bat_files_use_crlf,test_readmes_have_same_structure,test_workflow_actions_are_pinned_to_sha}` | P3-020, P3-017, P3-019, P3-007 |
| Mensagens de backend com tradução | `test_backend_error_messages_have_translations` | T-001 |

---

## 7. Falsos positivos e itens verificados sem problema (Parte 3)

**Hipóteses do prompt confirmadas/descartadas**
- **`_same_existing_file` duplicada → divergência de comportamento:** **descartada como divergência** (AST das duas funções, sem docstring, é idêntica: `gui.py:88-94` × `pdf_ops.py:68-75`; saída `idênticas: True`). Permanece só a duplicação (P3-021).
- **Encerramento de threads (`closeEvent`):** `OperationWorker` é mantido em `self._worker`; `_operation_finished` faz `wait()` + `deleteLater()` e zera a referência; os sinais `succeeded/failed/finished` são entregues em fila ao `QMainWindow` (thread GUI); `closeEvent` veta o fechamento durante operação e, para o worker de miniaturas, faz `requestInterruption()`+`wait()`+`deleteLater()` — sem risco encontrado de `QThread` destruída em execução ou de sinal a widget destruído **no fluxo normal**. Ressalva única: P3-012.
- **Reentrância de `_run_task`:** protegida por `self._worker is not None and self._worker.isRunning()` e por `self.tabs.setEnabled(False)`; o retorno é silencioso (aceitável).
- **Exceções que escapam de `run()`:** `except Exception` não pega `BaseException` (`SystemExit`/`KeyboardInterrupt`); mesmo assim `finished` é emitido e a UI se recupera. `MemoryError`/`RecursionError`/`OSError` são `Exception` (cobertos). Falha de `emit` improvável. Sem achado.
- **`pyproject.toml`:** `license = "AGPL-3.0-only"` (SPDX/PEP 639) coerente com `setuptools>=77` em `build-system` e com o texto AGPL v3 do `LICENSE` (661 linhas); nome `pdf-hub` × diretório `img-to-pdf-portable` sem impacto (não publicado no PyPI; *entry point* `document_tools.gui:main` retorna `int`); `requirements.txt` **sincronizado** com `pyproject.toml` (verificado: `True`).
- **README — alegações:** "os arquivos originais não são substituídos": a GUI bloqueia destino = origem em `_choose_output_pdf` (com `resolve()` + `samefile`) — verdadeiro para os diálogos de saída de PDF (ressalva P3-002 sobre nome alterado); "a janela não fecha enquanto uma operação está ativa": confere com `closeEvent`; "senhas não são salvas nas preferências": as únicas chaves de `QSettings` em `gui.py` são `theme`, `language`, `output_file_mode` e `pipeline_profiles` (l.1422, 1521, 1652, 2067/2099, 2143, 3586-3637) — **nenhuma senha** nas chaves da Parte 3 (perfis, relatórios e checkpoint: Parte 5). "Cancelamento seguro", "nunca substitui", marcadores/anotações: **não avaliados** (Partes 1/5).
- **READMEs pt/en/es:** estrutura idêntica (113/115/115 linhas, 31 itens, 4 `##`, 3 `###`, 10 blocos de código) e conjunto idêntico de símbolos de código/versões/faixas (72–600 DPI, `v0.11.0`, comandos) → **sem divergência material** entre idiomas nas afirmações comparadas.
- **Workflow:** `permissions` mínimas (`contents: read` global; `contents: write` só em `publish-release`); `needs` corretos (`package-*` dependem de `test`; `publish-release` de todos); `ubuntu-latest` (testes) × `ubuntu-22.04` (pacote Linux) é escolha deliberada de base glibc; `download-artifact` sem `name` baixa em subpastas e os globs `release-assets/<artefato>/*` são coerentes; `--onefile` (Windows/Linux) × `--onedir --windowed` (macOS) coerente com o executável usado no smoke test (`PDF Hub.app/Contents/MacOS/PDF Hub`); `.spec` ignorado é coerente com build apenas por CLI; checksums SHA-256 gerados para cada pacote; `python -c … __version__` do passo de release não importa PySide6 (`document_tools/__init__.py` tem 3 linhas); YAML parseia (5 jobs: test, package-windows, package-linux, package-macos, publish-release). Ausência de assinatura/notarização: **apenas registrada** (README já avisa).
- **Estilo/QSS:** todos os tokens `$X` resolvem nos dois temas (0 não resolvidos); `#intro` sem `setObjectName` e `progress` sem regra são inofensivos; thumbnails forçados em fundo claro no tema escuro são intencionais (existe teste); 0 imports não usados em `gui.py`.
- **`QSettings`:** `QSettings("PDFHub","PDF Hub")` coincide com `setOrganizationName("PDFHub")`/`setApplicationName("PDF Hub")` em `main()` (l.4765-4768) → `AppDataLocation` consistente; `theme`, `language` e `output_file_mode` têm validação/valores padrão (l.1422-1423, 1521-1523, 2096-2102, `_apply_language` l.1656); a hipótese "bool vindo como `\"true\"`" não se aplica (nenhuma chave booleana na Parte 3).
- **`_capture_ui_texts`:** o combo de histórico de lote está vazio no momento da captura (preenchido depois por `_load_batch_history`), logo `_apply_language` **não** sobrescreve seus itens dinâmicos.
- **Desempenho de `_t`:** 1000 chamadas com texto não mapeado = 0,066 s (reconstrói dois dicionários reversos a cada chamada) — irrelevante na prática; o ajuste está embutido em P3-005.
- **Colisões de tradução:** textos PT distintos com a mesma tradução (ex.: "Rodapé central"/"Rodapé centralizado" → "Pie centrado"; "Remover selecionadas/selecionados") são intencionais e só importam na busca reversa, usada apenas para texto de status; sem significado distinto conflitante encontrado. Chaves duplicadas no literal do dicionário (10 em `en`, 4 em `es`) têm **valores idênticos** (apenas ruído).
- **`.bat`:** `cd /d "%~dp0"` com aspas trata caminhos com espaços/acentos; verificação de Python ≥3.11 e `.venv` incompleta/movida têm mensagens e `exit /b 1`; falhas de `pip` tratadas (ressalva P3-018). `cd /d` não funciona em caminho UNC (compartilhamento de rede) — situação marginal, não registrada como achado.
- **Fora de escopo / não verificável aqui:** existência e compatibilidade das versões `actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`, `softprops/action-gh-release@v2`; existência das versões fixadas (PySide6 6.12.0, pypdf 6.21.2, cryptography 50.0.2, Pillow 13.0.0, reportlab 5.1.0, pytest 9.1.1, PyInstaller 6.22.3, pip-audit 2.10.1) e a disponibilidade de *wheels* para Python 3.14 (item da matriz); se `python` existe no runner do passo "Read application version" (P3-008 já usa `python3`); resultado real de `pip-audit`; baseline da suíte (164 ok / 1 falha) e qualquer comportamento dependente de Qt real. **Verificar com:** `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, `pip index versions <pacote>`, `pip install -e ".[dev]"` em cada versão do Python da matriz.

---

## 8. Melhorias opcionais
1. Aplicar `settings.sync()` + checar `settings.status()` após gravar `language/theme/output_file_mode` e avisar em caso de falha (pasta de configuração somente leitura).
2. Trocar `cd /d "%~dp0"` por `pushd "%~dp0"` nos `.bat` para suportar execução a partir de caminho UNC.
3. Mover `TRANSLATIONS` para módulo próprio (`document_tools/i18n.py`) ou JSON, com os dicionários reversos pré-calculados.
4. Remover as 14 chaves duplicadas dos literais de `TRANSLATIONS` (valores idênticos).
5. Remover `QPixmap`/ícone sem `devicePixelRatio` em favor de `QIcon` com tamanhos adicionais (ícones nítidos em alto DPI).
6. Adicionar `pip-audit` também aos jobs de pacote (hoje só na matriz 3.13 do job `test`).
7. Publicar SBOM (ex.: CycloneDX) junto da release.

---

## 9. Checklist final de verificação pós-correção

| # | Comando | Resultado esperado |
|---|---|---|
| 1 | `python -m compileall -q .` | sem saída, código 0 |
| 2 | `QT_QPA_PLATFORM=offscreen python -m pytest -q` | 0 falhas (inclui `test_window_preserves_space_for_controls_and_aligned_file_pickers`) |
| 3 | `QT_QPA_PLATFORM=offscreen python main.py --selftest; echo $?` | `0` |
| 4 | `python3 repros/repro_i18n_coverage.py` | "chaves com caractere invisível: []" |
| 5 | `python3 repros/repro_t_behaviour.py` | itens 1b, 2 e 5 já corretos (status em PT; erro totalmente traduzido; `relatorio 28.10.2026.pdf`) |
| 6 | `python3 repros/repro_backend_messages_i18n.py` | 0 mensagens sem tradução (ou só *allowlist*) |
| 7 | `grep -nE "uses: .+@v[0-9]" .github/workflows/build.yml` | sem resultados |
| 8 | `grep -c "timeout-minutes" .github/workflows/build.yml` | ≥ 5 |
| 9 | `python -c "import yaml;yaml.safe_load(open('.github/workflows/build.yml'))"` | sem erro |
| 10 | `file *.bat` / `grep -c $'\r' *.bat` | "with CRLF line terminators" / contagem > 0 |
| 11 | `python -m pip_audit --local` | sem vulnerabilidades conhecidas |
| 12 | macOS: `codesign --verify --deep --strict --verbose=2 "dist/PDF Hub.app"` | código 0 |
| 13 | Release de teste: tag `v<__version__ + 1>` sem alterar `__version__` | job `publish-release` falha com mensagem clara |

*Fim do relatório da Parte 3 (3ª de 5). Partes 1, 2, 4 e 5 permanecem não analisadas.*
