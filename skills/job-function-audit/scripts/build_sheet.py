#!/usr/bin/env python3
"""
build_sheet.py: create/format a job-function audit Google Sheet from a JSON spec.

Why this exists: every audit re-does the same mechanical Sheets work (create tabs,
write rows, freeze header, wrap, tint the owner-to-fill columns, verify Time% sums).
This bundles it so each run doesn't reinvent it. Auth uses `gcloud auth print-access-token`
because `gws` is typically not configured in this environment.

Usage:
    python3 build_sheet.py spec.json          # create a new sheet
    python3 build_sheet.py spec.json --id SID  # write into an existing sheet's first tab

Spec JSON (all fields optional except headers + rows):
{
  "title": "Job Function Audit: <name>",
  "exec_block": [["ROUGH TIME BREAKDOWN ..."], ["RevOps ~85% | Admin ~6% ..."], [""],
                 ["HEADLINE FINDINGS"], ["1. ..."], ["2. ..."], ["3. ..."]],
  "legend": "COLUMN KEY: Time % = draft ... Keep? = Y/Delegate/Automate ... Fly-in = ...",
  "headers": ["Function","Task Type","Examples","Time % (draft)","Criticality",
              "Keep? (Y/Delegate/Automate)","Fly-in","Current owner","Target owner (R)",
              "Delegation path","Notes"],
  "rows": [ ["Admin","...","...","3%","","","","Royce","IT/Ops","...","..."], ... ],
  "target_block": {"subheader": "TARGET STATE / REVENUE WORK ...",
                   "rows": [ ["Target state (desired)","...", ...], ... ]},
  "ask_block": ["THE ASK ...", "1. ...", "2. ...", "3. ..."],
  "timepct_col": 3,            # 0-based column index that holds "NN%" for the sum check
  "category_col": 0,           # 0-based column used for the category rollup
  "decision_cols": [3,4,5,6],  # 0-based columns to tint (owner-to-fill: Time/Crit/Keep/Fly-in)
  "col_widths": [95,210,330,72,80,120,64,120,150,200,330],
  "exclude_terms": []          # terms that must NOT appear anywhere (honor subject exclusions)
}

Prints a verification line (row count, Time% sum, category rollup, excluded-term scan) and the URL.
"""
import subprocess, json, sys, re, argparse

def token():
    return subprocess.check_output(["gcloud","auth","print-access-token"]).decode().strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--id", help="existing spreadsheetId (writes into first tab)")
    ap.add_argument("--tab", default="Audit", help="tab title for a new sheet")
    args = ap.parse_args()

    try:
        import requests
    except ImportError:
        sys.exit("Need `requests` (pip install requests) on a Python 3.10+ interpreter.")

    spec = json.load(open(args.spec))
    H = {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}
    B = "https://sheets.googleapis.com/v4/spreadsheets"

    headers = spec["headers"]; rows = spec["rows"]
    exec_block = spec.get("exec_block", [])
    legend = spec.get("legend")
    tb = spec.get("target_block") or {}
    ask = spec.get("ask_block", [])

    # assemble body, tracking positions (0-based)
    body, pos = [], {}
    for r in exec_block: body.append(r if isinstance(r, list) else [r])
    if exec_block: body.append([""])
    if legend: pos["legend"] = len(body); body.append([legend])
    pos["header"] = len(body); body.append(headers)
    pos["data_start"] = len(body); body += [list(r) for r in rows]; pos["data_end"] = len(body) - 1
    if tb:
        body.append([""]); pos["subheader"] = len(body); body.append([tb.get("subheader","TARGET STATE")])
        pos["tgt_start"] = len(body); body += [list(r) for r in tb.get("rows",[])]; pos["tgt_end"] = len(body)-1
    if ask:
        body.append([""]); pos["ask"] = len(body)
        for line in ask: body.append([line] if isinstance(line, str) else line)

    # create or reuse
    if args.id:
        sid = args.id
        meta = requests.get(f"{B}/{sid}", headers=H); meta.raise_for_status()
        gid = meta.json()["sheets"][0]["properties"]["sheetId"]
        tab = meta.json()["sheets"][0]["properties"]["title"]
    else:
        resp = requests.post(B, headers=H, data=json.dumps(
            {"properties":{"title":spec.get("title","Job Function Audit")},
             "sheets":[{"properties":{"title":args.tab}}]})); resp.raise_for_status()
        j = resp.json(); sid = j["spreadsheetId"]; gid = j["sheets"][0]["properties"]["sheetId"]; tab = args.tab

    # write values
    requests.post(f"{B}/{sid}/values:batchUpdate", headers=H, data=json.dumps(
        {"valueInputOption":"RAW","data":[{"range":f"'{tab}'!A1","values":body}]})).raise_for_status()

    # formatting
    hi = pos["header"]; d0 = pos["data_start"]; d1 = pos["data_end"]
    reqs = []
    for i, w in enumerate(spec.get("col_widths", [])):
        reqs.append({"updateDimensionProperties":{"range":{"sheetId":gid,"dimension":"COLUMNS","startIndex":i,"endIndex":i+1},"properties":{"pixelSize":w},"fields":"pixelSize"}})
    last = len(body)
    reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":hi,"endRowIndex":last},"cell":{"userEnteredFormat":{"wrapStrategy":"WRAP","verticalAlignment":"TOP"}},"fields":"userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment"}})
    reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":hi,"endRowIndex":hi+1},"cell":{"userEnteredFormat":{"backgroundColor":{"red":0.17,"green":0.24,"blue":0.31},"textFormat":{"bold":True,"foregroundColor":{"red":1,"green":1,"blue":1}}}},"fields":"userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"}})
    reqs.append({"updateSheetProperties":{"properties":{"sheetId":gid,"gridProperties":{"frozenRowCount":hi+1}},"fields":"gridProperties.frozenRowCount"}})
    if "legend" in pos:
        reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":pos["legend"],"endRowIndex":pos["legend"]+1},"cell":{"userEnteredFormat":{"textFormat":{"italic":True,"fontSize":9,"foregroundColor":{"red":0.4,"green":0.4,"blue":0.4}}}},"fields":"userEnteredFormat.textFormat"}})
    if "subheader" in pos:
        reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":pos["subheader"],"endRowIndex":pos["subheader"]+1},"cell":{"userEnteredFormat":{"backgroundColor":{"red":0.9,"green":0.95,"blue":0.9},"textFormat":{"bold":True}}},"fields":"userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"}})
    if "ask" in pos:
        reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":pos["ask"],"endRowIndex":pos["ask"]+1},"cell":{"userEnteredFormat":{"textFormat":{"bold":True}}},"fields":"userEnteredFormat.textFormat"}})
    dc = spec.get("decision_cols")
    if dc:
        reqs.append({"repeatCell":{"range":{"sheetId":gid,"startRowIndex":d0,"endRowIndex":d1+1,"startColumnIndex":min(dc),"endColumnIndex":max(dc)+1},"cell":{"userEnteredFormat":{"backgroundColor":{"red":1,"green":0.97,"blue":0.8},"horizontalAlignment":"CENTER"}},"fields":"userEnteredFormat.backgroundColor,userEnteredFormat.horizontalAlignment"}})
    requests.post(f"{B}/{sid}:batchUpdate", headers=H, data=json.dumps({"requests":reqs})).raise_for_status()

    # verify
    tcol = spec.get("timepct_col"); ccol = spec.get("category_col")
    total = 0; cat = {}
    for r in rows:
        if tcol is not None and tcol < len(r):
            m = re.match(r"(\d+)%", str(r[tcol]).strip())
            if m:
                n = int(m.group(1)); total += n
                if ccol is not None and ccol < len(r): cat[r[ccol]] = cat.get(r[ccol], 0) + n
    blob = " ".join(" ".join(map(str, r)) for r in body).lower()
    hits = [t for t in spec.get("exclude_terms", []) if t.lower() in blob]
    print(f"rows={len(rows)} time%_sum={total} by_category={cat}")
    print(f"excluded_terms_present={hits or 'none'}")
    print(f"https://docs.google.com/spreadsheets/d/{sid}/edit")

if __name__ == "__main__":
    main()
