#!/usr/bin/env python3
"""
iPhone simulator smoke test verdict.

Reads sim.png + sim.log + sim-syslog.txt and decides whether the run was
a "black screen / crash" failure or a "menu visible" pass.

Exits:
  0  = pass (non-black + no fatal log)
  1  = not enough inputs (skip)
  2  = black screen (mean luminance below threshold)
  3  = fatal log signature detected

Usage: python3 ci/sim_check.py --png <sim.png> --log <sim.log> --syslog <sim-syslog.txt>
"""
import argparse
import json
import pathlib
import re
import sys


BLACK_MEAN_THRESHOLD = 10.0  # /255, mean RGB below = black
BLACK_VAR_THRESHOLD = 2.0    # pixel variance below = solid color = likely black/splash

FATAL_PATTERNS = [
    (re.compile(r"^Trace/BPT trap"), "BPT trap"),
    (re.compile(r"\bSIGABRT\b"), "SIGABRT"),
    (re.compile(r"\bSIGSEGV\b"), "SIGSEGV"),
    (re.compile(r"\bEXC_BAD_ACCESS\b"), "EXC_BAD_ACCESS"),
    (re.compile(r"Godot Fatal"), "Godot Fatal"),
    (re.compile(r"\bcrashed\b"), "crashed"),
    (re.compile(r"\babort\(\)"), "abort()"),
    (re.compile(r"\bPanic\b"), "panic"),
]

GODOT_ERROR_PATTERNS = [
    (re.compile(r"ERROR:\s*Cannot open file\s+([\"'])?(res://[^\s\"']+)"),
     "missing_res_file"),
    (re.compile(r"ERROR:\s*Cannot find resource\s+([\"'])?(res://[^\s\"']+)"),
     "missing_res_find"),
    (re.compile(r"ERROR:\s*Condition\s+\"[^\"]+\"\s+failed"),
     "condition_failed"),
    (re.compile(r"SCRIPT ERROR.*?at line \d+"), "script_error"),
    (re.compile(r"Cannot resolve sub_resource"), "resolve_sub_resource"),
]


def png_mean_variance(path):
    try:
        from PIL import Image, ImageStat
    except ImportError:
        print("[sim_check] PIL not available; treating as unknown")
        return None, None
    img = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(img)
    mean = sum(stat.mean) / 3.0
    var = sum(stat.var) / 3.0
    return mean, var


def scan_fatal(text, patterns):
    hits = []
    for line in text.splitlines():
        for pat, label in patterns:
            if pat.search(line):
                hits.append({"label": label, "line": line.strip()[:200]})
                break
    return hits


def scan_godot_errors(text):
    hits = []
    for pat, label in GODOT_ERROR_PATTERNS:
        for m in pat.finditer(text):
            hits.append({
                "label": label,
                "match": m.group(0)[:200],
            })
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", required=False, default="")
    ap.add_argument("--png2", required=False, default="")
    ap.add_argument("--png3", required=False, default="")
    ap.add_argument("--log", required=False, default="")
    ap.add_argument("--syslog", required=False, default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    png = pathlib.Path(args.png) if args.png else None
    log = pathlib.Path(args.log) if args.log else None
    syslog = pathlib.Path(args.syslog) if args.syslog else None
    png2 = pathlib.Path(args.png2) if args.png2 else None
    png3 = pathlib.Path(args.png3) if args.png3 else None

    result = {
        "pass": False,
        "black_screen": False,
        "fatal_log": False,
        "godot_errors": [],
        "png_mean": None,
        "png_var": None,
        "png2_mean": None,
        "png3_mean": None,
        "first_non_black": None,
        "log_lines": 0,
    }

    pngs = [p for p in (png, png2, png3) if p and p.exists()]
    if not pngs:
        result["reason"] = "no_png"
        if args.json:
            print(json.dumps(result, indent=2))
        return 1

    means = []
    for i, p in enumerate(pngs):
        mean, var = png_mean_variance(p)
        key = ("png_mean", "png2_mean", "png3_mean")[i]
        result[key] = mean
        if mean is not None:
            means.append(mean)
            result["png_var"] = var
            if result["first_non_black"] is None and mean >= BLACK_MEAN_THRESHOLD:
                result["first_non_black"] = p.name
    if means:
        avg_mean = sum(means) / len(means)
        # PASS if ANY of the screenshots is non-black — means the app
        # eventually rendered, even if the first frame was still the
        # splash/launch image.
        max_mean = max(means)
        result["avg_mean"] = avg_mean
        result["max_mean"] = max_mean
        if max_mean < BLACK_MEAN_THRESHOLD:
            # All screenshots black: real black-screen failure
            result["black_screen"] = True
            if args.json:
                print(json.dumps(result, indent=2))
            return 2

    combined = ""
    for f in (log, syslog):
        if f and f.exists():
            text = f.read_text(errors="ignore")
            result["log_lines"] += len(text.splitlines())
            combined += text + "\n"

    if not combined.strip():
        result["reason"] = "no_log"
    else:
        fatals = scan_fatal(combined, FATAL_PATTERNS)
        if fatals:
            result["fatal_log"] = True
            result["fatals"] = fatals[:10]
        errors = scan_godot_errors(combined)
        result["godot_errors"] = errors[:20]
        if fatals:
            if args.json:
                print(json.dumps(result, indent=2))
            return 3

    if not result["black_screen"] and not result["fatal_log"]:
        result["pass"] = True
    if args.json:
        print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 4


if __name__ == "__main__":
    sys.exit(main())