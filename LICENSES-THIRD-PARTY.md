# Licenças de terceiros

> PDF Hub source repository: https://github.com/pablopcdossantos2-sys/img-to-pdf-portable
>
> The portable packages include this notice and the project AGPL-3.0 license. This summary is informational and does not replace the complete license texts or a review of each dependency's redistribution conditions.


A aplicação deste repositório está coberta pela GNU AGPL v3, conforme o arquivo `LICENSE`.

As dependências diretas listadas em `requirements.txt` têm termos próprios. Antes de redistribuir o aplicativo empacotado, preserve os avisos de licença exigidos e confira as versões efetivamente incluídas no executável:

- **PySide6 / Qt for Python** — distribuição sob LGPL-3.0, GPL-2.0 ou GPL-3.0, conforme a opção aplicável. O empacotamento inclui bibliotecas Qt; a redistribuição deve respeitar os avisos e as condições de LGPL/GPL pertinentes.
- **pypdf** — BSD-3-Clause.
- **cryptography** — Apache-2.0 OR BSD-3-Clause.
- **Pillow** — MIT-CMU.
- **ReportLab** — BSD License. Preserve and consult the `license.txt` notice distributed with the exact version being packaged.

As ferramentas de desenvolvimento usadas para os testes, auditoria e empacotamento também têm suas próprias licenças, entre elas pytest (MIT), pip-audit (Apache-2.0) e PyInstaller (GPL com exceção de bootloader). Consulte a documentação oficial e os avisos incluídos nas distribuições para determinar as obrigações exatas de cada release.

Referências:
- https://pypi.org/project/PySide6/
- https://doc.qt.io/qtforpython-6/licenses.html
- https://pypi.org/project/pypdf/
- https://pypi.org/project/pillow/
- https://pypi.org/project/reportlab/
- https://pypi.org/project/pyinstaller/


## Distributed notice file

Windows, Linux and macOS packages also include THIRD-PARTY-NOTICES.txt, generated from license files present in the installed runtime distributions. Keep it alongside the binary when redistributing a package. This generated file supplements this index; review obligations for the exact Qt and other third-party components included in each build.
