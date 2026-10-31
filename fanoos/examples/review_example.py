"""Use Fanoos as a library.

Run with XAI_API_KEY set:

    python examples/review_example.py https://your-portfolio.com
"""

from __future__ import annotations

import sys

from fanoos import Fanoos, FanoosError, load_source


def main(target: str) -> int:
    """Review ``target`` in English, stream the reply, then print the scores."""
    try:
        agent = Fanoos()
        source = load_source(target)
        review = agent.review(source, language="en", on_delta=lambda d: print(d, end="", flush=True))
    except FanoosError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return exc.exit_code

    print("\n\n--- Structured result ---")
    print("Verdict:", review.verdict)
    for issue in review.critical_issues:
        print(f"  ✗ {issue.issue}\n    → {issue.fix}")
    for key, score in review.scores.items():
        print(f"  {key:<24} {score:>3}/100")
    print("Overall:", review.overall_score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "https://example.com"))
