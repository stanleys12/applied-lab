#!/usr/bin/env python3
"""minisast: a small static-analysis scanner for common Python security smells.

Educational/defensive tool: flags patterns worth a human's attention
(hardcoded secrets, eval/exec, shell=True, weak hashes, string-built SQL).
It does not exploit anything and ships no working payloads.
"""
import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SECRET_NAME_RE = re.compile(r"(password|passwd|secret|api_key|apikey|token|access_key)", re.I)
SECRET_ASSIGN_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["']([^"']+)["']\s*(#.*)?$"""
)
PLACEHOLDER_RE = re.compile(r"^(changeme|xxx+|todo|<.*>|\$\{.*\}|)$", re.I)

WEAK_HASHES = {"md5", "sha1"}
SHELL_FUNCS = {"call", "run", "Popen", "check_call", "check_output"}
SQL_METHODS = {"execute", "executemany"}


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    severity: str
    message: str


def scan_source_lines(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for i, line in enumerate(lines, start=1):
        m = SECRET_ASSIGN_RE.match(line)
        if m and SECRET_NAME_RE.search(m.group(1)) and not PLACEHOLDER_RE.match(m.group(2)):
            findings.append(Finding(path, i, "hardcoded-secret", "HIGH",
                f"possible hardcoded credential in '{m.group(1)}'"))
    return findings


def _is_sql_unsafe_arg(node: ast.expr) -> bool:
    if isinstance(node, ast.JoinedStr):  # f-string
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    return False


class AstChecks(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.findings: list[Finding] = []

    def visit_Call(self, node: ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)

        if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
            self.findings.append(Finding(self.path, node.lineno, "eval-exec",
                "HIGH", f"use of {func.id}() can execute arbitrary code"))

        if name in SHELL_FUNCS:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append(Finding(self.path, node.lineno, "shell-injection",
                        "HIGH", f"subprocess.{name}(shell=True) risks command injection"))

        if name in WEAK_HASHES and isinstance(func, ast.Attribute):
            self.findings.append(Finding(self.path, node.lineno, "weak-hash",
                "LOW", f"hashlib.{name}() is not collision-resistant; avoid for security use"))

        if name in SQL_METHODS and node.args and _is_sql_unsafe_arg(node.args[0]):
            self.findings.append(Finding(self.path, node.lineno, "sql-injection",
                "HIGH", f"{name}() built from string interpolation; use parameterized queries"))

        self.generic_visit(node)


def scan_file(path: Path) -> list[Finding]:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    findings = scan_source_lines(str(path), lines)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        return findings + [Finding(str(path), e.lineno or 0, "parse-error", "INFO", str(e))]
    checker = AstChecks(str(path))
    checker.visit(tree)
    return findings + checker.findings


def scan_path(target: Path) -> list[Finding]:
    files = [target] if target.is_file() else sorted(target.rglob("*.py"))
    findings = []
    for f in files:
        findings.extend(scan_file(f))
    return sorted(findings, key=lambda f: (f.path, f.line))


def main():
    parser = argparse.ArgumentParser(description="minisast: tiny Python security scanner")
    parser.add_argument("target", help="file or directory to scan")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2

    findings = scan_path(target)
    for f in findings:
        print(f"[{f.severity:4}] {f.path}:{f.line}  {f.rule}: {f.message}")

    high = sum(1 for f in findings if f.severity == "HIGH")
    print(f"\n{len(findings)} finding(s), {high} high severity")
    return 1 if high else 0


if __name__ == "__main__":
    sys.exit(main())
