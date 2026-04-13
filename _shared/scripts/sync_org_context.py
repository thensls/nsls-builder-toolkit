#!/usr/bin/env python3
"""Sync org context from Airtable and Google Docs into markdown files.

Usage:
    python3 sync_org_context.py --org-chart      # Sync org chart from People Ops
    python3 sync_org_context.py --lops            # Sync LOPs from SLT base
    python3 sync_org_context.py --strategy        # Sync strategy from Google Doc
    python3 sync_org_context.py --all             # Sync everything

Environment:
    AIRTABLE_API_KEY    — Required for --org-chart and --lops
    GOOGLE_DOCS_API_KEY — Optional for --strategy (falls back to gws CLI)
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CONTEXT_DIR = Path(__file__).resolve().parent.parent / "context"

# Airtable config
PEOPLE_OPS_BASE = "appnXPTu01esWWbrK"
SLT_BASE = "appHDEHQA4bvlWwQq"
EMPLOYEES_TABLE = "tblpa8L4JPnqByINh"
L1_GOALS_TABLE = "tblFLHHpQUVpLrDjb"
L2_GOALS_TABLE = "tblpvFlUEy9GJflzB"

# Employee field IDs
EMP_NAME = "fldkA557zfIC2p8y2"
EMP_EMAIL = "fld3CmPWkul8GodI2"
EMP_SLACK = "fld3lm4bSBxV2tYVX"
EMP_DEPT = "fldIFpAjpTJpV965h"
EMP_TITLE = "fldVaevdMZwPc2NVu"
EMP_MANAGER = "fldDsdq5cCwMHMAjT"
EMP_STATUS = "fld8Wg5gwCEw6nCfw"

# L1 Goal field IDs
L1_THEME = "fldTVap09IVZHmgGi"
L1_SMART = "fldkgrP40za5d6wKn"
L1_DRI_USER = "fldJAWU95Xe0tioed"
L1_ACTIVE = "fldh5tsn6bTIbfAwk"
L1_YEAR = "fld5pzHuvIQh5sAzY"
L1_HEALTH = "fldn9BMtnN6eVm4NH"
L1_COMMENT = "fldNisSd2QmCh9cpf"

# L2 Goal field IDs
L2_NAME = "fld40ptzOdombUe0N"
L2_DRI_USER = "fldtkUyETBshr66uD"
L2_L1_GOAL = "fldzyHhzrh6mni3ND"
L2_STATUS = "fld1Pr6SUP7Z93iMK"
L2_YEAR = "fldP9xlZjm4y3giPo"
L2_HEALTH = "fldiXbqQQAfzq7gKT"
L2_COMMENT = "fldQrBwOTiCdjoSwn"
L2_DEADLINE = "fldqlzeaH1vGmvoVA"

# Google Doc
STRATEGY_DOC_ID = "1EOOTdKLV0j1MnpHV_hwNx4hbcOiHTjjKdo5h7UCZBYo"

TODAY = datetime.now().strftime("%Y-%m-%d")


def airtable_fetch(base_id, table_id, fields=None, filter_formula=None):
    """Fetch all records from an Airtable table with pagination."""
    api_key = os.environ.get("AIRTABLE_API_KEY")
    if not api_key:
        print("Error: AIRTABLE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    records = []
    offset = None
    while True:
        params = ["returnFieldsByFieldId=true"]
        if fields:
            for f in fields:
                params.append(f"fields[]={f}")
        if filter_formula:
            params.append(f"filterByFormula={urllib.request.quote(filter_formula)}")
        if offset:
            params.append(f"offset={offset}")

        url = f"https://api.airtable.com/v0/{base_id}/{table_id}?{'&'.join(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def sync_org_chart():
    """Sync org chart from People Ops Airtable."""
    print("Syncing org chart...", file=sys.stderr)

    fields = [EMP_NAME, EMP_EMAIL, EMP_SLACK, EMP_DEPT, EMP_TITLE, EMP_MANAGER, EMP_STATUS]
    records = airtable_fetch(PEOPLE_OPS_BASE, EMPLOYEES_TABLE, fields=fields)

    # Build lookup for manager names
    id_to_name = {r["id"]: r["fields"].get(EMP_NAME, "") for r in records}

    # Group active employees by department
    departments = {}
    for r in records:
        f = r["fields"]
        if f.get(EMP_STATUS) != "Active":
            continue
        dept = f.get(EMP_DEPT, "Unknown")
        if dept not in departments:
            departments[dept] = []

        manager_ids = f.get(EMP_MANAGER, [])
        manager_name = id_to_name.get(manager_ids[0], "") if manager_ids else ""

        departments[dept].append({
            "name": f.get(EMP_NAME, ""),
            "title": f.get(EMP_TITLE, ""),
            "manager": manager_name,
            "email": f.get(EMP_EMAIL, ""),
            "slack": f.get(EMP_SLACK, ""),
        })

    # Sort departments and employees
    lines = [
        "# NSLS Org Chart",
        f"_Last synced: {TODAY}_",
        "",
    ]

    for dept in sorted(departments.keys()):
        employees = sorted(departments[dept], key=lambda e: e["name"])
        lines.append(f"## {dept}")
        lines.append("")
        lines.append("| Name | Title | Manager | Email | Slack |")
        lines.append("|------|-------|---------|-------|-------|")
        for e in employees:
            slack = e["slack"] or ""
            lines.append(f"| {e['name']} | {e['title']} | {e['manager']} | {e['email']} | {slack} |")
        lines.append("")

    output = CONTEXT_DIR / "org-chart.md"
    output.write_text("\n".join(lines))
    print(f"  Wrote {output} ({sum(len(d) for d in departments.values())} employees)", file=sys.stderr)


def sync_lops():
    """Sync LOPs from SLT Airtable base."""
    print("Syncing LOPs...", file=sys.stderr)

    # Fetch L1 Goals
    l1_fields = [L1_THEME, L1_SMART, L1_DRI_USER, L1_ACTIVE, L1_YEAR, L1_HEALTH, L1_COMMENT]
    l1_records = airtable_fetch(SLT_BASE, L1_GOALS_TABLE, fields=l1_fields)

    # Fetch L2 Goals
    l2_fields = [L2_NAME, L2_DRI_USER, L2_L1_GOAL, L2_STATUS, L2_YEAR, L2_HEALTH, L2_COMMENT, L2_DEADLINE]
    l2_records = airtable_fetch(SLT_BASE, L2_GOALS_TABLE, fields=l2_fields)

    # Index L2s by their L1 parent
    l2_by_l1 = {}
    for r in l2_records:
        f = r["fields"]
        if f.get(L2_STATUS) != "Active":
            continue
        l1_ids = f.get(L2_L1_GOAL, [])
        for l1_id in l1_ids:
            if l1_id not in l2_by_l1:
                l2_by_l1[l1_id] = []
            l2_by_l1[l1_id].append(r)

    lines = [
        "# Lines of Priority (LOPs)",
        f"_Last synced: {TODAY}_",
        "",
    ]

    # Render L1s with their L2s nested
    active_l1s = [r for r in l1_records if r["fields"].get(L1_ACTIVE) == "Active"]
    for r in active_l1s:
        f = r["fields"]
        theme = f.get(L1_THEME, "Untitled")
        smart = f.get(L1_SMART, "")
        dri_users = f.get(L1_DRI_USER, [])
        owner = dri_users[0].get("name", "Unassigned") if dri_users else "Unassigned"
        health_list = f.get(L1_HEALTH, [])
        health = health_list[0] if health_list else "No update"
        comment_list = f.get(L1_COMMENT, [])
        comment = comment_list[0] if comment_list else "No update yet."

        lines.append(f"## L1: {theme}")
        lines.append(f"**Owner**: {owner} | **Health**: {health}")
        if smart:
            lines.append(f"**Goal**: {smart}")
        lines.append(f"> {comment}")
        lines.append("")

        # Nested L2s
        l2s = l2_by_l1.get(r["id"], [])
        for l2r in l2s:
            l2f = l2r["fields"]
            l2_name = l2f.get(L2_NAME, "Untitled")
            l2_dri = l2f.get(L2_DRI_USER, [])
            l2_owner = l2_dri[0].get("name", "Unassigned") if l2_dri else "Unassigned"
            l2_health_list = l2f.get(L2_HEALTH, [])
            l2_health = l2_health_list[0] if l2_health_list else "No update"
            l2_comment_list = l2f.get(L2_COMMENT, [])
            l2_comment = l2_comment_list[0] if l2_comment_list else "No update yet."
            l2_deadline = l2f.get(L2_DEADLINE, "")

            lines.append(f"### L2: {l2_name}")
            deadline_str = f" | **Deadline**: {l2_deadline}" if l2_deadline else ""
            lines.append(f"**Owner**: {l2_owner} | **Health**: {l2_health}{deadline_str}")
            lines.append(f"> {l2_comment}")
            lines.append("")

    output = CONTEXT_DIR / "lops.md"
    output.write_text("\n".join(lines))
    count_l2 = sum(len(v) for v in l2_by_l1.values())
    print(f"  Wrote {output} ({len(active_l1s)} L1s, {count_l2} L2s)", file=sys.stderr)


def sync_strategy():
    """Sync strategy doc from Google Docs."""
    print("Syncing strategy...", file=sys.stderr)

    # Try gws CLI first (works locally with Kevin's auth)
    try:
        result = subprocess.run(
            [os.path.expanduser("~/bin/gws"), "docs", "documents", "get",
             "--params", json.dumps({"documentId": STRATEGY_DOC_ID})],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # Parse gws output (may have keyring message on first line)
            output_lines = result.stdout.strip().split("\n")
            json_start = next(i for i, l in enumerate(output_lines) if l.strip().startswith("{"))
            doc = json.loads("\n".join(output_lines[json_start:]))
        else:
            raise RuntimeError(f"gws failed: {result.stderr}")
    except (FileNotFoundError, RuntimeError) as e:
        # Fallback: Google Docs API with API key or service account
        api_key = os.environ.get("GOOGLE_DOCS_API_KEY")
        if not api_key:
            print(f"  Error: gws not available ({e}) and GOOGLE_DOCS_API_KEY not set", file=sys.stderr)
            print("  Run this locally with gws, or set GOOGLE_DOCS_API_KEY for CI", file=sys.stderr)
            sys.exit(1)
        url = f"https://docs.googleapis.com/v1/documents/{STRATEGY_DOC_ID}?key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            doc = json.loads(resp.read())

    # Convert Google Doc JSON to markdown
    title = doc.get("title", "NSLS Strategy")
    md_lines = [
        f"# {title}",
        f"_Last synced: {TODAY}_",
        f"_Source: [Google Doc](https://docs.google.com/document/d/{STRATEGY_DOC_ID}/edit)_",
        "",
    ]

    for elem in doc.get("body", {}).get("content", []):
        if "paragraph" not in elem:
            continue
        para = elem["paragraph"]
        style = para.get("paragraphStyle", {}).get("namedStyleType", "")

        # Extract text from all elements in the paragraph
        text = ""
        for el in para.get("elements", []):
            text += el.get("textRun", {}).get("content", "")
        text = text.strip()
        if not text:
            continue

        # Check for bullet/list items
        bullet = para.get("bullet")

        if "HEADING_1" in style:
            md_lines.append(f"\n## {text}")
        elif "HEADING_2" in style:
            md_lines.append(f"\n### {text}")
        elif "HEADING_3" in style:
            md_lines.append(f"\n#### {text}")
        elif bullet:
            nesting = bullet.get("nestingLevel", 0)
            indent = "  " * nesting
            md_lines.append(f"{indent}- {text}")
        else:
            md_lines.append(text)

    output = CONTEXT_DIR / "strategy.md"
    output.write_text("\n".join(md_lines) + "\n")
    print(f"  Wrote {output}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Sync org context to markdown")
    parser.add_argument("--org-chart", action="store_true", help="Sync org chart")
    parser.add_argument("--lops", action="store_true", help="Sync LOPs")
    parser.add_argument("--strategy", action="store_true", help="Sync strategy doc")
    parser.add_argument("--all", action="store_true", help="Sync everything")
    args = parser.parse_args()

    if not any([args.org_chart, args.lops, args.strategy, args.all]):
        parser.print_help()
        sys.exit(1)

    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

    if args.org_chart or args.all:
        sync_org_chart()
    if args.lops or args.all:
        sync_lops()
    if args.strategy or args.all:
        sync_strategy()

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
