"""One entry point for guided users, power users, and agents."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Callable, Sequence

from blockchain_collector.envfile import load_environment_file
from blockchain_collector.menu import run_guided_menu as run_collector_menu

from .analyst_review import (
    ReviewSection,
    list_review_pages,
    parse_review_sections,
    run_analyst_review,
    save_analyst_review,
    select_review_page,
    select_review_section,
)
from .extraction import (
    OUTPUT_FILES,
    TEMPLATE_FILES,
    extract_research_page,
    plan_extraction,
)
from .evaluation import (
    generate_evaluation_proposals,
    pending_proposals,
    refresh_verification_summary,
    review_proposal,
)
from .market_data import refresh_market_data
from .obsidian_links import insert_verification_links
from .providers import ProviderError, create_provider
from .registry_workflow import (
    registry_needs_token_discovery,
    refresh_token_pages_from_registry,
    run_registry_workflow,
)
from .settings import SettingsManager
from .source_coverage import (
    CATEGORIES,
    CATEGORY_LABELS,
    add_official_source,
    ensure_source_coverage,
    sources_for_category,
    sync_research_coverage,
    update_source_status,
    write_coverage_source,
)
from .verification_planning import generate_verification_plan
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
    crawl.add_argument(
        "--ref",
        help="Git branch, tag, or commit. GitHub repositories only.",
    )

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
    extract.add_argument(
        "--refresh",
        action="store_true",
        help="Replace an existing generated research page.",
    )
    extract.add_argument(
        "--plan",
        action="store_true",
        help="Show source size and minimum provider-call estimate without AI.",
    )
    extract.add_argument(
        "--mode",
        choices=("auto", "single", "chunked"),
        default="auto",
        help=(
            "auto uses one request when safe and resumable batches when needed"
        ),
    )

    registry = subparsers.add_parser(
        "registry",
        help="Generate scoped entity registry, token pages, and links.",
    )
    registry.add_argument("project")

    market_data = subparsers.add_parser(
        "market-data",
        help="Refresh exact-address CoinGecko supply data without AI.",
    )
    market_data.add_argument("project")
    market_data.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore supply data cached within the last day.",
    )

    ask = subparsers.add_parser(
        "ask",
        help="Ask Hermes about one selected research-page section.",
    )
    ask.add_argument("project")
    ask.add_argument("--page", required=True, help="Markdown page name or stem.")
    ask.add_argument("--heading", required=True, help="Exact Markdown heading.")
    ask.add_argument("--question", required=True)
    ask.add_argument(
        "--save",
        action="store_true",
        help="Save the non-canonical answer under Analyst Reviews.",
    )

    source = subparsers.add_parser(
        "source",
        help="Register, list, or collect categorized official sources.",
    )
    source.add_argument("action", choices=("add", "list", "crawl"))
    source.add_argument("project")
    source.add_argument("--category", choices=CATEGORIES)
    source.add_argument("--url")
    source.add_argument("--refresh", action="store_true")

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Create human-reviewable evidence evaluation proposals.",
    )
    evaluate.add_argument("project")
    review = subparsers.add_parser(
        "review",
        help="Review pending evidence evaluation proposals.",
    )
    review.add_argument("project")

    verification_plan = subparsers.add_parser(
        "verification-plan",
        help="Create or refresh the categorized verification checklist.",
    )
    verification_plan.add_argument("project")

    complete = subparsers.add_parser(
        "all",
        help="Run or resume the complete research workflow.",
    )
    complete.add_argument("project")
    complete.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh sources and replace all generated research pages.",
    )

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
                ref=args.ref,
                print_fn=print_fn,
            )
        if args.command == "status":
            return _show_status(manager, args.project, print_fn)
        if args.command == "collect":
            workspace = manager.load_project(args.project)
            return _collect(
                manager,
                workspace,
                input_fn=input_fn,
                print_fn=print_fn,
            )
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
                mode=args.mode,
                plan_only=args.plan,
                refresh=args.refresh,
                print_fn=print_fn,
            )
        if args.command == "registry":
            workspace = manager.load_project(args.project)
            return _registry(manager, workspace, print_fn)
        if args.command == "market-data":
            workspace = manager.load_project(args.project)
            return _market_data(
                workspace,
                force=args.refresh,
                print_fn=print_fn,
            )
        if args.command == "ask":
            workspace = manager.load_project(args.project)
            page = select_review_page(workspace, args.page)
            section = select_review_section(page, args.heading)
            return _analyst_review(
                manager,
                workspace,
                page=page,
                section=section,
                question=args.question,
                save=args.save,
                print_fn=print_fn,
            )
        if args.command == "source":
            workspace = manager.load_project(args.project)
            return _source_command(
                manager,
                workspace,
                action=args.action,
                category=args.category,
                url=args.url,
                refresh=args.refresh,
                print_fn=print_fn,
            )
        if args.command == "verification-plan":
            workspace = manager.load_project(args.project)
            return _verification_plan(manager, workspace, print_fn)
        if args.command == "evaluate":
            workspace = manager.load_project(args.project)
            return _evaluate(manager, workspace, print_fn)
        if args.command == "review":
            workspace = manager.load_project(args.project)
            return _review(
                manager,
                workspace,
                input_fn=input_fn,
                print_fn=print_fn,
            )
        if args.command == "all":
            workspace = manager.load_project(args.project)
            return _complete_workflow(
                manager,
                workspace,
                refresh=args.refresh,
                print_fn=print_fn,
            )
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
        print_fn("8. Create evidence evaluation proposals")
        print_fn("9. Review pending evaluations")
        print_fn("10. Configure or test AI provider")
        print_fn("11. View project status")
        print_fn("12. Refresh current token supply data")
        print_fn("13. Explain a research-page entry")
        print_fn("14. Manage official sources")
        print_fn("15. Exit")
        choice = input_fn("Choice [1-15]: ").strip()

        try:
            if choice == "1":
                _menu_create(manager, input_fn, print_fn)
            elif choice == "2":
                workspace = _menu_project(manager, input_fn, print_fn)
                _complete_workflow(
                    manager,
                    workspace,
                    refresh=_yes_no(
                        input_fn,
                        "Refresh sources and existing research pages? [y/N]: ",
                    ),
                    print_fn=print_fn,
                )
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
                    pattern=_menu_crawl_pattern(input_fn, str(docs_url)),
                    refresh=_yes_no(
                        input_fn,
                        "Refresh existing source pages? [y/N]: ",
                    ),
                    retries=DEFAULT_RETRIES,
                    ref=_menu_github_ref(input_fn, str(docs_url)),
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
                    mode="auto",
                    refresh=False,
                    print_fn=print_fn,
                )
            elif choice in {"5", "6"}:
                workspace = _menu_project(manager, input_fn, print_fn)
                command = "registry" if choice == "5" else "verification-plan"
                if command == "registry":
                    _registry(manager, workspace, print_fn)
                else:
                    _verification_plan(manager, workspace, print_fn)
            elif choice == "7":
                workspace = _menu_project(manager, input_fn, print_fn)
                _collect(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "8":
                workspace = _menu_project(manager, input_fn, print_fn)
                _evaluate(manager, workspace, print_fn)
            elif choice == "9":
                workspace = _menu_project(manager, input_fn, print_fn)
                _review(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "10":
                _menu_provider(manager, input_fn, print_fn)
            elif choice == "11":
                name = input_fn(
                    "Project name (leave blank to list all): "
                ).strip()
                _show_status(manager, name or None, print_fn)
            elif choice == "12":
                workspace = _menu_project(manager, input_fn, print_fn)
                _market_data(
                    workspace,
                    force=_yes_no(
                        input_fn,
                        "Ignore supply data cached within the last day? [y/N]: ",
                    ),
                    print_fn=print_fn,
                )
            elif choice == "13":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_analyst_review(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "14":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_sources(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "15":
                print_fn("Goodbye.")
                return 0
            else:
                print_fn("Please enter a number from 1 to 15.")
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
        print_fn(f"  {index}. {project.name} ({project.slug})")

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
    ref: str | None = None,
    print_fn: PrintFunction,
) -> int:
    from crawler.github_importer import is_github_repository_url

    if workspace.document.get("docs_url") != docs_url:
        workspace = manager.set_docs_url(workspace, docs_url)

    try:
        if is_github_repository_url(docs_url):
            from crawler.github_importer import import_github_markdown

            summary = import_github_markdown(
                protocol_name=workspace.name,
                repository_url=docs_url,
                output_directory=workspace.sources_directory,
                ref=ref,
                refresh=refresh,
            )
            print_fn(
                f"GitHub snapshot: {summary.commit_sha} "
                f"({summary.discovered} Markdown files)"
            )
        else:
            if ref:
                raise ValueError("--ref can only be used with a GitHub repository.")
            try:
                from crawler.crawler import crawl_protocol
            except ImportError as exc:
                raise RuntimeError(
                    "Crawler dependencies are unavailable. Run "
                    "'pip install -r requirements.txt' and 'crawl4ai-setup'."
                ) from exc
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
    coverage = ensure_source_coverage(workspace)
    for source in coverage.sources:
        if source.url.casefold() == docs_url.strip().casefold():
            update_source_status(
                workspace,
                source_id=source.source_id,
                status="collected" if not summary.failed else "failed",
                detail=(
                    f"{summary.saved} saved, {summary.skipped} skipped, "
                    f"{summary.failed} failed"
                ),
            )
            break
    write_coverage_source(workspace)
    sync_research_coverage(workspace)
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
    *,
    input_fn: InputFunction = input,
    print_fn: PrintFunction = print,
) -> int:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_environment_file(env_path)
    exit_code = run_collector_menu(
        input_fn=input_fn,
        print_fn=print_fn,
        working_directory=workspace.project_root,
    )
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
    mode: str = "auto",
    plan_only: bool = False,
    refresh: bool = False,
    print_fn: PrintFunction,
) -> int:
    if plan_only:
        plan = plan_extraction(
            workspace=workspace,
            template_name=template_name,
            prompts_root=PROJECT_ROOT / "prompts",
        )
        print_fn(f"Template: {plan.template}")
        print_fn(
            f"Sources: {plan.source_files} files, "
            f"{plan.source_characters:,} characters"
        )
        print_fn(f"Planned mode: {plan.mode}")
        print_fn(f"Initial chunks: {plan.initial_chunks}")
        print_fn(
            "Minimum provider calls: "
            f"{plan.minimum_provider_calls} "
            "(additional consolidation calls may be required)"
        )
        return 0

    settings = SettingsManager(manager.root).load()
    provider = create_provider(settings["llm"])

    try:
        result = extract_research_page(
            workspace=workspace,
            template_name=template_name,
            provider=provider,
            prompts_root=PROJECT_ROOT / "prompts",
            mode=mode,
            refresh=refresh,
            progress=print_fn,
        )
    except Exception as exc:
        manager.update_stage(
            workspace,
            "research",
            "blocked",
            detail=str(exc),
        )
        raise

    missing_pages = [
        filename
        for filename in OUTPUT_FILES.values()
        if not (workspace.vault_entity_directory / filename).exists()
    ]
    research_status = "complete" if not missing_pages else "partial"
    detail = (
        "Generated all research pages"
        if not missing_pages
        else f"Generated {result.template}: {result.output_path.name}"
    )
    manager.update_stage(
        workspace,
        "research",
        research_status,
        detail=detail,
    )
    print_fn(f"Research page: {result.output_path}")
    print_fn(
        f"Sources: {result.source_files} files, "
        f"{result.source_characters:,} characters"
    )
    print_fn(f"Provider: {result.provider}")
    print_fn(
        f"Mode: {result.mode}; provider calls: {result.provider_calls}; "
        f"reused intermediate results: {result.reused_calls}"
    )
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


def _complete_workflow(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    refresh: bool,
    print_fn: PrintFunction,
) -> int:
    """Run or resume the complete research workflow through verification."""

    print_fn(f"Complete workflow: {workspace.name}")
    print_fn("Existing generated outputs will be reused." if not refresh else
             "Refresh enabled: sources and generated research will be rebuilt.")

    source_pages = _collected_source_pages(workspace)
    primary_pages = _collected_primary_source_pages(workspace)
    docs_url = workspace.document.get("docs_url")
    should_crawl = refresh or bool(docs_url and not primary_pages)
    if should_crawl:
        if not docs_url:
            raise ValueError(
                "The complete workflow needs a documentation URL or existing "
                "collected source pages."
            )
        print_fn("")
        print_fn("[1/5] Collecting primary documentation")
        crawl_code = _crawl(
            manager,
            workspace,
            docs_url=str(docs_url),
            pattern=DEFAULT_PATTERN,
            refresh=refresh,
            retries=DEFAULT_RETRIES,
            print_fn=print_fn,
        )
        if crawl_code:
            raise RuntimeError(
                "Primary documentation collection did not complete. Fix the "
                "reported crawl failures, then rerun the complete workflow."
            )
        workspace = manager.load_project(workspace.slug)
        source_pages = _collected_source_pages(workspace)
    else:
        print_fn("")
        print_fn(
            f"[1/5] Reusing {len(source_pages)} collected source pages"
        )
        manager.update_stage(
            workspace,
            "crawl",
            "complete",
            detail=f"Reused {len(source_pages)} collected source pages",
        )
        workspace = manager.load_project(workspace.slug)

    if not source_pages:
        raise RuntimeError(
            "Documentation collection produced no usable Markdown sources."
        )

    print_fn("")
    print_fn("[2/5] Generating research pages")
    generated = 0
    reused = 0
    for template_name, filename in OUTPUT_FILES.items():
        output_path = workspace.vault_entity_directory / filename
        if output_path.exists() and not refresh:
            reused += 1
            print_fn(f"Reused research page: {filename}")
            continue
        _extract(
            manager,
            workspace,
            template_name=template_name,
            mode="auto",
            refresh=refresh,
            print_fn=print_fn,
        )
        generated += 1
        workspace = manager.load_project(workspace.slug)
    manager.update_stage(
        workspace,
        "research",
        "complete",
        detail=f"{generated} generated; {reused} reused",
    )
    workspace = manager.load_project(workspace.slug)

    print_fn("")
    print_fn("[3/5] Building registry and current supply data")
    _registry(manager, workspace, print_fn)
    workspace = manager.load_project(workspace.slug)

    print_fn("")
    print_fn("[4/5] Checking source coverage")
    coverage = ensure_source_coverage(workspace)
    for category in CATEGORIES:
        print_fn(
            f"- {CATEGORY_LABELS[category]}: "
            f"{coverage.categories[category]}"
        )
    if coverage.status != "complete":
        print_fn(
            "Coverage is incomplete. Missing categories remain visible as "
            "research limitations and do not block the usable analysis."
        )

    print_fn("")
    verification_status = str(
        workspace.document.get("verification_status", "not_requested")
    )
    if verification_status in {"not_requested", "unsupported"}:
        print_fn(
            "[5/5] Verification skipped by project configuration. "
            "Research is ready for analysis without verification."
        )
    else:
        print_fn("[5/5] Creating verification checklist")
        _verification_plan(manager, workspace, print_fn)

    print_fn("")
    print_fn("Complete workflow finished.")
    print_fn(f"Obsidian vault: {workspace.vault_root}")
    return 0


def _collected_source_pages(
    workspace: ProjectWorkspace,
) -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(workspace.sources_directory.rglob("*.md"))
        if path.name.casefold() != "_source_coverage.md"
    )


def _collected_primary_source_pages(
    workspace: ProjectWorkspace,
) -> tuple[Path, ...]:
    return tuple(
        path
        for path in _collected_source_pages(workspace)
        if "_official" not in {
            part.casefold()
            for part in path.relative_to(workspace.sources_directory).parts
        }
    )


def _registry(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> int:
    registry_path = workspace.registry_directory / "registry.json"
    provider = None
    if registry_needs_token_discovery(workspace):
        settings = SettingsManager(manager.root).load()
        provider = create_provider(settings["llm"])
    try:
        result = run_registry_workflow(
            workspace=workspace,
            provider=provider,
        )
    except Exception as exc:
        manager.update_stage(
            workspace,
            "registry",
            "blocked",
            detail=str(exc),
        )
        raise

    # Supply enrichment is deterministic and non-blocking. It runs after the
    # registry during the normal workflow and remains separately refreshable.
    try:
        supply_result = refresh_market_data(workspace=workspace)
        refresh_token_pages_from_registry(workspace)
        available_supply = sum(
            snapshot.status == "available"
            for snapshot in supply_result.snapshots
        )
        print_fn(
            "Current token supply data: "
            f"{available_supply}/{len(supply_result.snapshots)} available "
            "from CoinGecko"
        )
    except Exception as exc:
        print_fn(
            "Current token supply data was not collected; registry "
            f"generation continues. Reason: {exc}"
        )

    coverage = ensure_source_coverage(workspace)
    registry_status = (
        "complete"
        if coverage.categories["tokenomics"] == "collected"
        else "partial"
    )
    manager.update_stage(
        workspace,
        "registry",
        registry_status,
        detail=(
            f"{len(result.tokens)} native/protocol-issued tokens; "
            f"{len(result.addresses)} address records; "
            f"{len(result.linked_pages)} linked research pages; "
            f"token source coverage: {coverage.categories['tokenomics']}"
        ),
    )
    print_fn(f"Registry: {result.registry_path}")
    if result.network_page:
        print_fn(f"Networks: {result.network_page}")
    if result.address_page:
        print_fn(f"Contract registry: {result.address_page}")
    for path in result.token_pages:
        print_fn(f"Token page: {path}")
    if coverage.categories["tokenomics"] != "collected":
        print_fn(
            "Registry is partial: token-source coverage is not collected, "
            "so an empty token list is not a conclusion that no token exists."
        )
    print_fn(f"Linked research pages: {len(result.linked_pages)}")
    return 0


def _market_data(
    workspace: ProjectWorkspace,
    *,
    force: bool,
    print_fn: PrintFunction,
) -> int:
    result = refresh_market_data(workspace=workspace, force=force)
    pages = refresh_token_pages_from_registry(workspace)
    available = sum(
        snapshot.status == "available" for snapshot in result.snapshots
    )
    unavailable = len(result.snapshots) - available
    print_fn(
        "Current token supply data: "
        f"{available} available; {unavailable} unavailable; "
        f"{result.refreshed} refreshed; {result.reused} cached"
    )
    for page in pages:
        print_fn(f"Token page: {page}")
    if unavailable:
        print_fn(
            "Unavailable supply entries remain visible and do not block "
            "other stages."
        )
    return 0


def _analyst_review(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    page: Path,
    section: ReviewSection,
    question: str,
    save: bool,
    print_fn: PrintFunction,
) -> int:
    settings = SettingsManager(manager.root).load()
    provider = create_provider(settings["llm"])
    result = run_analyst_review(
        workspace=workspace,
        provider=provider,
        page=page,
        section=section,
        question=question,
    )
    print_fn("")
    print_fn(f"Source: {page.name} > {section.title}")
    print_fn("Scope: selected section only")
    print_fn("")
    print_fn(result.answer)
    if save:
        result = save_analyst_review(
            workspace=workspace,
            result=result,
        )
        print_fn("")
        print_fn(f"Saved non-canonical review: {result.saved_path}")
    return 0


def _menu_analyst_review(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    pages = list_review_pages(workspace)
    if not pages:
        raise ValueError(
            "No generated research pages exist for this project."
        )
    print_fn("Research pages:")
    for index, page in enumerate(pages, start=1):
        print_fn(f"  {index}. {page.stem}")
    selected_page = _required(input_fn, "Page number: ")
    if not selected_page.isdigit() or not 1 <= int(selected_page) <= len(pages):
        raise ValueError("Invalid research page number.")
    page = pages[int(selected_page) - 1]

    sections = parse_review_sections(page)
    if not sections:
        raise ValueError(f"No Markdown headings were found in {page.name}.")
    print_fn(f"Sections in {page.stem}:")
    for index, section in enumerate(sections, start=1):
        indent = "  " * max(section.level - 1, 0)
        print_fn(f"  {index}. {indent}{section.title}")
    selected_section = _required(input_fn, "Section number: ")
    if (
        not selected_section.isdigit()
        or not 1 <= int(selected_section) <= len(sections)
    ):
        raise ValueError("Invalid section number.")
    section = sections[int(selected_section) - 1]
    question = _required(input_fn, "Question about this section: ")
    save = _yes_no(
        input_fn,
        "Save this AI explanation in the Obsidian vault? [y/N]: ",
    )
    _analyst_review(
        manager,
        workspace,
        page=page,
        section=section,
        question=question,
        save=save,
        print_fn=print_fn,
    )


def _source_command(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    action: str,
    category: str | None,
    url: str | None,
    refresh: bool,
    print_fn: PrintFunction,
) -> int:
    if action == "list":
        summary = ensure_source_coverage(workspace)
        print_fn(f"Overall source coverage: {summary.status}")
        for key in CATEGORIES:
            print_fn(
                f"- {CATEGORY_LABELS[key]}: {summary.categories[key]}"
            )
            for source in (
                item for item in summary.sources if item.category == key
            ):
                print_fn(
                    f"  {source.source_id}: {source.status} — {source.url}"
                )
        return 0

    if not category:
        raise ValueError("--category is required for source add or crawl.")
    if action == "add":
        if not url:
            raise ValueError("--url is required when adding a source.")
        source = add_official_source(
            workspace,
            category=category,
            url=url,
        )
        write_coverage_source(workspace)
        sync_research_coverage(workspace)
        print_fn(f"Official source registered: {source.source_id}")
        print_fn(
            "Run the source crawl action before this category is considered "
            "collected."
        )
        return 0

    sources = sources_for_category(workspace, category)
    if not sources:
        raise ValueError(
            f"No official sources are registered for category {category}."
        )
    failures = 0
    for source in sources:
        try:
            count = _crawl_official_source(
                workspace,
                source_id=source.source_id,
                category=source.category,
                url=source.url,
                refresh=refresh,
            )
            update_source_status(
                workspace,
                source_id=source.source_id,
                status="collected",
                detail=f"{count} Markdown pages collected",
            )
            print_fn(
                f"Collected {CATEGORY_LABELS[source.category]}: "
                f"{count} Markdown pages"
            )
        except Exception as exc:
            failures += 1
            update_source_status(
                workspace,
                source_id=source.source_id,
                status="failed",
                detail=str(exc),
            )
            print_fn(f"Source failed: {source.url} — {exc}")
    write_coverage_source(workspace)
    sync_research_coverage(workspace)
    summary = ensure_source_coverage(workspace)
    manager.update_stage(
        workspace,
        "crawl",
        "partial" if failures else "complete",
        detail=f"Official source coverage: {summary.status}",
    )
    print_fn(f"Overall source coverage: {summary.status}")
    return 2 if failures else 0


def _crawl_official_source(
    workspace: ProjectWorkspace,
    *,
    source_id: str,
    category: str,
    url: str,
    refresh: bool,
) -> int:
    from crawler.github_importer import (
        import_github_markdown,
        is_github_repository_url,
    )

    destination_root = (
        workspace.sources_directory / "_official" / category / source_id
    )
    if is_github_repository_url(url):
        result = import_github_markdown(
            protocol_name=workspace.name,
            repository_url=url,
            output_directory=destination_root,
            refresh=refresh,
        )
        return result.discovered

    try:
        from crawler.crawler import crawl_protocol
    except ImportError as exc:
        raise RuntimeError(
            "Crawler dependencies are unavailable. Run "
            "'pip install -r requirements.txt' and 'crawl4ai-setup'."
        ) from exc
    result = asyncio.run(
        crawl_protocol(
            protocol_name=source_id,
            docs_url=url,
            output_root=destination_root.parent,
            pattern=url,
            refresh=refresh,
            retries=DEFAULT_RETRIES,
        )
    )
    if result.failed:
        raise RuntimeError(
            f"{result.failed} official-source pages failed to crawl."
        )
    return result.saved + result.skipped


def _menu_sources(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    print_fn("1. View source coverage")
    print_fn("2. Add an official source")
    print_fn("3. Collect sources in a category")
    action = _required(input_fn, "Source option [1-3]: ")
    if action == "1":
        _source_command(
            manager,
            workspace,
            action="list",
            category=None,
            url=None,
            refresh=False,
            print_fn=print_fn,
        )
        return
    if action not in {"2", "3"}:
        raise ValueError("Please enter 1, 2, or 3.")
    print_fn("Source categories:")
    for index, key in enumerate(CATEGORIES, start=1):
        print_fn(f"  {index}. {CATEGORY_LABELS[key]} ({key})")
    selected = _required(input_fn, "Category name or number: ")
    if selected.isdigit() and 1 <= int(selected) <= len(CATEGORIES):
        selected = CATEGORIES[int(selected) - 1]
    if action == "2":
        url = _required(input_fn, "Official source URL: ")
        _source_command(
            manager,
            workspace,
            action="add",
            category=selected,
            url=url,
            refresh=False,
            print_fn=print_fn,
        )
        return
    _source_command(
        manager,
        workspace,
        action="crawl",
        category=selected,
        url=None,
        refresh=_yes_no(input_fn, "Refresh collected sources? [y/N]: "),
        print_fn=print_fn,
    )


def _verification_plan(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> int:
    settings = SettingsManager(manager.root).load()
    provider = create_provider(settings["llm"])
    try:
        result = generate_verification_plan(
            workspace=workspace,
            provider=provider,
            prompts_root=PROJECT_ROOT / "prompts",
            progress=print_fn,
        )
    except Exception as exc:
        manager.update_stage(
            workspace,
            "verification_plan",
            "blocked",
            detail=str(exc),
        )
        raise

    status = "complete"
    workspace = manager.update_stage(
        workspace,
        "verification_plan",
        status,
        detail=(
            f"{result.ready_requests} scanner-ready requests; "
            f"{result.manual_claims} manual-review claims"
        ),
    )
    links = insert_verification_links(
        verification_page=result.page_path,
        research_directory=workspace.vault_entity_directory,
    )
    workspace = manager.update_stage(
        workspace,
        "obsidian_links",
        "complete" if not links.unresolved_mappings else "partial",
        detail=(
            f"{links.inserted_links} verification links; "
            f"{len(links.unresolved_mappings)} unresolved mappings"
        ),
    )
    workspace = manager.set_verification_status(
        workspace,
        "pending" if result.ready_requests else "manual_review",
    )
    print_fn(f"Verification page: {result.page_path}")
    if result.job_path:
        print_fn(f"Collector job: {result.job_path}")
    else:
        print_fn("Collector job: none; material checks require manual review")
    print_fn(f"Import report: {result.report_path}")
    print_fn(
        f"Provider calls: {result.provider_calls}; "
        f"reused: {result.reused_calls}"
    )
    print_fn(
        f"Research links: {links.inserted_links}; "
        f"unresolved: {len(links.unresolved_mappings)}"
    )
    return 0 if result.job_path else 2


def _evaluate(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> int:
    settings = SettingsManager(manager.root).load()
    provider = create_provider(settings["llm"])
    result = generate_evaluation_proposals(
        workspace=workspace,
        provider=provider,
        progress=print_fn,
    )
    manager.update_stage(
        workspace,
        "evidence_evaluation",
        "pending" if result.proposals else "partial",
        detail=(
            f"{len(result.proposals)} proposals; "
            f"{len(result.unmatched_evidence)} unmatched evidence files"
        ),
    )
    print_fn(f"Evaluation proposals: {len(result.proposals)}")
    print_fn(f"Reused proposals: {result.reused}")
    print_fn(f"Unmatched evidence files: {len(result.unmatched_evidence)}")
    if result.proposals:
        print_fn("Review them with: python main.py review " + workspace.slug)
        return 0
    return 2


def _review(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> int:
    proposals = pending_proposals(workspace)
    if not proposals:
        refresh_verification_summary(
            workspace.vault_root
            / "Verification"
            / f"{workspace.name} - Verification.md"
        )
        print_fn("No pending evaluation proposals.")
        return 0
    print_fn("Pending evaluations:")
    documents = []
    for index, path in enumerate(proposals, start=1):
        document = json.loads(path.read_text(encoding="utf-8"))
        documents.append(document)
        print_fn(
            f"  {index}. {document['verification_id']} — "
            f"{document['proposed_status']}"
        )
    selected = _required(input_fn, "Proposal number: ")
    if not selected.isdigit() or not 1 <= int(selected) <= len(proposals):
        raise ValueError("Invalid proposal number.")
    index = int(selected) - 1
    document = documents[index]
    print_fn(f"Claim: {document['claim']}")
    print_fn(f"Proposed status: {document['proposed_status']}")
    print_fn(f"Reason: {document['reason']}")
    print_fn(f"Evidence scope: {document['evidence_scope']}")
    print_fn(f"Evidence: {document['evidence_file']}")
    print_fn("1. Approve")
    print_fn("2. Reject")
    print_fn("3. Change to inconclusive")
    print_fn("4. Leave pending")
    action_value = _required(input_fn, "Review action [1-4]: ")
    action = {
        "1": "approve",
        "2": "reject",
        "3": "inconclusive",
        "4": "leave",
    }.get(action_value)
    if action is None:
        raise ValueError("Invalid review action.")
    result = review_proposal(
        workspace=workspace,
        proposal_path=proposals[index],
        action=action,
    )
    remaining = pending_proposals(workspace)
    manager.update_stage(
        workspace,
        "evidence_evaluation",
        "complete" if not remaining else "pending",
        detail=f"{len(remaining)} pending human-review proposals",
    )
    print_fn(f"Review action recorded: {result.action}")
    print_fn(
        "Verification page updated."
        if result.verification_updated
        else "Verification page unchanged."
    )
    return 0


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


def _menu_crawl_pattern(
    input_fn: InputFunction,
    docs_url: str,
) -> str:
    from crawler.github_importer import is_github_repository_url

    if is_github_repository_url(docs_url):
        return DEFAULT_PATTERN
    return (
        input_fn(f"Sitemap pattern [{DEFAULT_PATTERN}]: ").strip()
        or DEFAULT_PATTERN
    )


def _menu_github_ref(
    input_fn: InputFunction,
    docs_url: str,
) -> str | None:
    from crawler.github_importer import is_github_repository_url

    if not is_github_repository_url(docs_url):
        return None
    return (
        input_fn(
            "Git branch, tag, or commit (leave blank for default branch): "
        ).strip()
        or None
    )


def _yes_no(input_fn: InputFunction, prompt: str) -> bool:
    value = input_fn(prompt).strip().lower()
    if not value:
        return False
    if value in {"y", "yes"}:
        return True
    if value in {"n", "no"}:
        return False
    raise ValueError("Expected yes or no.")
