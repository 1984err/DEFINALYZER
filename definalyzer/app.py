"""One entry point for guided users, power users, and agents."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Callable, Sequence

from blockchain_collector.envfile import load_environment_file
from blockchain_collector.menu import run_guided_menu as run_collector_menu

from .extraction import TEMPLATE_FILES, extract_research_page
from .providers import ProviderError, create_provider
from .settings import SettingsManager
from .workspace import ProjectWorkspace, WorkspaceManager


InputFunction = Callable[[str], str]
PrintFunction = Callable[[str], None]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = PROJECT_ROOT / "output"
DEFAULT_PATTERN = "*/docs/*"
DEFAULT_RETRIES = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Unified DEFINALYZER interface. Run without a command for the "
            "guided menu."
        ),
    )
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Generated project and Obsidian output root.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init = subparsers.add_parser("init", help="Create a research project.")
    init.add_argument("name")
    init.add_argument(
        "--type",
        choices=("protocol", "chain", "token"),
        default="protocol",
    )
    init.add_argument("--docs-url")
    init.add_argument(
        "--verification",
        choices=("not_requested", "pending", "unsupported"),
        default="not_requested",
    )

    crawl = subparsers.add_parser("crawl", help="Crawl project documentation.")
    crawl.add_argument("project")
    crawl.add_argument("--docs-url")
    crawl.add_argument("--pattern", default=DEFAULT_PATTERN)
    crawl.add_argument("--refresh", action="store_true")
    crawl.add_argument("--retries", type=int, default=DEFAULT_RETRIES)

    status = subparsers.add_parser("status", help="Show project status.")
    status.add_argument("project", nargs="?")

    collect = subparsers.add_parser(
        "collect",
        help="Open the guided blockchain evidence collector for a project.",
    )
    collect.add_argument("project")

    provider = subparsers.add_parser(
        "provider",
        help="Configure or test the external AI provider.",
    )
    provider.add_argument(
        "action",
        choices=("configure", "status", "test"),
    )
    provider.add_argument("--executable")
    provider.add_argument("--timeout", type=int, default=900)

    extract = subparsers.add_parser(
        "extract",
        help="Generate one fact-first research page.",
    )
    extract.add_argument("project")
    extract.add_argument(
        "--template",
        choices=tuple(sorted(TEMPLATE_FILES)),
        default="protocol-overview",
    )

    for name in ("registry", "verification-plan", "all"):
        stage = subparsers.add_parser(
            name,
            help="Reserved unified workflow stage.",
        )
        stage.add_argument("project")

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: InputFunction = input,
    print_fn: PrintFunction = print,
) -> int:
    args = build_parser().parse_args(argv)
    manager = WorkspaceManager(args.workspace)

    try:
        if args.command is None:
            return run_menu(manager, input_fn=input_fn, print_fn=print_fn)
        if args.command == "init":
            workspace = manager.create_project(
                name=args.name,
                entity_type=args.type,
                docs_url=args.docs_url,
                verification_status=args.verification,
            )
            _print_created(workspace, print_fn)
            return 0
        if args.command == "crawl":
            workspace = manager.load_project(args.project)
            docs_url = args.docs_url or workspace.document.get("docs_url")

            if not docs_url:
                raise ValueError(
                    "No documentation URL is configured. Pass --docs-url."
                )
            return _crawl(
                manager,
                workspace,
                docs_url=str(docs_url),
                pattern=args.pattern,
                refresh=args.refresh,
                retries=args.retries,
                print_fn=print_fn,
            )
        if args.command == "status":
            return _show_status(manager, args.project, print_fn)
        if args.command == "collect":
            workspace = manager.load_project(args.project)
            return _collect(manager, workspace)
        if args.command == "provider":
            return _provider_command(
                manager,
                action=args.action,
                executable=args.executable,
                timeout=args.timeout,
                print_fn=print_fn,
            )
        if args.command == "extract":
            workspace = manager.load_project(args.project)
            return _extract(
                manager,
                workspace,
                template_name=args.template,
                print_fn=print_fn,
            )
        if args.command in {
            "registry",
            "verification-plan",
            "all",
        }:
            workspace = manager.load_project(args.project)
            return _unconfigured_stage(args.command, workspace, print_fn)
    except (EOFError, KeyboardInterrupt):
        print_fn("\nCancelled.")
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print_fn(f"Stopped: {exc}")
        return 1

    return 1


def run_menu(
    manager: WorkspaceManager,
    *,
    input_fn: InputFunction = input,
    print_fn: PrintFunction = print,
) -> int:
    manager.initialize()

    while True:
        print_fn("")
        print_fn("DEFINALYZER")
        print_fn("1. Create a project")
        print_fn("2. Run complete workflow")
        print_fn("3. Crawl documentation")
        print_fn("4. Generate research pages")
        print_fn("5. Generate registry")
        print_fn("6. Create verification plan")
        print_fn("7. Collect blockchain evidence")
        print_fn("8. Configure or test AI provider")
        print_fn("9. View project status")
        print_fn("10. Exit")
        choice = input_fn("Choice [1-10]: ").strip()

        try:
            if choice == "1":
                _menu_create(manager, input_fn, print_fn)
            elif choice == "2":
                workspace = _menu_project(manager, input_fn, print_fn)
                _unconfigured_stage("all", workspace, print_fn)
            elif choice == "3":
                workspace = _menu_project(manager, input_fn, print_fn)
                docs_url = (
                    workspace.document.get("docs_url")
                    or _required(input_fn, "Documentation URL: ")
                )
                _crawl(
                    manager,
                    workspace,
                    docs_url=str(docs_url),
                    pattern=(
                        input_fn(f"Sitemap pattern [{DEFAULT_PATTERN}]: ").strip()
                        or DEFAULT_PATTERN
                    ),
                    refresh=_yes_no(
                        input_fn,
                        "Refresh existing source pages? [y/N]: ",
                    ),
                    retries=DEFAULT_RETRIES,
                    print_fn=print_fn,
                )
            elif choice == "4":
                workspace = _menu_project(manager, input_fn, print_fn)
                print_fn("Available research pages:")
                names = sorted(TEMPLATE_FILES)
                for index, name in enumerate(names, start=1):
                    print_fn(f"  {index}. {name}")
                selected = _required(input_fn, "Template name or number: ")
                if selected.isdigit() and 1 <= int(selected) <= len(names):
                    selected = names[int(selected) - 1]
                _extract(
                    manager,
                    workspace,
                    template_name=selected,
                    print_fn=print_fn,
                )
            elif choice in {"5", "6"}:
                workspace = _menu_project(manager, input_fn, print_fn)
                command = "registry" if choice == "5" else "verification-plan"
                _unconfigured_stage(command, workspace, print_fn)
            elif choice == "7":
                workspace = _menu_project(manager, input_fn, print_fn)
                _collect(manager, workspace)
            elif choice == "8":
                _menu_provider(manager, input_fn, print_fn)
            elif choice == "9":
                name = input_fn(
                    "Project name (leave blank to list all): "
                ).strip()
                _show_status(manager, name or None, print_fn)
            elif choice == "10":
                print_fn("Goodbye.")
                return 0
            else:
                print_fn("Please enter a number from 1 to 10.")
        except (OSError, RuntimeError, ValueError) as exc:
            print_fn(f"Stopped: {exc}")


def _menu_create(
    manager: WorkspaceManager,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    name = _required(input_fn, "Project name: ")
    entity_value = (
        input_fn("Entity type [protocol/chain/token] (protocol): ").strip().lower()
        or "protocol"
    )
    docs_url = input_fn("Documentation URL (optional): ").strip() or None
    verification = _yes_no(
        input_fn,
        "Plan blockchain verification later? [y/N]: ",
    )
    workspace = manager.create_project(
        name=name,
        entity_type=entity_value,
        docs_url=docs_url,
        verification_status="pending" if verification else "not_requested",
    )
    _print_created(workspace, print_fn)


def _menu_project(
    manager: WorkspaceManager,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    projects = manager.list_projects()

    if not projects:
        raise ValueError("No projects exist. Create a project first.")

    print_fn("Projects:")
    for index, project in enumerate(projects, start=1):
        print(f"  {index}. {project.name} ({project.slug})")

    value = _required(input_fn, "Project name or number: ")
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(projects):
            return projects[index - 1]
    return manager.load_project(value)


def _crawl(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    docs_url: str,
    pattern: str,
    refresh: bool,
    retries: int,
    print_fn: PrintFunction,
) -> int:
    try:
        from crawler.crawler import crawl_protocol
    except ImportError as exc:
        raise RuntimeError(
            "Crawler dependencies are unavailable. Run "
            "'pip install -r requirements.txt' and 'crawl4ai-setup'."
        ) from exc

    if workspace.document.get("docs_url") != docs_url:
        workspace = manager.set_docs_url(workspace, docs_url)

    try:
        summary = asyncio.run(
            crawl_protocol(
                protocol_name=workspace.name,
                docs_url=docs_url,
                output_root=manager.root / "sources",
                pattern=pattern,
                refresh=refresh,
                retries=retries,
            )
        )
    except Exception as exc:
        manager.update_stage(
            workspace,
            "crawl",
            "blocked",
            detail=str(exc),
        )
        raise

    status = "complete" if not summary.failed else "partial"
    manager.update_stage(
        workspace,
        "crawl",
        status,
        detail=(
            f"{summary.saved} saved, {summary.skipped} skipped, "
            f"{summary.failed} failed"
        ),
    )
    print_fn(f"Project sources: {workspace.sources_directory}")
    return 0 if not summary.failed else 2


def _collect(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
) -> int:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_environment_file(env_path)
    exit_code = run_collector_menu(working_directory=workspace.project_root)
    manager.update_stage(
        workspace,
        "evidence_collection",
        "complete" if exit_code == 0 else "partial",
        detail=f"Collector menu exit code {exit_code}",
    )
    return exit_code


def _extract(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    template_name: str,
    print_fn: PrintFunction,
) -> int:
    settings = SettingsManager(manager.root).load()
    provider = create_provider(settings["llm"])

    try:
        result = extract_research_page(
            workspace=workspace,
            template_name=template_name,
            provider=provider,
            prompts_root=PROJECT_ROOT / "prompts",
        )
    except Exception as exc:
        manager.update_stage(
            workspace,
            "research",
            "blocked",
            detail=str(exc),
        )
        raise

    manager.update_stage(
        workspace,
        "research",
        "partial",
        detail=f"Generated {result.template}: {result.output_path.name}",
    )
    print_fn(f"Research page: {result.output_path}")
    print_fn(
        f"Sources: {result.source_files} files, "
        f"{result.source_characters:,} characters"
    )
    print_fn(f"Provider: {result.provider}")
    return 0


def _unconfigured_stage(
    command: str,
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> int:
    labels = {
        "registry": "Registry generation",
        "verification-plan": "Verification planning",
        "all": "The complete automated workflow",
    }
    print_fn(
        f"{labels[command]} is not configured yet for {workspace.name}."
    )
    print_fn(
        "The requested workflow stage has not been connected yet."
    )
    return 2


def _provider_command(
    manager: WorkspaceManager,
    *,
    action: str,
    executable: str | None,
    timeout: int,
    print_fn: PrintFunction,
) -> int:
    settings_manager = SettingsManager(manager.root)

    if action == "configure":
        settings = settings_manager.configure_hermes(
            executable=executable,
            timeout_seconds=timeout,
        )
        provider = create_provider(settings["llm"])
        print_fn("Hermes provider configured.")
        print_fn(f"Executable: {provider.executable}")
        print_fn("Credentials remain managed by Hermes.")
        return 0

    settings = settings_manager.load()
    provider = create_provider(settings["llm"])
    diagnostic = provider.diagnostic()
    print_fn(json.dumps(diagnostic, indent=2))

    if action == "test":
        response = provider.generate(
            "Reply with exactly: DEFINALYZER provider connection successful",
            working_directory=PROJECT_ROOT,
        )
        print_fn(response.text)
    return 0


def _menu_provider(
    manager: WorkspaceManager,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    print_fn("1. Configure detected Hermes installation")
    print_fn("2. Show provider status")
    print_fn("3. Run a small live provider test")
    action = _required(input_fn, "Provider option [1-3]: ")
    mapped = {
        "1": "configure",
        "2": "status",
        "3": "test",
    }.get(action)

    if mapped is None:
        raise ValueError("Please enter 1, 2, or 3.")

    _provider_command(
        manager,
        action=mapped,
        executable=None,
        timeout=900,
        print_fn=print_fn,
    )


def _show_status(
    manager: WorkspaceManager,
    project: str | None,
    print_fn: PrintFunction,
) -> int:
    if project:
        workspace = manager.load_project(project)
        print_fn(json.dumps(manager.status_document(workspace), indent=2))
        return 0

    projects = manager.list_projects()
    if not projects:
        print_fn("No projects exist.")
        return 0
    for workspace in projects:
        stages = workspace.document["stages"]
        complete = sum(
            stage["status"] == "complete" for stage in stages.values()
        )
        print_fn(
            f"{workspace.name} [{workspace.document['entity_type']}] — "
            f"{complete}/{len(stages)} stages complete — verification: "
            f"{workspace.document['verification_status']}"
        )
    return 0


def _print_created(
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> None:
    print_fn(f"Project created: {workspace.name}")
    print_fn(f"Manifest: {workspace.manifest_path}")
    print_fn(f"Obsidian folder: {workspace.vault_entity_directory}")
    print_fn(f"Open vault: {workspace.vault_root}")


def _required(input_fn: InputFunction, prompt: str) -> str:
    value = input_fn(prompt).strip()
    if not value:
        raise ValueError("A value is required.")
    return value


def _yes_no(input_fn: InputFunction, prompt: str) -> bool:
    value = input_fn(prompt).strip().lower()
    if not value:
        return False
    if value in {"y", "yes"}:
        return True
    if value in {"n", "no"}:
        return False
    raise ValueError("Expected yes or no.")
