"""Check feature completion independently of API success and report freshness."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])


def audit(source):
    here = source / "trials/2026-10-19-features"
    read = lambda name: json.loads((here / name).read_text(encoding="utf-8"))
    cases, blocked, baseline, reviews = [read(name) for name in
        ("cases.json", "blocked.json", "baseline.json", "reviews.json")]
    parser = Anchors()
    parser.feed((here / "feature-report.html").read_text(encoding="utf-8"))
    replacements = {}
    for case in cases:
        review = reviews.get(case["id"], {})
        if case.get("comparison_case") and isinstance(review, dict) and review.get("verdict", "").startswith("通过"):
            replacements[case["comparison_case"]] = case["id"]
    # This historical retry lacks comparison_case in the old merged cases.json.
    # Its two independent records and reviews explicitly identify the retry.
    if reviews.get("flux2-klein-single-color-pinned", {}).get("verdict", "").startswith("通过"):
        replacements["flux2-klein-single-color"] = "flux2-klein-single-color-pinned"
    replacements = {old: new for old, new in replacements.items()
                    if reviews.get(old, {}).get("verdict", "").startswith("失败")}
    rows = []
    for case in cases + blocked:
        case_id = case["id"]
        result_file = here / "cases" / case_id / "result.json"
        result = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else {}
        review = reviews.get(case_id, case.get("review", result.get("review", {})))
        verdict = review.get("verdict", "") if isinstance(review, dict) else str(review)
        detail = review.get("detail", review.get("notes", "")) if isinstance(review, dict) else ""
        is_h3 = "minimax" in str(case.get("model", "")).lower()
        status = result.get("status", "missing")
        if case in blocked:
            category = "blocked_no_output"
        elif case_id in replacements:
            category = "historical_failure_with_successful_retry"
        elif status not in {"success", "completed", "complete", "partial_output"} or verdict.startswith(("失败", "未达到")):
            category = "failed_or_unmet"
        elif "部分" in verdict or verdict == "达到风格目标，姿态有变化" or status == "partial_output":
            category = "partial_goal"
        elif verdict in {"pending", "", "待评估"}:
            category = "review_pending"
        else:
            category = "passed_scoped_or_material"
        rows.append({"id": case_id, "model": case.get("model"), "feature": case.get("feature"),
                     "category": category, "excluded_h3": is_h3, "execution": status,
                     "verdict": verdict, "detail": detail, "reason": case.get("reason"),
                     "successful_retry": replacements.get(case_id), "in_html": case_id in parser.ids,
                     "result_file": result_file.relative_to(source).as_posix() if result_file.exists() else None})
    non_h3 = [row for row in rows if not row["excluded_h3"]]
    open_categories = {"blocked_no_output", "failed_or_unmet", "partial_goal", "review_pending"}
    unresolved = [row for row in non_h3 if row["category"] in open_categories]
    caveats = [row for row in non_h3 if row["category"] == "passed_scoped_or_material"
               and ("未严格满足" in row["detail"] or "不满足" in row["detail"])]
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Recorded features only; excludes H3, does not convert every generalization limit into a new task",
            "source_sha256": {name: hashlib.sha256((here / name).read_bytes()).hexdigest() for name in
                              ("cases.json", "blocked.json", "baseline.json", "reviews.json", "feature-report.html")},
            "expected_total_cards": len(cases) + len(blocked) + len(baseline),
            "missing_case_cards": [row["id"] for row in rows if not row["in_html"]],
            "non_h3_categories": dict(Counter(row["category"] for row in non_h3)),
            "non_h3_unresolved_record_count": len(unresolved), "unresolved": unresolved,
            "passed_label_with_explicit_constraint_caveat": [row["id"] for row in caveats],
            "historical_recovered_failures": [row for row in non_h3 if row["category"] == "historical_failure_with_successful_retry"],
            "all_case_rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = audit(args.source.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("expected_total_cards", "missing_case_cards", "non_h3_categories",
                     "non_h3_unresolved_record_count", "passed_label_with_explicit_constraint_caveat")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
