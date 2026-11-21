"""Local CSV handoff checks. Never changes input or exports its cell values.

The report shows only counts, source hashes, and record/column coordinates.
Formula detection is conservative triage, not a guarantee for all spreadsheet apps.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import unicodedata
from tablib_runtime import tablib, FormattedHTML

MAX_BYTES = 5_000_000
MAX_ROWS = 10_000
MAX_ISSUES = 200


def validate_schema(schema):
    if set(schema) != {"headers", "key", "required", "encoding"}:
        raise ValueError("SCHEMA_FIELDS")
    headers = schema["headers"]
    if (not isinstance(headers, list) or not 1 <= len(headers) <= 100 or
        any(not isinstance(h, str) or not h.strip() for h in headers) or
        len(set(headers)) != len(headers)):
        raise ValueError("SCHEMA_HEADERS")
    if schema["key"] not in headers or not isinstance(schema["required"], list):
        raise ValueError("SCHEMA_KEY_OR_REQUIRED")
    if any(h not in headers for h in schema["required"]):
        raise ValueError("SCHEMA_REQUIRED_COLUMN")
    if schema["encoding"] not in ("utf-8-sig", "cp932"):
        raise ValueError("ENCODING_NOT_SUPPORTED")
    return schema


def formula_like(cell):
    # Japanese full-width formula prefixes and leading whitespace merit review.
    normalized = unicodedata.normalize("NFKC", cell)
    return (cell.startswith(("\t", "\r", "\n")) or
            normalized.lstrip().startswith(("=", "+", "-", "@")))


def check(raw, schema):
    validate_schema(schema)
    result = {"source_sha256": hashlib.sha256(raw).hexdigest(), "status": "PASS",
              "records": 0, "issues": [], "issues_truncated": False}
    def issue(code, record=0, column=0):
        result["status"] = "REVIEW_REQUIRED"
        if len(result["issues"]) < MAX_ISSUES:
            result["issues"].append({"code": code, "record": record, "column": column})
        else:
            result["issues_truncated"] = True
    if len(raw) > MAX_BYTES:
        issue("SIZE_LIMIT")
        return result
    try:
        text = raw.decode(schema["encoding"], errors="strict")
    except UnicodeError:
        issue("DECODE_ERROR")
        return result
    try:
        rows = csv.reader(io.StringIO(text, newline=""), strict=True)
        headers = next(rows, None)
        if not headers:
            issue("EMPTY_INPUT")
            return result
        if headers != schema["headers"]:
            issue("HEADER_MISMATCH")
            return result
        if any(formula_like(h) for h in headers):
            issue("FORMULA_LIKE_HEADER", 1)
        required = [headers.index(h) for h in schema["required"]]
        key = headers.index(schema["key"])
        seen = set()
        validated = tablib.Dataset(headers=headers)
        for record, row in enumerate(rows, start=2):
            if result["records"] >= MAX_ROWS:
                issue("ROW_LIMIT", record)
                break
            result["records"] += 1
            if len(row) != len(headers):
                issue("COLUMN_COUNT", record)
                continue
            validated.append(row)
            if not row[key].strip():
                issue("EMPTY_KEY", record, key + 1)
            elif row[key] in seen:
                issue("DUPLICATE_KEY", record, key + 1)
            seen.add(row[key])
            for col in required:
                if not row[col].strip():
                    issue("REQUIRED_EMPTY", record, col + 1)
            for col, cell in enumerate(row, start=1):
                if formula_like(cell):
                    issue("FORMULA_LIKE_CELL", record, col)
        if result["records"] == 0:
            issue("NO_DATA_ROWS")
        # Tablib retains validated rectangular records; only aggregate data leaves this function.
        result["rectangular_records"] = len(validated)
    except csv.Error:
        issue("MALFORMED_CSV")
    return result


def render_report(report):
    data = tablib.Dataset(headers=["ファイル番号", "状態", "行数", "指摘数"])
    for i, entry in enumerate(report["files"], start=1):
        data.append([i, entry["status"], entry["records"], len(entry["issues"])])
    table = FormattedHTML.export_set(data)
    return ('<!doctype html><html lang="ja"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>CSV納品前チェック</title><style>body{font:16px system-ui;max-width:900px;'
            'margin:40px auto;padding:20px;color:#172b36}table{border-collapse:collapse;width:100%}'
            'th,td{padding:12px;border-bottom:1px solid #ccd8df;text-align:left}</style>'
            '<h1>CSV納品前チェック</h1><p>入力の値は表示しません。指摘の位置は同梱JSONを参照。'
            'PASSは指定した検査の通過であり、業務上の正しさや全表計算ソフトの安全性を保証しません。</p>'
            + table + '</html>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New, non-existing report directory")
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args(argv)
    if not 1 <= len(args.files) <= 20:
        raise ValueError("FILE_COUNT")
    if args.output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    schema = validate_schema(json.loads(args.schema.read_text(encoding="utf-8-sig")))
    checks = []
    for path in args.files:
        if not path.is_file():
            raise ValueError("REGULAR_INPUT_FILE_REQUIRED")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            checks.append({"source_sha256": None, "status": "REVIEW_REQUIRED", "records": 0,
                           "issues": [{"code": "SIZE_LIMIT", "record": 0, "column": 0}],
                           "issues_truncated": False})
        else:
            checks.append(check(raw, schema))
    report = {"schema_version": 1, "files": checks,
              "schema_sha256": hashlib.sha256(args.schema.read_bytes()).hexdigest(),
              "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "REVIEW_REQUIRED",
              "input_values_in_report": False, "input_modified": False}
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    with (args.output / "report.html").open("x", encoding="utf-8") as stream:
        stream.write(render_report(report))
    print(json.dumps({"status": report["status"], "report_directory": str(args.output.resolve())}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
