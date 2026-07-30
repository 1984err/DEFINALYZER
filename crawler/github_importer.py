"""Import public GitHub-hosted Markdown without changing the web crawler."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


GITHUB_API = "https://api.github.com"
GITHUB_HOSTS = {"github.com", "www.github.com"}
MANIFEST_NAME = "github-import.json"
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_MARKDOWN_BYTES = 5 * 1024 * 1024
MAX_TOTAL_MARKDOWN_BYTES = 50 * 1024 * 1024
MARKDOWN_SUFFIXES = {".md", ".markdown"}
SAFE_REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"


@dataclass(frozen=True)
class GitHubImportSummary:
    protocol: str
    domain: str
    output_directory: str
    discovered: int
    saved: int
    skipped: int
    failed: int
    failed_urls: tuple[str, ...]
    repository: str
    requested_ref: str
    commit_sha: str
    manifest_path: str


JsonFetcher = Callable[[str], dict[str, Any]]
BytesFetcher = Callable[[str], bytes]


def is_github_repository_url(value: str) -> bool:
    try:
        parse_github_repository_url(value)
    except ValueError:
        return False
    return True


def parse_github_repository_url(value: str) -> GitHubRepository:
    clean = value.strip()
    parsed = urlparse(clean if "://" in clean else f"https://{clean}")
    if parsed.scheme not in {"http", "https"} or parsed.netloc.casefold() not in GITHUB_HOSTS:
        raise ValueError("GitHub source must be a github.com repository URL.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ValueError(
            "GitHub source must identify one repository, for example "
            "https://github.com/owner/repository."
        )
    owner, name = parts
    name = name.removesuffix(".git")
    if not all(
        part
        and SAFE_REPOSITORY_PART.fullmatch(part)
        and part not in {".", ".."}
        for part in (owner, name)
    ):
        raise ValueError("GitHub owner or repository name is invalid.")
    return GitHubRepository(owner=owner, name=name)


def import_github_markdown(
    *,
    protocol_name: str,
    repository_url: str,
    output_directory: str | Path,
    ref: str | None = None,
    refresh: bool = False,
    fetch_json: JsonFetcher | None = None,
    fetch_bytes: BytesFetcher | None = None,
) -> GitHubImportSummary:
    """Import Markdown files from one immutable public repository snapshot."""

    protocol = protocol_name.strip()
    if not protocol:
        raise ValueError("Protocol name cannot be empty.")
    repository = parse_github_repository_url(repository_url)
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    existing_manifest = _load_manifest(output / MANIFEST_NAME)
    previous_files = _manifest_files(existing_manifest)
    if (
        not refresh
        and existing_manifest
        and existing_manifest.get("repository") == repository.url
        and isinstance(existing_manifest.get("commit_sha"), str)
    ):
        prior_sha = str(existing_manifest["commit_sha"])
        prior_ref = str(existing_manifest.get("requested_ref") or "unknown")
        summary = GitHubImportSummary(
            protocol=protocol,
            domain="github.com",
            output_directory=str(output),
            discovered=len(previous_files),
            saved=0,
            skipped=len(previous_files),
            failed=0,
            failed_urls=(),
            repository=repository.url,
            requested_ref=prior_ref,
            commit_sha=prior_sha,
            manifest_path=str(output / MANIFEST_NAME),
        )
        _write_json(output / "crawl-report.json", asdict(summary))
        return summary
    json_fetcher = fetch_json or _fetch_json
    bytes_fetcher = fetch_bytes or _fetch_bytes

    metadata_url = (
        f"{GITHUB_API}/repos/{quote(repository.owner)}/{quote(repository.name)}"
    )
    metadata = json_fetcher(metadata_url)
    default_branch = metadata.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch.strip():
        raise ValueError("GitHub repository metadata has no default branch.")
    requested_ref = ref.strip() if ref and ref.strip() else default_branch
    commit_url = (
        f"{metadata_url}/commits/{quote(requested_ref, safe='')}"
    )
    commit = json_fetcher(commit_url)
    commit_sha = commit.get("sha")
    if (
        not isinstance(commit_sha, str)
        or not re.fullmatch(r"[a-fA-F0-9]{40}", commit_sha)
    ):
        raise ValueError("GitHub did not return a valid commit SHA.")
    commit_sha = commit_sha.lower()

    archive_url = f"{repository.url}/archive/{commit_sha}.zip"
    archive = bytes_fetcher(archive_url)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("GitHub repository archive exceeds the safe size limit.")
    files = _read_markdown_archive(archive)
    if not files:
        raise ValueError("The GitHub repository contains no Markdown files.")

    collisions = [
        relative.as_posix()
        for relative, _ in files
        if _safe_destination(output, relative).exists()
        and (not refresh or relative.as_posix() not in previous_files)
    ]
    if collisions:
        raise FileExistsError(
            "GitHub import would overwrite a source file not owned by the "
            f"current import manifest: {collisions[0]}"
        )
    saved = 0
    skipped = 0
    imported_rows = []

    for relative, content in files:
        destination = _safe_destination(output, relative)
        source_url = (
            f"{repository.url}/blob/{commit_sha}/"
            f"{quote(relative.as_posix(), safe='/')}"
        )
        document = (
            f"<!-- definalyzer-source: {source_url} -->\n"
            f"<!-- definalyzer-commit: {commit_sha} -->\n\n"
            f"{content.rstrip()}\n"
        )
        encoded = document.encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        imported_rows.append(
            {
                "path": relative.as_posix(),
                "source_url": source_url,
                "sha256": digest,
            }
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(destination)
        saved += 1

    current_files = {row["path"] for row in imported_rows}
    if refresh:
        for stale in sorted(previous_files - current_files):
            stale_path = _safe_destination(output, PurePosixPath(stale))
            if stale_path.is_file():
                stale_path.unlink()
            _remove_empty_parents(stale_path.parent, stop=output)

    imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "schema_version": 1,
        "source_type": "public_github_repository",
        "protocol": protocol,
        "repository": repository.url,
        "requested_ref": requested_ref,
        "commit_sha": commit_sha,
        "imported_at": imported_at,
        "archive_url": archive_url,
        "files": imported_rows,
    }
    manifest_path = output / MANIFEST_NAME
    _write_json(manifest_path, manifest)
    summary = GitHubImportSummary(
        protocol=protocol,
        domain="github.com",
        output_directory=str(output),
        discovered=len(files),
        saved=saved,
        skipped=skipped,
        failed=0,
        failed_urls=(),
        repository=repository.url,
        requested_ref=requested_ref,
        commit_sha=commit_sha,
        manifest_path=str(manifest_path),
    )
    _write_json(output / "crawl-report.json", asdict(summary))
    return summary


def _read_markdown_archive(
    archive: bytes,
) -> tuple[tuple[PurePosixPath, str], ...]:
    files: list[tuple[PurePosixPath, str]] = []
    total_size = 0
    try:
        package = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise ValueError("GitHub returned an invalid repository archive.") from exc
    with package:
        for info in package.infolist():
            if info.is_dir():
                continue
            archive_path = PurePosixPath(info.filename)
            parts = archive_path.parts
            if len(parts) < 2:
                continue
            relative = PurePosixPath(*parts[1:])
            if not _safe_relative_path(relative):
                raise ValueError("GitHub archive contains an unsafe file path.")
            if relative.suffix.casefold() not in MARKDOWN_SUFFIXES:
                continue
            if info.file_size > MAX_MARKDOWN_BYTES:
                raise ValueError(
                    f"Markdown file exceeds the safe size limit: {relative}"
                )
            total_size += info.file_size
            if total_size > MAX_TOTAL_MARKDOWN_BYTES:
                raise ValueError(
                    "GitHub Markdown content exceeds the safe total size limit."
                )
            raw = package.read(info)
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"Markdown file is not valid UTF-8: {relative}"
                ) from exc
            files.append((relative, content))
    return tuple(sorted(files, key=lambda item: item[0].as_posix().casefold()))


def _safe_relative_path(path: PurePosixPath) -> bool:
    return (
        not path.is_absolute()
        and bool(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
        and ":" not in path.parts[0]
    )


def _safe_destination(root: Path, relative: PurePosixPath) -> Path:
    if not _safe_relative_path(relative):
        raise ValueError("Imported path is unsafe.")
    destination = root.joinpath(*relative.parts).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError("Imported path escapes the project source directory.")
    return destination


def _fetch_json(url: str) -> dict[str, Any]:
    document = json.loads(_fetch_bytes(url).decode("utf-8"))
    if not isinstance(document, dict):
        raise ValueError("GitHub API returned a non-object response.")
    return document


def _fetch_bytes(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "DEFINALYZER/1.0",
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read(MAX_ARCHIVE_BYTES + 1)


def _load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return document if isinstance(document, dict) else None


def _manifest_files(document: dict[str, Any] | None) -> set[str]:
    if not document or not isinstance(document.get("files"), list):
        return set()
    return {
        str(row["path"])
        for row in document["files"]
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }


def _write_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _remove_empty_parents(directory: Path, *, stop: Path) -> None:
    current = directory
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import public GitHub Markdown into a source directory."
    )
    parser.add_argument("protocol")
    parser.add_argument("repository")
    parser.add_argument("--output", required=True)
    parser.add_argument("--ref")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = import_github_markdown(
            protocol_name=args.protocol,
            repository_url=args.repository,
            output_directory=args.output,
            ref=args.ref,
            refresh=args.refresh,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Import stopped: {exc}")
        return 1
    print(f"Repository: {summary.repository}")
    print(f"Commit:     {summary.commit_sha}")
    print(f"Discovered: {summary.discovered}")
    print(f"Saved:      {summary.saved}")
    print(f"Skipped:    {summary.skipped}")
    print(f"Output:     {summary.output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
