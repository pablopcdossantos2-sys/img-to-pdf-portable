# Licenças de terceiros

A aplicação deste repositório está coberta pela GNU AGPL v3, conforme o arquivo `LICENSE`.

As dependências diretas listadas em `requirements.txt` têm termos próprios. Antes de redistribuir o aplicativo empacotado, preserve os avisos de licença exigidos e confira as versões efetivamente incluídas no executável:

- **PySide6 / Qt for Python** — distribuição sob LGPL-3.0, GPL-2.0 ou GPL-3.0, conforme a opção aplicável. O empacotamento inclui bibliotecas Qt; a redistribuição deve respeitar os avisos e as condições de LGPL/GPL pertinentes.
- **pypdf** — BSD-3-Clause.
- **cryptography** — Apache-2.0 OR BSD-3-Clause.
- **Pillow** — MIT-CMU.
- **ReportLab** — BSD License (BSD-3-Clause-style license terms; consult the version-specific license notice distributed with ReportLab).

As ferramentas de desenvolvimento usadas para os testes, auditoria e empacotamento também têm suas próprias licenças, entre elas pytest (MIT), pip-audit (Apache-2.0) e PyInstaller (GPL com exceção de bootloader). Consulte a documentação oficial e os avisos incluídos nas distribuições para determinar as obrigações exatas de cada release.

Referências:
- https://pypi.org/project/PySide6/
- https://doc.qt.io/qtforpython-6/licenses.html
- https://pypi.org/project/pypdf/
- https://pypi.org/project/pillow/
- https://pypi.org/project/reportlab/
- https://pypi.org/project/pyinstaller/
