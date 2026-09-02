"""One entry point for guided users, power users, and agents."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

from blockchain_collector.envfile import load_environment_file
from blockchain_collector.evidence import write_evidence_bundle
from blockchain_collector.executor import execute_collection_job
from blockchain_collector.jobs import load_collection_job
from blockchain_collector.menu import run_guided_menu as run_collector_menu
from blockchain_collector.rpc import SUPPORTED_CHAINS
from blockchain_collector.summary import write_evidence_summary

from .analyst_review import (
    ReviewSection,
    list_review_pages,
    parse_review_sections,
    select_review_page,
    select_review_section,
)
from .application import DefinalyzerApplication
from .dependencies import (
    bootstrap_legacy_research,
    json_fingerprint,
    record_research_page,
    research_pages_current,
    source_corpus_fingerprint,
    stale_research_pages,
)
from .dune_assistant import (
    restore_dune_dialogue_links,
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
    TokenRecord,
    project_tokens,
    registry_needs_token_discovery,
    refresh_token_pages_from_registry,
    run_registry_workflow,
    upsert_manual_token,
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
from .verification_state import (
    JOB_FINGERPRINT_KEY,
    evidence_job_fingerprint,
    verification_job_fingerprint,
)
from .workflow_status import (
    verification_status_label,
    workflow_status_document,
)
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
        help="Open the standalone advanced blockchain evidence collector.",
    )
    collect.add_argument("project")
    collect.add_argument(
        "--planned",
        action="store_true",
        help="Run this project's scanner-ready verification checklist.",
    )

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
        help="Ask Hermes a question across project research.",
    )
    ask.add_argument("project")
    ask.add_argument(
        "--page",
        help="Optional Markdown page name or stem; use with --heading.",
    )
    ask.add_argument(
        "--heading",
        help="Optional exact heading used with --page to restrict the search.",
    )
    ask.add_argument("--question", required=True)
    ask.add_argument(
        "--deep",
        action="store_true",
        help="Also search locally collected raw documentation.",
    )
    ask.add_argument(
        "--save",
        action="store_true",
        help="Save the non-canonical answer under Analyst Reviews.",
    )

    dune = subparsers.add_parser(
        "dune",
        help="Draft or revise an optional Dune query for one eligible check.",
    )
    dune.add_argument("project")
    dune.add_argument("verification_id")
    dune.add_argument(
        "--feedback-type",
        choices=("error", "result", "context"),
        help="Continue an existing dialogue with pasted Dune feedback.",
    )
    dune.add_argument(
        "--feedback",
        help="Exact Dune error, result summary/link, or additional context.",
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
        "analyze",
        aliases=("all",),
        help="Run or resume the complete project analysis (`all` also works).",
    )
    complete.add_argument("project")
    complete.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh sources and replace all generated research pages.",
    )

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Open the local browser dashboard.",
    )
    dashboard.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port (default: select an available port).",
    )
    dashboard.add_argument(
        "--no-open",
        action="store_true",
        help="Print the local URL without opening the default browser.",
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
    application = DefinalyzerApplication(manager)

    try:
        if args.command is None:
            return run_menu(manager, input_fn=input_fn, print_fn=print_fn)
        if args.command == "dashboard":
            from .dashboard import run_dashboard

            return run_dashboard(
                manager,
                port=args.port,
                open_browser=not args.no_open,
                print_fn=print_fn,
            )
        if args.command == "init":
            workspace = application.create_project(
                name=args.name,
                entity_type=args.type,
                docs_url=args.docs_url,
                verification_status=args.verification,
            )
            _print_created(workspace, print_fn)
            return 0
        if args.command == "crawl":
            workspace = application.load_project(args.project)
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
            workspace = application.load_project(args.project)
            if args.planned:
                if not _workflow_prerequisites_ready(
                    workspace,
                    step="evidence_collection",
                    print_fn=print_fn,
                ):
                    return 2
                return (
                    0
                    if _collect_planned_verification(
                        manager,
                        workspace,
                        job_path=(
                            workspace.jobs_directory
                            / "verification-plan.json"
                        ),
                        print_fn=print_fn,
                    )
                    else 2
                )
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
            workspace = application.load_project(args.project)
            if not _workflow_prerequisites_ready(
                workspace,
                step="research_page",
                print_fn=print_fn,
            ):
                return 2
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
            workspace = application.load_project(args.project)
            if not _workflow_prerequisites_ready(
                workspace,
                step="registry",
                print_fn=print_fn,
            ):
                return 2
            return _registry(manager, workspace, print_fn)
        if args.command == "market-data":
            workspace = application.load_project(args.project)
            return _market_data(
                workspace,
                force=args.refresh,
                print_fn=print_fn,
            )
        if args.command == "ask":
            workspace = application.load_project(args.project)
            if bool(args.page) != bool(args.heading):
                raise ValueError("--page and --heading must be supplied together.")
            page = select_review_page(workspace, args.page) if args.page else None
            section = (
                select_review_section(page, args.heading)
                if page is not None
                else None
            )
            return _analyst_review(
                manager,
                workspace,
                page=page,
                section=section,
                question=args.question,
                deep=args.deep,
                save=args.save,
                print_fn=print_fn,
            )
        if args.command == "dune":
            workspace = application.load_project(args.project)
            if bool(args.feedback_type) != bool(args.feedback):
                raise ValueError(
                    "--feedback-type and --feedback must be supplied together."
                )
            return _dune_assistant(
                manager,
                workspace,
                verification_id=args.verification_id,
                feedback_type=args.feedback_type,
                feedback=args.feedback,
                print_fn=print_fn,
            )
        if args.command == "source":
            workspace = application.load_project(args.project)
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
            workspace = application.load_project(args.project)
            if not _workflow_prerequisites_ready(
                workspace,
                step="verification_plan",
                print_fn=print_fn,
            ):
                return 2
            return _verification_plan(manager, workspace, print_fn)
        if args.command == "evaluate":
            workspace = application.load_project(args.project)
            if not _workflow_prerequisites_ready(
                workspace,
                step="evidence_evaluation",
                print_fn=print_fn,
            ):
                return 2
            return _evaluate(manager, workspace, print_fn)
        if args.command == "review":
            workspace = application.load_project(args.project)
            if not _workflow_prerequisites_ready(
                workspace,
                step="review",
                print_fn=print_fn,
            ):
                return 2
            return _review(
                manager,
                workspace,
                input_fn=input_fn,
                print_fn=print_fn,
            )
        if args.command in {"analyze", "all"}:
            workspace = application.load_project(args.project)
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
    application = DefinalyzerApplication(manager)
    application.initialize()

    while True:
        print_fn("")
        print_fn("DEFINALYZER")
        print_fn("")
        print_fn("RESEARCH WORKFLOW")
        print_fn("1. Set up a new project (setup only)")
        print_fn("2. Analyze a project (complete research workflow)")
        print_fn("")
        print_fn("INDIVIDUAL RESEARCH STEPS")
        print_fn("3. Crawl or update documentation")
        print_fn("4. Generate research pages")
        print_fn("5. Generate registry and token data")
        print_fn("6. Generate verification checklist")
        print_fn("")
        print_fn("VERIFICATION WORKFLOW")
        print_fn("7. Collect blockchain evidence")
        print_fn("8. Generate evidence assessment proposals")
        print_fn("9. Review and approve assessments")
        print_fn("10. Draft or revise an optional Dune query")
        print_fn("")
        print_fn("RESEARCH TOOLS AND SETTINGS")
        print_fn("11. Configure or test AI provider")
        print_fn("12. View project status")
        print_fn("13. Refresh current token supply data")
        print_fn("14. Ask a question about project research")
        print_fn("15. Manage official sources")
        print_fn("16. Add or update a token manually")
        print_fn("17. Refresh Obsidian vault indexes")
        print_fn("18. Delete a project and its generated data")
        print_fn("")
        print_fn("ADVANCED TOOLS")
        print_fn("19. Open standalone evidence collector (advanced)")
        print_fn("20. Open local dashboard")
        print_fn("21. Exit")
        choice = input_fn("Choice [1-21]: ").strip()

        try:
            if choice == "1":
                workspace = _menu_create(manager, input_fn, print_fn)
                if _yes_no(
                    input_fn,
                    "Run the complete research analysis now? [y/N]: ",
                ):
                    code = _complete_workflow(
                        manager,
                        workspace,
                        refresh=False,
                        print_fn=print_fn,
                    )
                    if code == 0:
                        _guided_post_analysis(
                            manager,
                            workspace,
                            input_fn=input_fn,
                            print_fn=print_fn,
                        )
            elif choice == "2":
                workspace = _menu_project(manager, input_fn, print_fn)
                code = _complete_workflow(
                    manager,
                    workspace,
                    refresh=_yes_no(
                        input_fn,
                        "Refresh sources and existing research pages? [y/N]: ",
                    ),
                    print_fn=print_fn,
                )
                if code == 0:
                    _guided_post_analysis(
                        manager,
                        workspace,
                        input_fn=input_fn,
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
                if not _menu_prerequisites_ready(
                    workspace, choice="4", print_fn=print_fn
                ):
                    continue
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
                    if _menu_prerequisites_ready(
                        workspace, choice="5", print_fn=print_fn
                    ):
                        _registry(manager, workspace, print_fn)
                else:
                    if _menu_prerequisites_ready(
                        workspace, choice="6", print_fn=print_fn
                    ):
                        _verification_plan(manager, workspace, print_fn)
            elif choice == "7":
                workspace = _menu_project(manager, input_fn, print_fn)
                if _menu_prerequisites_ready(
                    workspace, choice="7", print_fn=print_fn
                ):
                    if _yes_no(
                        input_fn,
                        "Collect this project's scanner-ready evidence now? "
                        "[y/N]: ",
                    ):
                        ready = _collect_planned_verification(
                            manager,
                            workspace,
                            job_path=(
                                workspace.jobs_directory
                                / "verification-plan.json"
                            ),
                            print_fn=print_fn,
                        )
                        if not ready:
                            print_fn(
                                "Planned evidence remains incomplete. Check "
                                "the reported RPC errors before retrying."
                            )
                    else:
                        print_fn("Planned evidence collection was not started.")
            elif choice == "8":
                workspace = _menu_project(manager, input_fn, print_fn)
                if _menu_prerequisites_ready(
                    workspace, choice="8", print_fn=print_fn
                ):
                    _evaluate(manager, workspace, print_fn)
            elif choice == "9":
                workspace = _menu_project(manager, input_fn, print_fn)
                if _menu_prerequisites_ready(
                    workspace, choice="9", print_fn=print_fn
                ):
                    _review(
                        manager,
                        workspace,
                        input_fn=input_fn,
                        print_fn=print_fn,
                    )
            elif choice == "10":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_dune_assistant(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "11":
                _menu_provider(manager, input_fn, print_fn)
            elif choice == "12":
                name = input_fn(
                    "Project name (leave blank to list all): "
                ).strip()
                _show_status(manager, name or None, print_fn)
            elif choice == "13":
                workspace = _menu_project(manager, input_fn, print_fn)
                _market_data(
                    workspace,
                    force=_yes_no(
                        input_fn,
                        "Ignore supply data cached within the last day? [y/N]: ",
                    ),
                    print_fn=print_fn,
                )
            elif choice == "14":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_analyst_review(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "15":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_sources(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "16":
                workspace = _menu_project(manager, input_fn, print_fn)
                _menu_manual_token(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "17":
                paths = application.refresh_indexes()
                print_fn(f"Refreshed {len(paths)} vault indexes.")
                for path in paths:
                    print_fn(f"Index: {path}")
            elif choice == "18":
                _menu_delete_project(
                    manager,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "19":
                workspace = _menu_project(manager, input_fn, print_fn)
                _collect(
                    manager,
                    workspace,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
            elif choice == "20":
                from .dashboard import run_dashboard

                run_dashboard(manager, print_fn=print_fn)
            elif choice == "21":
                print_fn("Goodbye.")
                return 0
            else:
                print_fn("Please enter a number from 1 to 21.")
        except (OSError, RuntimeError, ValueError) as exc:
            print_fn(f"Stopped: {exc}")


def _menu_create(
    manager: WorkspaceManager,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    name = _required(input_fn, "Project name: ")
    print_fn("Entity type:")
    print_fn("  1. Protocol (default)")
    print_fn("  2. Chain")
    print_fn("  3. Token")
    entity_choice = input_fn("Entity type [1-3] (1): ").strip()
    entity_value = {
        "": "protocol",
        "1": "protocol",
        "2": "chain",
        "3": "token",
    }.get(entity_choice)
    if entity_value is None:
        raise ValueError("Entity type must be 1, 2, or 3.")
    print_fn(
        "Use the URL for the exact protocol or product documentation section. "
        "An umbrella homepage may combine separate products into one analysis."
    )
    docs_url = input_fn("Documentation URL (optional): ").strip() or None
    verification = _yes_no(
        input_fn,
        "Plan blockchain verification later? [y/N]: ",
    )
    workspace = DefinalyzerApplication(manager).create_project(
        name=name,
        entity_type=entity_value,
        docs_url=docs_url,
        verification_status="pending" if verification else "not_requested",
    )
    _print_created(workspace, print_fn)
    return workspace


def _menu_delete_project(
    manager: WorkspaceManager,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    workspace = _menu_project(manager, input_fn, print_fn)
    print_fn("")
    print_fn(f"Permanently delete project: {workspace.name}")
    print_fn(f"- Project state, jobs, and evidence: {workspace.project_root}")
    print_fn(f"- Collected documentation: {workspace.sources_directory}")
    print_fn(f"- Registry data: {workspace.registry_directory}")
    print_fn(f"- Research notes: {workspace.vault_entity_directory}")
    print_fn(f"- Verification notes: {workspace.verification_directory}")
    print_fn(
        "- Analyst reviews and token pages used only by this project will "
        "also be removed."
    )
    confirmation = input_fn(
        f'Type the exact project name "{workspace.name}" to delete it: '
    ).strip()
    if confirmation != workspace.name:
        print_fn("Deletion cancelled; the project name did not match.")
        return

    removed = DefinalyzerApplication(manager).delete_project(workspace.slug)
    print_fn(f"Deleted project {workspace.name}.")
    print_fn(f"Removed {len(removed)} generated folders.")
    print_fn("Obsidian vault indexes were refreshed.")


def _guided_post_analysis(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    """Offer safe continuation steps after a newly created project's analysis."""

    workspace = manager.load_project(workspace.slug)
    print_fn("")
    print_fn(f"Research analysis complete for {workspace.name}.")

    verification_status = str(
        workspace.document.get("verification_status", "not_requested")
    )
    if verification_status == "not_requested":
        print_fn(
            "Blockchain verification was not requested. Research is ready "
            "for use; verification can be enabled or run separately later."
        )
        return
    if verification_status == "unsupported":
        print_fn(
            "This project is configured as unsupported for automated "
            "verification. Its research remains usable."
        )
        return

    _print_supported_collector_chains(print_fn)
    job_path = workspace.jobs_directory / "verification-plan.json"
    if not job_path.exists():
        print_fn(
            "No scanner-ready requests were created. Verification entries "
            "remain categorized for manual analyst review."
        )
        return

    job = load_collection_job(job_path)
    planned_chains = sorted(dict.fromkeys(request.chain for request in job.requests))
    print_fn(
        f"Scanner-ready requests: {len(job.requests)} across "
        f"{', '.join(planned_chains)}."
    )
    if not _yes_no(
        input_fn,
        "Collect scanner-ready blockchain evidence now? [y/N]: ",
    ):
        print_fn("Evidence collection remains available as menu option 7.")
        return

    evidence_ready = _collect_planned_verification(
        manager,
        workspace,
        job_path=job_path,
        print_fn=print_fn,
    )
    if not evidence_ready:
        return
    if not _yes_no(
        input_fn,
        "Generate evidence assessment proposals now? [y/N]: ",
    ):
        print_fn("Assessment generation remains available as menu option 8.")
        return
    if _evaluate(manager, workspace, print_fn) != 0:
        print_fn("No reviewable assessment proposals were generated.")
        return
    if pending_proposals(workspace):
        print_fn(
            "Evidence assessment proposals are ready for optional human "
            "review. Research and automated collection are complete; use "
            "menu option 9 when you intentionally want to approve or reject "
            "them."
        )


def _print_supported_collector_chains(print_fn: PrintFunction) -> None:
    print_fn("")
    print_fn("Automated blockchain evidence collection currently supports:")
    for configuration in SUPPORTED_CHAINS.values():
        print_fn(f"- {configuration.name} (chain ID {configuration.chain_id})")
    print_fn(
        "Other networks and off-chain claims remain visible as manual "
        "verification tasks; they are not treated as disproven."
    )


def _collect_planned_verification(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    job_path: Path,
    print_fn: PrintFunction,
) -> bool:
    """Execute the scanner-ready job produced by verification planning."""

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_environment_file(env_path)
    job = load_collection_job(job_path)
    fingerprint = verification_job_fingerprint(job_path)
    suffix = fingerprint[:12]
    evidence_path = workspace.evidence_directory / f"{job.name}-{suffix}.json"
    summary_path = workspace.evidence_directory / f"{job.name}-{suffix}.md"
    if evidence_path.exists() and summary_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise ValueError(f"Evidence bundle is not a JSON object: {evidence_path}")
        if evidence_job_fingerprint(existing) != fingerprint:
            raise ValueError(
                "Existing planned evidence does not match the current "
                f"verification job: {evidence_path}"
            )
        print_fn(f"Reusing existing evidence: {evidence_path}")
        records = existing.get("records", [])
        if not isinstance(records, list):
            raise ValueError(f"Evidence records are invalid: {evidence_path}")
        statuses = [
            record.get("status")
            for record in records
            if isinstance(record, dict)
        ]
        if len(statuses) != len(records) or any(
            status not in {"collected", "partial", "failed"}
            for status in statuses
        ):
            raise ValueError(f"Evidence record statuses are invalid: {evidence_path}")
        collected = statuses.count("collected")
        partial = statuses.count("partial")
        failed = statuses.count("failed")
        expected = {request.name for request in job.requests}
        present = {
            str(record.get("request_name"))
            for record in records
            if isinstance(record, dict)
        }
        if present != expected:
            raise ValueError(
                "Existing evidence does not cover exactly the current planned "
                "verification requests."
            )
        stage_status = "complete" if not partial and not failed else "partial"
        workspace = manager.update_stage(
            workspace,
            "evidence_collection",
            stage_status,
            detail=f"{collected} collected; {partial} partial; {failed} failed",
        )
        if stage_status == "complete":
            manager.set_verification_status(workspace, "evidence_collected")
        return bool(collected or partial)
    if evidence_path.exists() or summary_path.exists():
        raise FileExistsError(
            "Planned evidence output is incomplete; refusing to overwrite "
            f"existing files under {workspace.evidence_directory}."
        )

    execution_job = replace(
        job,
        metadata={**job.metadata, JOB_FINGERPRINT_KEY: fingerprint},
    )
    bundle = execute_collection_job(execution_job, job_source=str(job_path))
    write_evidence_bundle(bundle, evidence_path)
    write_evidence_summary(bundle, summary_path)
    collected = sum(record.status == "collected" for record in bundle.records)
    partial = sum(record.status == "partial" for record in bundle.records)
    failed = sum(record.status == "failed" for record in bundle.records)
    expected = {request.name for request in job.requests}
    present = {record.request_name for record in bundle.records}
    fully_covered = present == expected
    stage_complete = fully_covered and not partial and not failed
    workspace = manager.update_stage(
        workspace,
        "evidence_collection",
        "complete" if stage_complete else "partial",
        detail=(
            f"{collected} collected; {partial} partial; {failed} failed; "
            f"{len(present & expected)}/{len(expected)} planned requests covered"
        ),
    )
    if stage_complete:
        manager.set_verification_status(workspace, "evidence_collected")
    print_fn(f"Evidence: {evidence_path}")
    print_fn(f"Evidence summary: {summary_path}")
    print_fn(f"Collected: {collected}; partial: {partial}; failed: {failed}")
    if failed and not collected and not partial:
        print_fn(
            "All scanner-ready requests failed, so assessment generation "
            "was not offered. Check RPC configuration and retry option 7."
        )
        return False
    return bool(collected or partial)


def _menu_project(
    manager: WorkspaceManager,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    application = DefinalyzerApplication(manager)
    projects = application.list_projects()

    if not projects:
        raise ValueError("No projects exist. Create a project first.")

    print_fn("Projects:")
    for index, project in enumerate(projects, start=1):
        print_fn(f"  {index}. {project.name} ({project.slug})")

    value = _required(input_fn, "Project name or number: ")
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(projects):
            return application.load_project(projects[index - 1].slug)
    return application.load_project(value)


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

    source_fingerprint_before = source_corpus_fingerprint(workspace)
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
    workspace = manager.update_stage(
        workspace,
        "crawl",
        status,
        detail=(
            f"{summary.saved} saved, {summary.skipped} skipped, "
            f"{summary.failed} failed"
        ),
    )
    _invalidate_after_source_change(
        manager,
        workspace,
        previous_fingerprint=source_fingerprint_before,
        print_fn=print_fn,
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
    print_fn(
        "Opening the standalone advanced evidence collector. Its result will be saved "
        "to this project, but it will not mark the planned verification "
        "checklist complete."
    )
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_environment_file(env_path)
    exit_code = run_collector_menu(
        input_fn=input_fn,
        print_fn=print_fn,
        working_directory=workspace.project_root,
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
        print_fn(
            f"Reference material retained locally but excluded from AI: "
            f"{plan.excluded_source_files} files, "
            f"{plan.excluded_source_characters:,} characters"
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

    record_research_page(
        workspace,
        template_name=template_name,
        prompts_root=PROJECT_ROOT / "prompts",
    )
    missing_pages = [
        filename
        for filename in OUTPUT_FILES.values()
        if not (workspace.vault_entity_directory / filename).exists()
    ]
    current_pages = research_pages_current(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    )
    research_status = "complete" if current_pages else "partial"
    detail = (
        "Generated all current research pages"
        if current_pages
        else (
            f"Generated {result.template}: {result.output_path.name}; "
            f"{len(missing_pages)} pages missing or other pages require refresh"
        )
    )
    workspace = manager.update_stage(
        workspace,
        "research",
        research_status,
        detail=detail,
    )
    _invalidate_after_research_change(manager, workspace)
    _record_extraction_usage(workspace, result)
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
    print_fn(
        "Reference material retained locally but excluded from AI: "
        f"{result.excluded_source_files} files, "
        f"{result.excluded_source_characters:,} characters"
    )
    print_fn(
        "Approximate provider input: "
        f"{result.provider_input_characters:,} characters"
    )
    return 0


def _record_extraction_usage(workspace, result) -> Path:
    """Persist provider-call accounting without relying on provider billing."""

    path = workspace.project_root / "extraction" / "usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": 1, "runs": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("runs"), list):
                document = loaded
        except (json.JSONDecodeError, OSError):
            pass
    document["runs"].append(
        {
            "completed_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "template": result.template,
            "mode": result.mode,
            "provider": result.provider,
            "selected_source_files": result.source_files,
            "selected_source_characters": result.source_characters,
            "excluded_source_files": result.excluded_source_files,
            "excluded_source_characters": result.excluded_source_characters,
            "provider_calls": result.provider_calls,
            "reused_calls": result.reused_calls,
            "approximate_provider_input_characters": (
                result.provider_input_characters
            ),
        }
    )
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
    return path


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

    with _project_workflow_lock(workspace):
        return _run_complete_workflow(
            manager,
            workspace,
            refresh=refresh,
            print_fn=print_fn,
        )


def _run_complete_workflow(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    refresh: bool,
    print_fn: PrintFunction,
) -> int:
    """Internal implementation protected by the per-project run lock."""

    print_fn(f"Analyze Project: {workspace.name}")
    print_fn("Existing generated outputs will be reused." if not refresh else
             "Refresh enabled: sources and generated research will be rebuilt.")

    source_pages = _collected_source_pages(workspace)
    primary_pages = _collected_primary_source_pages(workspace)
    docs_url = workspace.document.get("docs_url")
    crawl_status = str(
        workspace.document.get("stages", {})
        .get("crawl", {})
        .get("status", "not_started")
    )
    should_crawl = refresh or bool(
        docs_url
        and (
            not primary_pages
            or crawl_status in {"partial", "blocked", "pending"}
        )
    )
    if should_crawl:
        if not docs_url:
            raise ValueError(
                "Project analysis needs a documentation URL or existing "
                "collected source pages."
            )
        print_fn("")
        print_fn("[1/5] Collecting primary documentation")
        crawl_code = _crawl(
            manager,
            workspace,
            docs_url=str(docs_url),
            pattern=_default_crawl_pattern(str(docs_url)),
            refresh=refresh,
            retries=DEFAULT_RETRIES,
            print_fn=print_fn,
        )
        if crawl_code:
            raise RuntimeError(
                "Primary documentation collection did not complete. Fix the "
                "reported crawl failures, then rerun Analyze Project."
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
    # A project created before dependency tracking may already have the full
    # research set even if its old manifest did not record the stage cleanly.
    bootstrap_legacy_research(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    )
    stale_research = set(stale_research_pages(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    ))
    generated = 0
    reused = 0
    for template_name, filename in OUTPUT_FILES.items():
        output_path = workspace.vault_entity_directory / filename
        if (
            output_path.exists()
            and not refresh
            and template_name not in stale_research
        ):
            reused += 1
            print_fn(f"Reused research page: {filename}")
            continue
        _extract(
            manager,
            workspace,
            template_name=template_name,
            mode="auto",
            refresh=output_path.exists(),
            print_fn=print_fn,
        )
        generated += 1
        workspace = manager.load_project(workspace.slug)
    workspace = manager.load_project(workspace.slug)
    if not research_pages_current(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    ):
        raise RuntimeError(
            "Research generation finished without bringing every page up to "
            "the current source and prompt fingerprint."
        )
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
    print_fn("Project analysis finished.")
    try:
        indexes = manager.refresh_vault_indexes()
        print_fn(f"Refreshed {len(indexes)} Obsidian vault indexes.")
    except (OSError, ValueError) as exc:
        print_fn(
            "Research completed, but vault navigation indexes could not be "
            f"refreshed: {exc}"
        )
    print_fn(f"Obsidian vault: {workspace.vault_root}")
    return 0


@contextmanager
def _project_workflow_lock(workspace: ProjectWorkspace):
    """Prevent two complete workflows from writing one project concurrently."""
    lock_path = workspace.project_root / ".complete-workflow.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    if lock_path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as exc:
        handle.close()
        raise RuntimeError(
            f"A project analysis is already running for {workspace.name}. "
            "Wait for it to finish before starting another."
        ) from exc
    try:
        yield
    finally:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


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
    registry_fingerprint_before = json_fingerprint(
        registry_path,
        ignored_keys=("generated_at",),
    )
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
    workspace = manager.update_stage(
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
    _invalidate_after_registry_change(
        manager,
        workspace,
        previous_fingerprint=registry_fingerprint_before,
        print_fn=print_fn,
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


def _menu_manual_token(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    """Create or revise one sourced protocol/chain token without AI."""
    existing = project_tokens(workspace)
    if existing:
        print_fn("Current token records:")
        for row in existing:
            print_fn(f"  {row.symbol}: {row.name}")
    else:
        print_fn("No token records exist yet.")

    symbol = _required(input_fn, "Token symbol: ").upper()
    current = next(
        (row for row in existing if row.symbol.casefold() == symbol.casefold()),
        None,
    )

    def field(label: str, attribute: str, default: str) -> str:
        prior = getattr(current, attribute) if current else default
        value = input_fn(f"{label} [{prior}]: ").strip()
        return value or prior

    token = TokenRecord(
        name=field("Token name", "name", symbol),
        symbol=symbol,
        token_type=field("Type", "token_type", "Not documented"),
        protocol_relationship=field(
            "Relationship to project",
            "protocol_relationship",
            "Not documented",
        ),
        network=field("Network", "network", "Not documented"),
        standard=field("Token standard", "standard", "Not documented"),
        address=field("Contract address or mint", "address", "Not documented"),
        # Current supply statistics are intentionally owned by the separate,
        # deterministic market-data refresh rather than manual or AI entry.
        supply="Not documented",
        maximum_supply="Not documented",
        circulating_supply="Not documented",
        emissions=field("Emissions", "emissions", "Not documented"),
        allocation=field("Allocation", "allocation", "Not documented"),
        unlocks=field("Vesting/unlocks", "unlocks", "Not documented"),
        mint_authority=field(
            "Mint authority or issuance control",
            "mint_authority",
            "Not documented",
        ),
        utility=field("Utility/value rights", "utility", "Not documented"),
        source=field("Official source URL or source note", "source", ""),
    )
    registry_path = workspace.registry_directory / "registry.json"
    registry_fingerprint_before = json_fingerprint(
        registry_path,
        ignored_keys=("generated_at",),
    )
    result = upsert_manual_token(workspace=workspace, token=token)
    _invalidate_after_registry_change(
        manager,
        workspace,
        previous_fingerprint=registry_fingerprint_before,
        print_fn=print_fn,
    )
    print_fn(f"Saved token {token.symbol} in {result.registry_path}")
    for page in result.token_pages:
        if page.parent.name.casefold() == token.symbol.casefold():
            print_fn(f"Token page: {page}")

    if token.address.casefold() != "not documented" and _yes_no(
        input_fn,
        "Refresh CoinGecko supply data now? [y/N]: ",
    ):
        _market_data(workspace, force=True, print_fn=print_fn)


def _market_data(
    workspace: ProjectWorkspace,
    *,
    force: bool,
    print_fn: PrintFunction,
) -> int:
    application = DefinalyzerApplication(WorkspaceManager(workspace.root))
    service_result = application.refresh_market_data(
        workspace=workspace,
        force=force,
    )
    result = service_result.refresh
    pages = service_result.token_pages
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
    page: Path | None,
    section: ReviewSection | None,
    question: str,
    deep: bool,
    save: bool,
    print_fn: PrintFunction,
) -> int:
    application = DefinalyzerApplication(
        manager,
        provider_factory=create_provider,
    )
    result = application.ask(
        workspace=workspace,
        page=page,
        section=section,
        question=question,
        deep=deep,
        save=save,
    )
    print_fn("")
    print_fn(f"Scope: {result.scope}")
    print_fn(f"Retrieved passages: {len(result.passages)}")
    for passage in result.passages:
        print_fn(
            f"- {passage.display_path} > {passage.heading} "
            f"({passage.source_type})"
        )
    print_fn("")
    print_fn(result.answer)
    if result.saved_path is not None:
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
        raise ValueError("No generated research pages exist for this project.")
    question = _required(input_fn, "Question about this project: ")
    deep = _yes_no(
        input_fn,
        "Deep search collected source documentation too? [y/N]: ",
    )
    page = None
    section = None
    if _yes_no(
        input_fn,
        "Restrict this question to one page and heading? [y/N]: ",
    ):
        print_fn("Research pages:")
        for index, candidate in enumerate(pages, start=1):
            print_fn(f"  {index}. {candidate.stem}")
        selected_page = _required(input_fn, "Page number: ")
        if not selected_page.isdigit() or not 1 <= int(selected_page) <= len(pages):
            raise ValueError("Invalid research page number.")
        page = pages[int(selected_page) - 1]
        sections = parse_review_sections(page)
        if not sections:
            raise ValueError(f"No populated Markdown headings were found in {page.name}.")
        print_fn(f"Populated sections in {page.stem}:")
        for index, candidate in enumerate(sections, start=1):
            indent = "  " * max(candidate.level - 1, 0)
            print_fn(f"  {index}. {indent}{candidate.title}")
        selected_section = _required(input_fn, "Section number: ")
        if (
            not selected_section.isdigit()
            or not 1 <= int(selected_section) <= len(sections)
        ):
            raise ValueError("Invalid section number.")
        section = sections[int(selected_section) - 1]
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
        deep=deep,
        save=save,
        print_fn=print_fn,
    )


def _dune_assistant(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    verification_id: str,
    feedback_type: str | None,
    feedback: str | None,
    print_fn: PrintFunction,
) -> int:
    application = DefinalyzerApplication(
        manager,
        provider_factory=create_provider,
    )
    result = application.dune_dialogue(
        workspace=workspace,
        verification_id=verification_id,
        feedback_type=feedback_type,
        feedback=feedback,
    )
    print_fn("")
    print_fn(
        f"Dune query draft {result.candidate.verification_id}, "
        f"version {result.version}"
    )
    print_fn("")
    print_fn(result.response)
    print_fn("")
    print_fn("This query was not executed and no verification status changed.")
    print_fn(f"Dialogue note: {result.note_path}")
    return 0


def _menu_dune_assistant(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    input_fn: InputFunction,
    print_fn: PrintFunction,
) -> None:
    candidates = DefinalyzerApplication(manager).dune_candidates(workspace)
    if not candidates:
        raise ValueError(
            "This checklist has no checks marked as optional Dune candidates."
        )
    print_fn("Optional Dune query candidates:")
    for index, candidate in enumerate(candidates, start=1):
        print_fn(
            f"  {index}. {candidate.verification_id} - "
            f"{candidate.title or candidate.claim}"
        )
    selected = _required(input_fn, "Verification number: ")
    if not selected.isdigit() or not 1 <= int(selected) <= len(candidates):
        raise ValueError("Invalid Dune verification number.")
    candidate = candidates[int(selected) - 1]

    while True:
        session = (
            workspace.project_root
            / "dune-assistant"
            / f"{candidate.verification_id.lower()}.json"
        )
        if not session.exists():
            feedback_type = None
            feedback = None
        else:
            print_fn("")
            print_fn("Continue the saved Dune dialogue:")
            print_fn("  1. Paste a Dune error and revise the query")
            print_fn("  2. Add context and revise the query")
            print_fn("  3. Paste a result or result link and check query coverage")
            print_fn("  4. Return to the main menu")
            action = _required(input_fn, "Dune dialogue option [1-4]: ")
            if action == "4":
                return
            feedback_type = {
                "1": "error",
                "2": "context",
                "3": "result",
            }.get(action)
            if feedback_type is None:
                raise ValueError("Invalid Dune dialogue option.")
            feedback = _required(
                input_fn,
                "Paste the exact error, context, result, or result link: ",
            )
        _dune_assistant(
            manager,
            workspace,
            verification_id=candidate.verification_id,
            feedback_type=feedback_type,
            feedback=feedback,
            print_fn=print_fn,
        )
        if not _yes_no(input_fn, "Continue this Dune dialogue now? [y/N]: "):
            return


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
                    f"  {source.source_id}: {source.status} - {source.url}"
                )
        return 0

    if not category:
        raise ValueError("--category is required for source add or crawl.")
    if action == "add":
        if not url:
            raise ValueError("--url is required when adding a source.")
        source_fingerprint_before = source_corpus_fingerprint(workspace)
        source = add_official_source(
            workspace,
            category=category,
            url=url,
        )
        write_coverage_source(workspace)
        sync_research_coverage(workspace)
        _invalidate_after_source_change(
            manager,
            workspace,
            previous_fingerprint=source_fingerprint_before,
            print_fn=print_fn,
        )
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
    source_fingerprint_before = source_corpus_fingerprint(workspace)
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
            print_fn(f"Source failed: {source.url} - {exc}")
    write_coverage_source(workspace)
    sync_research_coverage(workspace)
    summary = ensure_source_coverage(workspace)
    workspace = manager.update_stage(
        workspace,
        "crawl",
        "partial" if failures else "complete",
        detail=f"Official source coverage: {summary.status}",
    )
    _invalidate_after_source_change(
        manager,
        workspace,
        previous_fingerprint=source_fingerprint_before,
        print_fn=print_fn,
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
    planned_job_path = workspace.jobs_directory / "verification-plan.json"
    previous_job_fingerprint = (
        verification_job_fingerprint(planned_job_path)
        if planned_job_path.exists()
        else None
    )
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
            f"{result.manual_claims} analyst-routed claims"
        ),
    )
    current_job_fingerprint = (
        verification_job_fingerprint(result.job_path)
        if result.job_path
        else None
    )
    workspace = _invalidate_after_verification_job_change(
        manager,
        workspace,
        previous_fingerprint=previous_job_fingerprint,
        current_fingerprint=current_job_fingerprint,
        print_fn=print_fn,
    )
    links = insert_verification_links(
        verification_page=result.page_path,
        research_directory=workspace.vault_entity_directory,
    )
    restored_dune = restore_dune_dialogue_links(workspace)
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
    print_fn(f"Verification catalog: {result.catalog_path}")
    if restored_dune:
        print_fn(f"Restored Dune dialogue links: {len(restored_dune)}")
    print_fn(
        f"Provider calls: {result.provider_calls}; "
        f"reused: {result.reused_calls}"
    )
    print_fn(
        f"Research links: {links.inserted_links}; "
        f"unresolved: {len(links.unresolved_mappings)}"
    )
    # A manual-only checklist is a successful planning outcome, not an error.
    return 0


def _evaluate(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    print_fn: PrintFunction,
) -> int:
    # A preceding guided collection step may have updated the manifest. Reload
    # it before recording evaluation state so those newer stage results are not
    # overwritten by the older in-memory workspace document.
    workspace = manager.load_project(workspace.slug)
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
            f"{len(result.unmatched_evidence)} unmatched evidence files; "
            f"{len(result.ignored_stale_evidence)} stale evidence files ignored"
        ),
    )
    print_fn(f"Evaluation proposals: {len(result.proposals)}")
    print_fn(f"Reused proposals: {result.reused}")
    print_fn(f"Unmatched evidence files: {len(result.unmatched_evidence)}")
    print_fn(f"Stale evidence files ignored: {len(result.ignored_stale_evidence)}")
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
            workspace.verification_page_path
        )
        print_fn("No pending evaluation proposals.")
        return 0
    print_fn("Pending evaluations:")
    documents = []
    for index, path in enumerate(proposals, start=1):
        document = json.loads(path.read_text(encoding="utf-8"))
        documents.append(document)
        print_fn(
            f"  {index}. {document['verification_id']} - "
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
    application = DefinalyzerApplication(manager)
    if project:
        snapshot = application.snapshot(project)
        print_fn(json.dumps(snapshot.to_dict(), indent=2))
        return 0

    projects = application.list_projects()
    if not projects:
        print_fn("No projects exist.")
        return 0
    for snapshot in projects:
        workflow = snapshot.workflow
        print_fn(
            f"{snapshot.name} [{snapshot.entity_type}] - "
            f"{workflow['ready_stages']}/{workflow['required_stages']} "
            "required stages ready - "
            f"{workflow['next_action']}"
        )
    return 0


def _workflow_status_document(workspace: ProjectWorkspace) -> dict[str, object]:
    return workflow_status_document(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    )


def _invalidate_after_source_change(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    previous_fingerprint: str,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    """Mark generated descendants stale when source semantics changed."""

    if source_corpus_fingerprint(workspace) == previous_fingerprint:
        return workspace
    changed = False
    for stage in (
        "research",
        "registry",
        "verification_plan",
        "evidence_collection",
        "evidence_evaluation",
        "obsidian_links",
    ):
        current_status = workspace.document["stages"][stage]["status"]
        if current_status in {"not_started", "pending"}:
            continue
        workspace = manager.update_stage(
            workspace,
            stage,
            "pending",
            detail="Collected source inputs changed; regenerate this stage.",
        )
        changed = True
    if changed:
        verification_status = str(
            workspace.document.get("verification_status", "not_requested")
        )
        if verification_status not in {"not_requested", "unsupported"}:
            workspace = manager.set_verification_status(workspace, "pending")
        print_fn(
            "Collected source content changed. Existing generated files were "
            "preserved and dependent stages were marked for regeneration."
        )
    return workspace


def _invalidate_after_research_change(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
) -> ProjectWorkspace:
    """Preserve derived artifacts but prevent reuse after research changes."""

    changed = False
    for stage in (
        "registry",
        "verification_plan",
        "evidence_collection",
        "evidence_evaluation",
        "obsidian_links",
    ):
        if workspace.document["stages"][stage]["status"] in {
            "not_started",
            "pending",
        }:
            continue
        workspace = manager.update_stage(
            workspace,
            stage,
            "pending",
            detail="Research inputs changed; regenerate this stage.",
        )
        changed = True
    if changed and workspace.document.get("verification_status") not in {
        "not_requested",
        "unsupported",
    }:
        workspace = manager.set_verification_status(workspace, "pending")
    return workspace


def _invalidate_after_registry_change(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    previous_fingerprint: str | None,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    """Mark verification descendants stale after a registry content change."""

    registry_path = workspace.registry_directory / "registry.json"
    if json_fingerprint(
        registry_path,
        ignored_keys=("generated_at",),
    ) == previous_fingerprint:
        return workspace
    changed = False
    for stage in (
        "verification_plan",
        "evidence_collection",
        "evidence_evaluation",
        "obsidian_links",
    ):
        if workspace.document["stages"][stage]["status"] in {
            "not_started",
            "pending",
        }:
            continue
        workspace = manager.update_stage(
            workspace,
            stage,
            "pending",
            detail="Registry inputs changed; regenerate this stage.",
        )
        changed = True
    if changed:
        if workspace.document.get("verification_status") not in {
            "not_requested",
            "unsupported",
        }:
            workspace = manager.set_verification_status(workspace, "pending")
        print_fn(
            "Registry content changed. Existing verification files were "
            "preserved and marked for regeneration."
        )
    return workspace


def _invalidate_after_verification_job_change(
    manager: WorkspaceManager,
    workspace: ProjectWorkspace,
    *,
    previous_fingerprint: str | None,
    current_fingerprint: str | None,
    print_fn: PrintFunction,
) -> ProjectWorkspace:
    """Prevent old evidence from satisfying a revised verification plan."""

    if current_fingerprint == previous_fingerprint:
        return workspace
    changed = False
    for stage in ("evidence_collection", "evidence_evaluation"):
        if workspace.document["stages"][stage]["status"] in {
            "not_started",
            "pending",
        }:
            continue
        workspace = manager.update_stage(
            workspace,
            stage,
            "pending",
            detail="Verification requests changed; recollect this stage.",
        )
        changed = True
    if changed:
        print_fn(
            "Verification requests changed. Existing evidence was preserved "
            "but cannot satisfy the revised checklist."
        )
    return workspace


def _menu_prerequisites_ready(
    workspace: ProjectWorkspace,
    *,
    choice: str,
    print_fn: PrintFunction,
) -> bool:
    """Compatibility wrapper mapping menu positions to workflow steps."""

    steps = {
        "4": "research_page",
        "5": "registry",
        "6": "verification_plan",
        "7": "evidence_collection",
        "8": "evidence_evaluation",
        "9": "review",
    }
    if choice not in steps:
        raise ValueError(f"Unknown workflow menu choice: {choice}")
    return _workflow_prerequisites_ready(
        workspace,
        step=steps[choice],
        print_fn=print_fn,
    )


def _workflow_prerequisites_ready(
    workspace: ProjectWorkspace,
    *,
    step: str,
    print_fn: PrintFunction,
) -> bool:
    """Enforce the same stage prerequisites for menu and CLI users."""

    supported = {
        "research_page",
        "registry",
        "verification_plan",
        "evidence_collection",
        "evidence_evaluation",
        "review",
    }
    if step not in supported:
        raise ValueError(f"Unknown workflow step: {step}")

    bootstrap_legacy_research(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    )
    research_current = research_pages_current(
        workspace,
        prompts_root=PROJECT_ROOT / "prompts",
    )
    if step == "research_page" and not _collected_source_pages(workspace):
        print_fn("Research-page generation needs collected documentation first.")
        print_fn(
            "Crawl documentation first (menu option 3 / `python main.py "
            f"crawl {workspace.slug}`), or analyze the complete project."
        )
        return False
    if step == "registry" and not research_current:
        print_fn(
            "Registry generation needs all current research pages first."
        )
        print_fn(
            "Run Analyze Project (menu option 2 / `python main.py analyze "
            f"{workspace.slug}`) to generate or refresh them."
        )
        return False
    if step in {
        "verification_plan",
        "evidence_collection",
        "evidence_evaluation",
        "review",
    }:
        missing = []
        if not research_current:
            missing.append(
                "complete current research pages (menu option 4 or option 2)"
            )
        registry_status = workspace.document["stages"]["registry"]["status"]
        if (
            not (workspace.registry_directory / "registry.json").exists()
            or registry_status not in {"complete", "partial"}
        ):
            missing.append("registry and token data (option 5)")
        if missing:
            print_fn("This verification step cannot run yet.")
            print_fn("Missing: " + "; ".join(missing) + ".")
            print_fn(
                "Run the listed menu steps, or `python main.py analyze "
                f"{workspace.slug}` to complete the research steps in order."
            )
            return False
    if step in {"evidence_collection", "evidence_evaluation", "review"}:
        if (
            workspace.document["stages"]["verification_plan"]["status"]
            != "complete"
            or not workspace.verification_page_path.exists()
        ):
            print_fn("This step needs a current verification checklist.")
            print_fn(
                "Run menu option 6 or `python main.py verification-plan "
                f"{workspace.slug}` first."
            )
            return False
    if step == "evidence_collection":
        if not (workspace.jobs_directory / "verification-plan.json").exists():
            print_fn(
                "This checklist has no scanner-ready requests. Its claims "
                "remain in the verification page for manual analyst review."
            )
            return False
    if step == "evidence_evaluation":
        if workspace.document["stages"]["evidence_collection"]["status"] not in {
            "complete",
            "partial",
        }:
            print_fn("No planned blockchain evidence is ready for assessment.")
            print_fn("Run option 7 first.")
            return False
    if step == "review" and not pending_proposals(workspace):
        print_fn("No pending evidence assessment proposals require approval.")
        print_fn("Run option 8 after collecting evidence, if applicable.")
        return False
    return True


def _verification_status_label(workspace: ProjectWorkspace) -> str:
    return verification_status_label(workspace)


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
    default_pattern = _default_crawl_pattern(docs_url)
    return (
        input_fn(f"Sitemap pattern [{default_pattern}]: ").strip()
        or default_pattern
    )


def _default_crawl_pattern(docs_url: str) -> str:
    """Scope subsection URLs while retaining broad discovery for site roots."""

    parsed_path = urlparse(docs_url.strip()).path
    path = parsed_path.rstrip("/")
    if not path:
        return DEFAULT_PATTERN
    if not parsed_path.endswith("/"):
        parent = path.rpartition("/")[0]
        if parent:
            path = parent
    return f"*{path}/*"


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
