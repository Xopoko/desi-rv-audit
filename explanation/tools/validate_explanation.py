#!/usr/bin/env python3
"""Validate the integrity and coverage of the repository explanation layer."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPLANATION_DIR = REPO_ROOT / "explanation"
MANIFEST_PATH = EXPLANATION_DIR / "manifest.json"
SOURCES_PATH = EXPLANATION_DIR / "sources.json"
CLAIMS_PATH = EXPLANATION_DIR / "claims.jsonl"

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
GENERATOR_STAMP_RE = re.compile(r"^[^+\s]+\+sha256\.([0-9a-fA-F]{12})$")
FENCED_CODE_RE = re.compile(
    r"(?ms)^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=fence)[ \t]*$"
)
INLINE_CODE_RE = re.compile(r"(?s)(?P<ticks>`+).*?(?P=ticks)")
HTML_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")
INLINE_LINK_RE = re.compile(
    r"!?\[[^\]\n]*\]\(\s*"
    r"(?P<target><[^>\n]*>|(?:\\.|[^()\s]|\([^()\n]*\))+?)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?P<target><[^>\n]+>|\S+)"
)
MARKDOWN_HEADING_RE = re.compile(
    r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(?P<label>.+?)[ \t]*#*[ \t]*$"
)
EXPLICIT_ANCHOR_RE = re.compile(
    r"(?i)<(?:a|[a-z][a-z0-9-]*)\s+[^>]*(?:id|name)=[\"'](?P<id>[^\"']+)[\"']"
)


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"{label}: missing file {path.relative_to(REPO_ROOT).as_posix()}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot parse JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label}: top-level value must be an object")
        return {}
    return payload


def _load_claims(errors: list[str]) -> list[tuple[int, dict[str, Any]]]:
    if not CLAIMS_PATH.is_file():
        errors.append("claims: missing file explanation/claims.jsonl")
        return []

    records: list[tuple[int, dict[str, Any]]] = []
    try:
        lines = CLAIMS_PATH.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(f"claims: cannot read JSONL: {exc}")
        return []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"claims.jsonl:{line_number}: cannot parse JSON: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"claims.jsonl:{line_number}: record must be an object")
            continue
        records.append((line_number, record))
    return records


def _records(
    payload: dict[str, Any], key: str, context: str, errors: list[str]
) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{context}.{key}: must be a list")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{context}.{key}[{index}]: must be an object")
            continue
        records.append(item)
    return records


def _register_id(
    record: dict[str, Any],
    context: str,
    seen: dict[str, str],
    errors: list[str],
) -> str | None:
    identifier = record.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        errors.append(f"{context}.id: must be a nonempty string")
        return None
    identifier = identifier.strip()
    if identifier in seen:
        errors.append(
            f"{context}.id: duplicate {identifier!r}; first declared at {seen[identifier]}"
        )
        return None
    seen[identifier] = context
    return identifier


def _string_list(
    value: Any,
    context: str,
    errors: list[str],
    *,
    require_nonempty: bool = False,
    unique: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{context}: must be a list")
        return []
    if require_nonempty and not value:
        errors.append(f"{context}: must not be empty")

    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{context}[{index}]: must be a nonempty string")
            continue
        item = item.strip()
        if unique and item in seen:
            errors.append(f"{context}[{index}]: duplicate value {item!r}")
            continue
        seen.add(item)
        result.append(item)
    return result


def _repo_path(raw_path: Any, context: str, errors: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{context}: must be a nonempty repository-relative path")
        return None

    raw_path = raw_path.strip()
    posix_path = PurePosixPath(raw_path.replace("\\", "/"))
    windows_path = PureWindowsPath(raw_path)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        errors.append(f"{context}: path must be repository-relative: {raw_path!r}")
        return None

    candidate = (REPO_ROOT / Path(*posix_path.parts)).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        errors.append(f"{context}: path escapes the repository: {raw_path!r}")
        return None
    return candidate


def _require_file(raw_path: Any, context: str, errors: list[str]) -> Path | None:
    path = _repo_path(raw_path, context, errors)
    if path is not None and not path.is_file():
        errors.append(f"{context}: file does not exist: {raw_path!r}")
        return None
    return path


def _parse_frontmatter(
    path: Path, context: str, errors: list[str]
) -> tuple[str, dict[str, Any] | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{context}: cannot read Markdown: {exc}")
        return "", None

    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"{context}: missing YAML frontmatter")
        return text, None

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        errors.append(f"{context}: YAML frontmatter is not closed")
        return text, None

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError as exc:
        errors.append(f"{context}: cannot parse YAML frontmatter: {exc}")
        return text, None
    if not isinstance(frontmatter, dict):
        errors.append(f"{context}: YAML frontmatter must be a mapping")
        return text, None
    return text, frontmatter


def _markdown_without_code(text: str) -> str:
    text = HTML_COMMENT_RE.sub("", text)
    text = FENCED_CODE_RE.sub("", text)
    return INLINE_CODE_RE.sub("", text)


def _clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    return re.sub(r"\\([\\() ])", r"\1", target)


def _github_heading_slug(label: str) -> str:
    label = html.unescape(label)
    label = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", label)
    label = re.sub(r"<[^>]+>", "", label)
    label = label.replace("`", "").replace("*", "").replace("~", "")
    kept = []
    for character in label.lower().strip():
        category = unicodedata.category(character)
        if character.isalnum() or character.isspace() or character in {"-", "_"}:
            kept.append(character)
        elif not category.startswith(("P", "S")):
            kept.append(character)
    return re.sub(r"\s+", "-", "".join(kept)).strip("-")


def _markdown_anchors_from_text(text: str) -> frozenset[str]:
    searchable = HTML_COMMENT_RE.sub("", FENCED_CODE_RE.sub("", text))
    anchors: set[str] = {
        html.unescape(match.group("id")).strip().lower()
        for match in EXPLICIT_ANCHOR_RE.finditer(searchable)
    }
    counts: dict[str, int] = {}
    for match in MARKDOWN_HEADING_RE.finditer(searchable):
        base = _github_heading_slug(match.group("label"))
        if not base:
            continue
        duplicate_index = counts.get(base, 0)
        counts[base] = duplicate_index + 1
        anchors.add(base if duplicate_index == 0 else f"{base}-{duplicate_index}")
    return frozenset(anchors)


@lru_cache(maxsize=None)
def _markdown_anchors(path: Path) -> frozenset[str]:
    return _markdown_anchors_from_text(path.read_text(encoding="utf-8"))


def _validate_link_target(
    raw_target: str,
    *,
    base_dir: Path,
    same_document_anchors: frozenset[str],
    context: str,
    errors: list[str],
) -> bool:
    target = _clean_link_target(raw_target)
    split = urlsplit(target)
    if split.scheme or target.startswith("//"):
        return False

    path_part = unquote(split.path)
    if not path_part:
        if split.fragment:
            fragment = unquote(split.fragment).strip().lower()
            if fragment not in same_document_anchors:
                errors.append(
                    f"{context}: unresolved same-document link fragment: {target!r}"
                )
            return True
        return False

    if path_part.startswith("/"):
        candidate = (REPO_ROOT / path_part.lstrip("/")).resolve()
    else:
        candidate = (base_dir / Path(*PurePosixPath(path_part.replace("\\", "/")).parts)).resolve()

    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        errors.append(f"{context}: internal link escapes the repository: {target!r}")
        return True
    if not candidate.exists():
        errors.append(f"{context}: unresolved internal link: {target!r}")
    elif split.fragment and candidate.is_file() and candidate.suffix.lower() == ".md":
        fragment = unquote(split.fragment).strip().lower()
        try:
            anchors = _markdown_anchors(candidate)
        except (OSError, UnicodeError) as exc:
            errors.append(f"{context}: cannot inspect link fragment {target!r}: {exc}")
        else:
            if fragment not in anchors:
                errors.append(f"{context}: unresolved internal link fragment: {target!r}")
    return True


def _validate_markdown_links(
    text: str,
    *,
    base_dir: Path,
    context: str,
    errors: list[str],
) -> int:
    searchable = _markdown_without_code(text)
    same_document_anchors = _markdown_anchors_from_text(text)
    targets = [match.group("target") for match in INLINE_LINK_RE.finditer(searchable)]
    targets.extend(
        match.group("target") for match in REFERENCE_DEFINITION_RE.finditer(searchable)
    )
    checked = 0
    for target in targets:
        checked += int(
            _validate_link_target(
                target,
                base_dir=base_dir,
                same_document_anchors=same_document_anchors,
                context=context,
                errors=errors,
            )
        )
    return checked


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sources(
    sources_payload: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    source_records = _records(sources_payload, "sources", "sources.json", errors)
    seen: dict[str, str] = {}
    sources: dict[str, dict[str, Any]] = {}

    for index, record in enumerate(source_records):
        context = f"sources.json.sources[{index}]"
        source_id = _register_id(record, context, seen, errors)
        if source_id is not None:
            sources[source_id] = record

        for field in ("title", "type", "stable_id", "role"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{context}.{field}: must be a nonempty string")

        url = record.get("url")
        if not isinstance(url, str) or not url.strip():
            errors.append(f"{context}.url: must be a nonempty HTTP(S) URL")
        else:
            parsed = urlsplit(url.strip())
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{context}.url: must be an HTTP(S) URL: {url!r}")

        checked_at = record.get("checked_at")
        if not isinstance(checked_at, str) or not checked_at.strip():
            errors.append(f"{context}.checked_at: must be a nonempty ISO date or datetime")
        else:
            try:
                datetime.fromisoformat(checked_at.strip().replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    f"{context}.checked_at: must be an ISO date or datetime: {checked_at!r}"
                )
    return sources


def _validate_claims(
    claim_records: list[tuple[int, dict[str, Any]]],
    sources: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    seen: dict[str, str] = {}
    claims: dict[str, dict[str, Any]] = {}
    contexts: list[tuple[str, dict[str, Any], str | None]] = []

    for line_number, record in claim_records:
        context = f"claims.jsonl:{line_number}"
        claim_id = _register_id(record, context, seen, errors)
        if claim_id is not None:
            claims[claim_id] = record
        contexts.append((context, record, claim_id))

    for context, record, _claim_id in contexts:
        for field in ("kind", "status"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{context}.{field}: must be a nonempty string")

        statement = record.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            errors.append(f"{context}.statement: must be a nonempty string")

        limitations = _string_list(
            record.get("limitations"),
            f"{context}.limitations",
            errors,
            require_nonempty=True,
        )
        if limitations and not any(item.strip() for item in limitations):
            errors.append(f"{context}.limitations: must contain a nonempty limitation")

        source_ids = _string_list(
            record.get("source_ids"), f"{context}.source_ids", errors, unique=True
        )
        evidence = _string_list(
            record.get("evidence"), f"{context}.evidence", errors, unique=True
        )
        explained_in = _string_list(
            record.get("explained_in"),
            f"{context}.explained_in",
            errors,
            require_nonempty=True,
            unique=True,
        )

        if not source_ids and not evidence:
            errors.append(f"{context}: claim must cite at least one source or evidence file")
        for source_id in source_ids:
            if source_id not in sources:
                errors.append(f"{context}.source_ids: unknown source ID {source_id!r}")
        for index, raw_path in enumerate(evidence):
            _require_file(raw_path, f"{context}.evidence[{index}]", errors)
        for index, raw_path in enumerate(explained_in):
            _require_file(raw_path, f"{context}.explained_in[{index}]", errors)
    return claims


def _validate_notebook(
    path: Path,
    *,
    context: str,
    generator_path: Path | None,
    required_claims: list[str],
    claims: dict[str, dict[str, Any]],
    errors: list[str],
) -> int:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{context}: cannot parse notebook JSON: {exc}")
        return 0
    if not isinstance(notebook, dict):
        errors.append(f"{context}: notebook must be a JSON object")
        return 0

    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{context}.metadata: must be an object")
        metadata = {}
    explanation = metadata.get("explanation")
    if not isinstance(explanation, dict):
        errors.append(f"{context}.metadata.explanation: must be an object")
        explanation = {}

    required_metadata_keys = {"generator_version", "inputs", "claims", "executed"}
    missing_keys = sorted(required_metadata_keys - set(explanation))
    extra_keys = sorted(set(explanation) - required_metadata_keys)
    if missing_keys:
        errors.append(
            f"{context}.metadata.explanation: missing keys {', '.join(missing_keys)}"
        )
    if extra_keys:
        errors.append(
            f"{context}.metadata.explanation: unsupported keys {', '.join(extra_keys)}"
        )

    generator_version = explanation.get("generator_version")
    if not isinstance(generator_version, str) or not generator_version.strip():
        errors.append(
            f"{context}.metadata.explanation.generator_version: must be a nonempty string"
        )
    elif generator_path is not None:
        stamp_match = GENERATOR_STAMP_RE.fullmatch(generator_version.strip())
        if stamp_match is None:
            errors.append(
                f"{context}.metadata.explanation.generator_version: must include "
                "the generator SHA256 stamp"
            )
        else:
            expected_stamp = _sha256(generator_path)[:12]
            if stamp_match.group(1).lower() != expected_stamp:
                errors.append(
                    f"{context}.metadata.explanation.generator_version: stale generator "
                    f"SHA256 stamp; expected {expected_stamp}"
                )

    executed = explanation.get("executed")
    if not isinstance(executed, bool):
        errors.append(f"{context}.metadata.explanation.executed: must be a boolean")
    elif not executed:
        errors.append(f"{context}.metadata.explanation.executed: must be true")

    metadata_claims = _string_list(
        explanation.get("claims"),
        f"{context}.metadata.explanation.claims",
        errors,
        require_nonempty=True,
        unique=True,
    )
    for claim_id in metadata_claims:
        if claim_id not in claims:
            errors.append(
                f"{context}.metadata.explanation.claims: unknown claim ID {claim_id!r}"
            )
    missing_claims = sorted(set(required_claims) - set(metadata_claims))
    if missing_claims:
        errors.append(
            f"{context}.metadata.explanation.claims: missing manifest claims "
            + ", ".join(missing_claims)
        )

    inputs = explanation.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        errors.append(
            f"{context}.metadata.explanation.inputs: must be a nonempty path-to-SHA256 mapping"
        )
    else:
        for raw_path, expected_hash in inputs.items():
            input_context = f"{context}.metadata.explanation.inputs[{raw_path!r}]"
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"{input_context}: input path must be a nonempty string")
                continue
            if "\\" in raw_path or PurePosixPath(raw_path).is_absolute():
                errors.append(
                    f"{input_context}: input path must be repository-relative POSIX form"
                )
            input_path = _require_file(raw_path, input_context, errors)
            if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
                errors.append(f"{input_context}: value must be a 64-character SHA256 hex digest")
                continue
            if input_path is not None:
                actual_hash = _sha256(input_path)
                if actual_hash != expected_hash.lower():
                    errors.append(
                        f"{input_context}: stale SHA256; expected {expected_hash.lower()}, "
                        f"current {actual_hash}"
                    )

    cells = notebook.get("cells")
    if not isinstance(cells, list):
        errors.append(f"{context}.cells: must be a list")
        return 0

    links_checked = 0
    for index, cell in enumerate(cells):
        cell_context = f"{context}.cells[{index}]"
        if not isinstance(cell, dict):
            errors.append(f"{cell_context}: must be an object")
            continue
        cell_type = cell.get("cell_type")
        if cell_type == "code":
            if cell.get("execution_count") is None:
                errors.append(f"{cell_context}.execution_count: code cell was not executed")
            outputs = cell.get("outputs")
            if not isinstance(outputs, list):
                errors.append(f"{cell_context}.outputs: must be a list")
                continue
            for output_index, output in enumerate(outputs):
                if not isinstance(output, dict):
                    errors.append(f"{cell_context}.outputs[{output_index}]: must be an object")
                elif output.get("output_type") == "error":
                    error_name = output.get("ename", "unknown error")
                    errors.append(
                        f"{cell_context}.outputs[{output_index}]: error output {error_name!r}"
                    )
        elif cell_type == "markdown":
            source = cell.get("source", "")
            if isinstance(source, list) and all(isinstance(part, str) for part in source):
                source = "".join(source)
            if not isinstance(source, str):
                errors.append(f"{cell_context}.source: must be a string or list of strings")
            else:
                links_checked += _validate_markdown_links(
                    source,
                    base_dir=path.parent,
                    context=cell_context,
                    errors=errors,
                )
    return links_checked


def _validate_declared_files(
    manifest: dict[str, Any], section: str, errors: list[str]
) -> None:
    mapping = manifest.get(section)
    if not isinstance(mapping, dict) or not mapping:
        errors.append(f"manifest.{section}: must be a nonempty object")
        return
    for name, raw_path in mapping.items():
        _require_file(raw_path, f"manifest.{section}.{name}", errors)


def validate() -> dict[str, Any]:
    errors: list[str] = []
    manifest = _load_json(MANIFEST_PATH, "manifest", errors)
    sources_payload = _load_json(SOURCES_PATH, "sources", errors)
    claim_records = _load_claims(errors)

    sources = _validate_sources(sources_payload, errors)
    claims = _validate_claims(claim_records, sources, errors)

    document_records = _records(manifest, "documents", "manifest", errors)
    notebook_records = _records(manifest, "notebooks", "manifest", errors)
    required_concepts = _string_list(
        manifest.get("required_concepts"),
        "manifest.required_concepts",
        errors,
        require_nonempty=True,
        unique=True,
    )
    required_claims = _string_list(
        manifest.get("required_claims"),
        "manifest.required_claims",
        errors,
        require_nonempty=True,
        unique=True,
    )
    for claim_id in required_claims:
        if claim_id not in claims:
            errors.append(f"manifest.required_claims: unknown claim ID {claim_id!r}")

    artifact_ids: dict[str, str] = {}
    document_paths: dict[Path, str] = {}
    document_claims: dict[Path, set[str]] = {}
    covered_concepts: set[str] = set()
    covered_claims: set[str] = set()
    covered_sources: set[str] = set()

    for index, record in enumerate(document_records):
        context = f"manifest.documents[{index}]"
        document_id = _register_id(record, context, artifact_ids, errors)
        path = _require_file(record.get("path"), f"{context}.path", errors)
        if path is None:
            continue
        if path in document_paths:
            errors.append(
                f"{context}.path: duplicate document path; first declared at "
                f"{document_paths[path]}"
            )
        else:
            document_paths[path] = context

        _text, frontmatter = _parse_frontmatter(path, context, errors)
        if frontmatter is None:
            continue
        if frontmatter.get("explanation_id") != document_id:
            errors.append(
                f"{context}: frontmatter explanation_id "
                f"{frontmatter.get('explanation_id')!r} does not match {document_id!r}"
            )

        concepts = _string_list(
            frontmatter.get("concepts"), f"{context}.frontmatter.concepts", errors, unique=True
        )
        doc_claims = _string_list(
            frontmatter.get("claims"), f"{context}.frontmatter.claims", errors, unique=True
        )
        doc_sources = _string_list(
            frontmatter.get("sources"), f"{context}.frontmatter.sources", errors, unique=True
        )
        covered_concepts.update(concepts)
        covered_claims.update(doc_claims)
        covered_sources.update(doc_sources)
        document_claims[path] = set(doc_claims)
        for claim_id in doc_claims:
            if claim_id not in claims:
                errors.append(f"{context}.frontmatter.claims: unknown claim ID {claim_id!r}")
        for source_id in doc_sources:
            if source_id not in sources:
                errors.append(f"{context}.frontmatter.sources: unknown source ID {source_id!r}")

    missing_concepts = sorted(set(required_concepts) - covered_concepts)
    if missing_concepts:
        errors.append("coverage: missing required concepts " + ", ".join(missing_concepts))
    missing_claim_coverage = sorted(set(required_claims) - covered_claims)
    if missing_claim_coverage:
        errors.append("coverage: missing required claims " + ", ".join(missing_claim_coverage))

    for claim_id, record in claims.items():
        explained_in = record.get("explained_in")
        if not isinstance(explained_in, list):
            continue
        for index, raw_path in enumerate(explained_in):
            context = f"claim {claim_id}.explained_in[{index}]"
            path = _repo_path(raw_path, context, errors)
            if path is None:
                continue
            if path not in document_paths:
                errors.append(
                    f"{context}: path is not declared in manifest.documents: {raw_path!r}"
                )
            elif claim_id not in document_claims.get(path, set()):
                errors.append(
                    f"{context}: manifest document frontmatter does not list claim {claim_id!r}"
                )

    links_checked = 0
    if EXPLANATION_DIR.is_dir():
        for markdown_path in sorted(EXPLANATION_DIR.rglob("*.md")):
            try:
                markdown_text = markdown_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                relative = markdown_path.relative_to(REPO_ROOT).as_posix()
                errors.append(f"{relative}: cannot read Markdown: {exc}")
                continue
            relative = markdown_path.relative_to(REPO_ROOT).as_posix()
            links_checked += _validate_markdown_links(
                markdown_text,
                base_dir=markdown_path.parent,
                context=relative,
                errors=errors,
            )

    notebook_paths: dict[Path, str] = {}
    for index, record in enumerate(notebook_records):
        context = f"manifest.notebooks[{index}]"
        _register_id(record, context, artifact_ids, errors)
        path = _require_file(record.get("path"), f"{context}.path", errors)
        generator_path = _require_file(
            record.get("generator"), f"{context}.generator", errors
        )
        notebook_claims = _string_list(
            record.get("claims"),
            f"{context}.claims",
            errors,
            require_nonempty=True,
            unique=True,
        )
        for claim_id in notebook_claims:
            if claim_id not in claims:
                errors.append(f"{context}.claims: unknown claim ID {claim_id!r}")
        if path is None:
            continue
        if path in notebook_paths:
            errors.append(
                f"{context}.path: duplicate notebook path; first declared at "
                f"{notebook_paths[path]}"
            )
        else:
            notebook_paths[path] = context
        links_checked += _validate_notebook(
            path,
            context=context,
            generator_path=generator_path,
            required_claims=notebook_claims,
            claims=claims,
            errors=errors,
        )

    _validate_declared_files(manifest, "ledgers", errors)
    _validate_declared_files(manifest, "maintenance", errors)

    summary: dict[str, Any] = {
        "ok": not errors,
        "counts": {
            "claims": len(claims),
            "claims_covered": len(covered_claims),
            "concepts_covered": len(covered_concepts),
            "documents": len(document_records),
            "links_checked": links_checked,
            "notebooks": len(notebook_records),
            "sources": len(sources),
            "sources_covered": len(covered_sources),
        },
        "errors": errors,
    }
    return summary


def main() -> int:
    try:
        summary = validate()
    except Exception as exc:  # pragma: no cover - last-resort machine-readable failure
        summary = {
            "ok": False,
            "counts": {},
            "errors": [f"validator: unexpected {type(exc).__name__}: {exc}"],
        }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
