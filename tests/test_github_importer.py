import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from crawler.github_importer import (
    import_github_markdown,
    is_github_repository_url,
    parse_github_repository_url,
)


COMMIT = "a" * 40


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as package:
        for path, content in files.items():
            package.writestr(f"example-{COMMIT}/{path}", content)
    return stream.getvalue()


def api_fetcher(url):
    if "/commits/" in url:
        return {"sha": COMMIT}
    return {"default_branch": "main"}


class GitHubImporterTests(unittest.TestCase):
    def test_recognizes_only_repository_root_urls(self):
        repository = parse_github_repository_url(
            "https://github.com/pump-fun/pump-public-docs"
        )

        self.assertEqual(repository.owner, "pump-fun")
        self.assertEqual(repository.name, "pump-public-docs")
        self.assertTrue(
            is_github_repository_url("github.com/pump-fun/pump-public-docs.git")
        )
        self.assertFalse(
            is_github_repository_url(
                "https://github.com/pump-fun/pump-public-docs/tree/main/docs"
            )
        )

    def test_imports_markdown_only_with_commit_provenance(self):
        package = archive(
            {
                "README.md": "# Example\n",
                "docs/FEES.md": "# Fees\n\nOne percent.\n",
                "docs/reference.markdown": "# Reference\n",
                "idl/program.json": '{"address":"ignored"}',
                "src/client.ts": "ignored",
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sources"
            summary = import_github_markdown(
                protocol_name="Example",
                repository_url="https://github.com/example/docs",
                output_directory=output,
                fetch_json=api_fetcher,
                fetch_bytes=lambda url: package,
            )
            fees = (output / "docs" / "FEES.md").read_text(encoding="utf-8")
            manifest = json.loads(
                (output / "github-import.json").read_text(encoding="utf-8")
            )
            idl_exists = (output / "idl" / "program.json").exists()

        self.assertEqual(summary.discovered, 3)
        self.assertEqual(summary.saved, 3)
        self.assertIn(f"definalyzer-commit: {COMMIT}", fees)
        self.assertIn(f"/blob/{COMMIT}/docs/FEES.md", fees)
        self.assertFalse(idl_exists)
        self.assertEqual(manifest["commit_sha"], COMMIT)
        self.assertEqual(len(manifest["files"]), 3)

    def test_second_import_skips_existing_snapshot_without_network(self):
        package = archive({"README.md": "# Example\n"})
        calls = []

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sources"
            import_github_markdown(
                protocol_name="Example",
                repository_url="https://github.com/example/docs",
                output_directory=output,
                fetch_json=api_fetcher,
                fetch_bytes=lambda url: package,
            )
            summary = import_github_markdown(
                protocol_name="Example",
                repository_url="https://github.com/example/docs",
                output_directory=output,
                fetch_json=lambda url: calls.append(url),
                fetch_bytes=lambda url: calls.append(url),
            )

        self.assertEqual(calls, [])
        self.assertEqual(summary.saved, 0)
        self.assertEqual(summary.skipped, 1)
        self.assertEqual(summary.commit_sha, COMMIT)

    def test_refresh_removes_only_manifest_owned_stale_files(self):
        first = archive(
            {
                "README.md": "# First\n",
                "docs/OLD.md": "# Old\n",
            }
        )
        second = archive({"README.md": "# Second\n"})

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sources"
            import_github_markdown(
                protocol_name="Example",
                repository_url="https://github.com/example/docs",
                output_directory=output,
                fetch_json=api_fetcher,
                fetch_bytes=lambda url: first,
            )
            unrelated = output / "manual.md"
            unrelated.write_text("# Manual\n", encoding="utf-8")
            import_github_markdown(
                protocol_name="Example",
                repository_url="https://github.com/example/docs",
                output_directory=output,
                refresh=True,
                fetch_json=api_fetcher,
                fetch_bytes=lambda url: second,
            )
            old_exists = (output / "docs" / "OLD.md").exists()
            unrelated_exists = unrelated.exists()
            readme = (output / "README.md").read_text(encoding="utf-8")

        self.assertFalse(old_exists)
        self.assertTrue(unrelated_exists)
        self.assertIn("# Second", readme)


if __name__ == "__main__":
    unittest.main()
