from __future__ import annotations

import json

from pdf_epub_reader.services.plotly_sandbox import runner


class TestPlotlySandboxRunner:
    def test_collect_static_violations_allows_supported_imports(self) -> None:
        tree = runner.ast.parse(
            "import plotly.graph_objects as go\nimport math\nfrom numpy import array\n",
            filename="<llm>",
        )

        violations = runner.collect_static_violations(tree)

        assert violations == []

    def test_collect_static_violations_reports_multiple_policy_errors(self) -> None:
        tree = runner.ast.parse(
            "import os\n"
            'eval("1 + 1")\n'
            "().__class__.__mro__\n",
            filename="<llm>",
        )

        violations = runner.collect_static_violations(tree)

        assert [(v.node_type, v.name, v.lineno) for v in violations] == [
            ("Import", "os", 1),
            ("Call", "eval", 2),
            ("Attribute", "__mro__", 3),
            ("Attribute", "__class__", 3),
        ]

    def test_main_returns_exit_code_3_and_writes_json_lines_for_static_violations(
        self,
        tmp_path,
        capsys,
    ) -> None:
        code_path = tmp_path / "script.py"
        code_path.write_text("import os\n", encoding="utf-8")

        exit_code = runner.main(["--code-path", str(code_path)])

        assert exit_code == 3
        stderr_lines = capsys.readouterr().err.strip().splitlines()
        assert len(stderr_lines) == 1
        payload = json.loads(stderr_lines[0])
        assert payload == {"node_type": "Import", "name": "os", "lineno": 1}

    def test_execute_code_blocks_disallowed_dynamic_import_when_static_checks_are_skipped(
        self,
        capsys,
    ) -> None:
        exit_code = runner.execute_code(
            "__import__('os')\n",
            enforce_static_checks=False,
        )

        assert exit_code == 2
        assert "is not allowed in sandbox" in capsys.readouterr().err