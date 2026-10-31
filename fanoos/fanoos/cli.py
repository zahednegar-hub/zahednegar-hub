"""Command-line interface: ``fanoos review <url-or-pdf-path>``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .agent import Fanoos
from .errors import FanoosError
from .providers import PROVIDERS, preferred_provider_name
from .review import SCORE_KEYS, SCORE_LABELS, Review, contains_persian
from .sources import load_source
from .system_prompt import NO_LIVE_SEARCH_FOOTER

AMBER = "#f2a93b"
_JSON_FENCE = "```json"


# --- environment ----------------------------------------------------------------


def load_dotenv(path: Path | None = None) -> None:
    """Load ``KEY=value`` lines from a ``.env`` file without overriding the real environment.

    Only the current directory's ``.env`` is read. Values are never printed.

    Args:
        path: File to read; defaults to ``./.env``.
    """
    path = path or Path.cwd() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _force_utf8(stream: TextIO) -> None:
    """Make Persian text printable on Windows consoles with legacy code pages."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure and (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - exotic streams
            pass


# --- RTL helpers --------------------------------------------------------------------


def to_visual(text: str, enabled: bool) -> str:
    """Reorder Persian text for terminals without bidi support.

    Most macOS and Linux terminals already render right-to-left text
    correctly, so this is off by default (``--bidi`` turns it on). It needs the
    optional ``python-bidi`` package (``pip install "fanoos[bidi]"``).

    Args:
        text: Logical-order text.
        enabled: Whether to reorder at all.

    Returns:
        Text in visual order, or unchanged if disabled or unsupported.
    """
    if not enabled or not contains_persian(text):
        return text
    try:
        from bidi.algorithm import get_display
    except ImportError:
        return text
    return "\n".join(get_display(line) if contains_persian(line) else line for line in text.split("\n"))


def _block(markdown: str, bidi: bool) -> Markdown:
    rtl = contains_persian(markdown)
    return Markdown(to_visual(markdown, bidi), justify="right" if rtl else "left")


def render_report(report: str, bidi: bool = False) -> Group:
    """Render the written review as Markdown, right-aligning Persian paragraphs."""
    renderables: list[Markdown | Text] = []
    for block in (b for b in report.split("\n\n") if b.strip()):
        if renderables:
            renderables.append(Text(""))
        renderables.append(_block(block, bidi))
    return Group(*renderables)


# --- scorecard -------------------------------------------------------------------------


def _bar(score: int, width: int = 20) -> Text:
    filled = round(score / 100 * width)
    color = "green" if score >= 75 else AMBER if score >= 50 else "red"
    return Text("█" * filled, style=color) + Text("░" * (width - filled), style="grey35")


def render_scorecard(review: Review, bidi: bool = False) -> Panel:
    """Build the closing scorecard panel: verdict, five scores and the overall score."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_column(justify="right")
    for key in SCORE_KEYS:
        if key in review.scores:
            score = review.scores[key]
            table.add_row(SCORE_LABELS[key], _bar(score), f"{score}/100")
    overall = review.overall_score
    if overall is not None:
        table.add_row("", "", "")
        table.add_row(Text("Overall", style=f"bold {AMBER}"), _bar(overall), Text(f"{overall}/100", style="bold"))

    parts: list = []
    if review.verdict:
        parts.append(
            Text(
                to_visual(review.verdict, bidi),
                style="bold",
                justify="right" if contains_persian(review.verdict) else "left",
            )
        )
        parts.append(Text(""))
    parts.append(table)
    if review.next_actions:
        parts.append(Text(""))
        parts.append(Text("Next 3 Actions", style=f"bold {AMBER}"))
        for i, action in enumerate(review.next_actions, 1):
            rtl = contains_persian(action)
            parts.append(Text(f"{i}. {to_visual(action, bidi)}", justify="right" if rtl else "left"))
    if not review.live_search:
        parts.append(Text(""))
        parts.append(Text(to_visual(NO_LIVE_SEARCH_FOOTER, bidi), style="grey50", justify="right"))
    subtitle = f"[grey50]{review.provider} · {review.model}[/]" if review.provider else None
    return Panel(
        Group(*parts),
        title=f"[bold {AMBER}]Fanoos · فانوس[/] scorecard",
        subtitle=subtitle,
        border_style=AMBER,
        padding=(1, 2),
    )


def render_providers() -> Table:
    """Build the ``fanoos providers`` table from the environment (keys are never shown)."""
    selected = preferred_provider_name()
    table = Table(title="Fanoos providers", title_style=f"bold {AMBER}", border_style="grey35")
    table.add_column("Provider")
    table.add_column("API key")
    table.add_column("Status")
    table.add_column("Default model")
    table.add_column("Live search")
    table.add_column("Tier")
    for provider in PROVIDERS.values():
        name = provider.name + ("  ◀ selected" if provider.name == selected else "")
        status = "[green]✓ configured[/]" if provider.configured else "[grey50]✗ not set[/]"
        table.add_row(
            Text(name, style=f"bold {AMBER}" if provider.name == selected else ""),
            provider.env_var,
            status,
            provider.default_model,
            "web + X" if provider.live_search else "—",
            "free" if provider.free_tier else "paid",
        )
    return table


# --- streaming ------------------------------------------------------------------------------


class ReportStream:
    """Pass streamed text through to the terminal while hiding the trailing JSON block."""

    def __init__(self) -> None:
        self._pending = ""
        self._stopped = False

    def feed(self, delta: str) -> str:
        """Accept a fragment and return the part that is safe to print now."""
        if self._stopped:
            return ""
        self._pending += delta
        idx = self._pending.find(_JSON_FENCE)
        if idx != -1:
            out, self._pending, self._stopped = self._pending[:idx], "", True
            return out
        # Hold back a tail that could be the start of the fence.
        cut = len(self._pending)
        for start in range(max(0, cut - len(_JSON_FENCE) + 1), cut):
            if _JSON_FENCE.startswith(self._pending[start:]):
                cut = start
                break
        out, self._pending = self._pending[:cut], self._pending[cut:]
        return out

    def flush(self) -> str:
        """Return whatever is still held back at the end of the stream."""
        out, self._pending = ("" if self._stopped else self._pending), ""
        return out


# --- commands -------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="fanoos",
        description="Fanoos (فانوس): a bilingual AI portfolio critic for UI/UX and web designers.",
        epilog="API keys are read from XAI_API_KEY, GEMINI_API_KEY or GROQ_API_KEY (environment or ./.env).",
    )
    parser.add_argument("--version", action="version", version=f"fanoos {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser(
        "providers",
        help="Show which AI providers are configured.",
        description="Show which AI providers are configured (from the environment) and which one is selected.",
    )

    review = sub.add_parser(
        "review", help="Review a portfolio URL or PDF.", description="Review a portfolio URL or PDF."
    )
    review.add_argument("target", help="Portfolio URL (https://...) or path to a PDF.")
    review.add_argument("--lang", choices=("fa", "en"), default="fa", help="Reply language (default: fa).")
    review.add_argument(
        "--focus", metavar="TEXT", help="Extra request, e.g. 'Focus on the Venture Compass case study'."
    )
    review.add_argument(
        "--provider",
        choices=tuple(PROVIDERS),
        help="AI provider (default: $FANOOS_PROVIDER, else the first configured of xai, gemini, groq).",
    )
    review.add_argument("--model", help="Model ID (default: $FANOOS_MODEL, else the provider's default).")
    review.add_argument("--json", action="store_true", help="Print the structured review as JSON only.")
    review.add_argument("--raw", action="store_true", help="Print the model's reply unparsed.")
    review.add_argument("--no-stream", action="store_true", help="Wait for the full reply, then render it.")
    review.add_argument("--no-fetch", action="store_true", help="Do not pre-fetch the URL; let the model browse it.")
    review.add_argument("--bidi", action="store_true", help="Reorder Persian text for terminals without RTL support.")
    return parser


def cmd_review(args: argparse.Namespace, out: Console, err: Console) -> int:
    """Run ``fanoos review``. Returns the process exit code."""
    agent = Fanoos(provider=args.provider, model=args.model)  # fail fast on a missing key, before any download
    if not (args.json or args.raw):
        err.print(
            f"[{AMBER}]🏮 Fanoos[/] is reading [bold]{args.target}[/] "
            f"[grey50]({agent.provider.name} · {agent.model})[/] …"
        )
    source = load_source(args.target, fetch=not args.no_fetch)

    if args.raw:
        for delta in agent.stream(source, args.lang, args.focus):
            out.file.write(delta)
            out.file.flush()
        out.file.write("\n")
        return 0

    if args.json:
        review = agent.review(source, args.lang, args.focus)
        out.file.write(json.dumps(review.to_dict(), ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.no_stream or args.bidi:
        with err.status(f"[{AMBER}]Lighting the lantern…[/]"):
            review = agent.review(source, args.lang, args.focus)
        out.print(Panel(render_report(review.report, args.bidi), border_style="grey35", padding=(1, 2)))
    else:
        stream = ReportStream()
        chunks: list[str] = []
        for delta in agent.stream(source, args.lang, args.focus):
            chunks.append(delta)
            out.file.write(stream.feed(delta))
            out.file.flush()
        out.file.write(stream.flush() + "\n\n")
        review = agent.finish("".join(chunks))

    out.print(render_scorecard(review, args.bidi))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``fanoos`` command.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        The process exit code (0 on success).
    """
    _force_utf8(sys.stdout)
    _force_utf8(sys.stderr)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    out = Console(file=sys.stdout, highlight=False)
    err = Console(file=sys.stderr, highlight=False)
    load_dotenv()
    try:
        if args.command == "providers":
            out.print(render_providers())
            return 0
        return cmd_review(args, out, err)
    except FanoosError as exc:
        err.print(Text("error: ", style="bold red") + Text(str(exc)))
        return exc.exit_code
    except KeyboardInterrupt:
        err.print("\n[grey50]Cancelled.[/]")
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
