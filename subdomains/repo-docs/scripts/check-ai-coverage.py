#!/usr/bin/env python3
"""Every marked face of AI-POLICY.md must have an owner that enforces it.

Three consecutive adversarial review rounds found the same defect: a rule
marked [C] or [R] whose enforcement point does not mention it. The text
always existed somewhere -- in a caller, in a header -- just not in the skill
the policy names. This is the mechanical check that ends that class.

  [C] -> must appear as a row in latex-ai-statement's Checks table
  [R] -> must be named by update-ai-usage or update-tokens
  [F] -> the SHORT index's floor line must match the marker set exactly

Exit 0 = every face owned. Exit 1 = an unowned face (the defect).
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
POLICY = ROOT / "subdomains/repo-docs/templates/AI-POLICY.md"
OWNERS = {
    "C": [ROOT / "subdomains/latex/skills/latex-ai-statement/SKILL.md"],
    "R": [ROOT / "skills/update-ai-usage/SKILL.md",
          ROOT / "skills/update-tokens/SKILL.md"],
}

def main():
    if not POLICY.exists():
        print(f"FAIL: policy not found at {POLICY}"); return 1
    text = POLICY.read_text()

    rules = {}
    for m in re.finditer(r"\*\*(AI\d+) — .*?((?:\[[CRF]\])+)\.\*\*", text):
        rules[m.group(1)] = set(re.findall(r"\[([CRF])\]", m.group(2)))
    if not rules:
        print("FAIL: no marked rules parsed -- marker format changed?"); return 1

    # [C] owner: a table row, not a passing mention. The row form is "| AIn |".
    checker = OWNERS["C"][0]
    c_rows = set(re.findall(r"^\|\s*(AI\d+)\s*\|", checker.read_text(), re.M)) \
             if checker.exists() else set()
    # [R] owner: named anywhere in either record skill.
    r_text = "\n".join(p.read_text() for p in OWNERS["R"] if p.exists())
    r_named = set(re.findall(r"\bAI\d+\b", r_text))
    # [F]: markers are the source of truth; the SHORT index must agree.
    short = POLICY.with_name("AI-POLICY-SHORT.md")
    fl = re.search(r"Floors \(never weakened\):([^.]*)\.", short.read_text()) \
         if short.exists() else None
    f_listed = set(re.findall(r"\bAI\d+\b", fl.group(1))) if fl else set()

    problems = []
    for rule, marks in sorted(rules.items(), key=lambda kv: int(kv[0][2:])):
        if "C" in marks and rule not in c_rows:
            problems.append(f"{rule} [C] has no row in {checker.name}")
        if "R" in marks and rule not in r_named:
            problems.append(f"{rule} [R] is named by neither record skill")
        if "F" in marks and rule not in f_listed:
            problems.append(f"{rule} [F] is missing from AI-POLICY-SHORT's floor line")
    # reverse: a checker row for a rule that is not [C]
    for rule in sorted(c_rows - {r for r, m in rules.items() if "C" in m}):
        problems.append(f"{rule} has a checker row but is not marked [C]")
    for rule in sorted(f_listed - {r for r, m in rules.items() if "F" in m}):
        problems.append(f"{rule} is in SHORT's floor line but is not marked [F]")

    print(f"parsed {len(rules)} rules: "
          f"{sum('C' in m for m in rules.values())} [C], "
          f"{sum('R' in m for m in rules.values())} [R], "
          f"{sum('F' in m for m in rules.values())} [F]")
    if problems:
        print(f"\nUNOWNED FACES ({len(problems)}):")
        for p in problems: print(f"  - {p}")
        return 1
    print("every marked face has an owner.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
