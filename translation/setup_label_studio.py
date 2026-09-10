"""
setup_label_studio.py

Creates Label Studio projects for human review, one per language (plus one
for the English PARA/SYNO perturbations), and imports the current data as
tasks. Idempotent: reuses an existing project by title instead of
duplicating it, and skips tasks whose base_id/perturbation_type/language
combination is already imported.

Review flow (per the user's design): reviewer sees source + target text,
picks Correct/Incorrect. If Incorrect, a multi-select issue-type checklist,
a corrected-text box, and a notes box appear.

Label Studio runs in its own separate venv (label_studio_env, not bfcl_env)
to avoid numpy/dependency conflicts with the BFCL harness -- see LOG.md
2026-08-24. This script itself runs under bfcl_env and only talks to the
already-running Label Studio server over its REST API.

Exported reviews (once verifiers submit them) land in a separate file per
the data provenance policy in PROJECT_MANIFEST.md -- see
import_label_studio_reviews.py (to be built when the first reviews are in).

USAGE (run from inside berkeley-function-call-leaderboard, with the Label
Studio server already running):
    python translation/setup_label_studio.py
"""

import argparse
import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import requests
from dotenv import load_dotenv

load_dotenv()

# Two targets: the original local instance (token auth, via a legacy
# token pulled from its DB -- see LOG.md 2026-08-24) and the Render-hosted
# instance (session+CSRF auth instead -- no shell/manage.py access there
# to pull a token the same way, so it logs in with real credentials).
LS_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LS_TOKEN = os.getenv("LABEL_STUDIO_API_TOKEN")

RENDER_LS_URL = os.getenv("RENDER_LS_URL")
RENDER_LS_EMAIL = os.getenv("RENDER_LS_EMAIL")
RENDER_LS_PASSWORD = os.getenv("RENDER_LS_PASSWORD")

PERTURBATIONS_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
PERTURBATIONS_QA_PATH = Path("data/perturbations/en_multiple_perturbations_qa.jsonl")
TRANSLATIONS_PATH = Path("data/translations/multiple_translations.jsonl")
TRANSLATIONS_QA_PATH = Path("data/translations/multiple_translations_qa.jsonl")

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil", "mr": "Marathi", "bn": "Bengali", "sat": "Santali", "brx": "Bodo", "gu": "Gujarati"}

ISSUE_TYPES = [
    "Number/value changed or dropped",
    "Wrong word choice / mistranslation",
    "Grammar error",
    "Meaning changed",
    "Missing content",
    "Added content (hallucination)",
    "Script/formatting issue",
    "Not a valid paraphrase/synonym swap (too different, or unchanged)",
    "Other",
]

# What to actively look for while reading -- shown upfront, before the
# reviewer judges anything, since the issue-type checklist only kicks in
# AFTER they've already decided something's wrong. Static and identical
# on every task page (not per-task data), so it's baked directly into the
# label_config XML rather than passed through task data.
TRANSLATION_GUIDELINES = [
    "Are all numbers and values exactly preserved (nothing changed, dropped, or added)?",
    "Is the full meaning preserved -- nothing added, nothing left out?",
    "Are units, symbols, and exponents (e.g. %, ^, &#176;) correctly conveyed, even if reworded as text?",
    "Is the word choice and grammar natural and accurate?",
]

PERTURBATION_GUIDELINES = TRANSLATION_GUIDELINES + [
    "For SYNO items: is it a word-for-word synonym swap, not a full rewrite of the sentence?",
    "For PARA items: does it still mean exactly the same thing as the original, just phrased differently?",
]


def session(target):
    """Local: legacy token auth (pulled from the DB via Django shell --
    see LOG.md 2026-08-24). Render: no shell access there, so this logs
    in with real credentials instead (session cookie + CSRF header,
    confirmed working for both reads and writes)."""
    s = requests.Session()
    if target == "render":
        login_page = s.get(f"{LS_URL}/user/login/")
        m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        csrf_token = m.group(1)
        resp = s.post(
            f"{LS_URL}/user/login/?next=/",
            data={"csrfmiddlewaretoken": csrf_token, "email": RENDER_LS_EMAIL, "password": RENDER_LS_PASSWORD},
            headers={"Referer": f"{LS_URL}/user/login/"},
        )
        resp.raise_for_status()
        s.headers.update({
            "X-CSRFToken": s.cookies.get("csrftoken"),
            "Referer": f"{LS_URL}/",
        })
    else:
        s.headers.update({"Authorization": f"Token {LS_TOKEN}"})
    return s


def build_labeling_config(source_label, target_label, guidelines):
    issue_choices = "\n".join(f'      <Choice value="{c}"/>' for c in ISSUE_TYPES)
    guidelines_items = "".join(f"<li>{g}</li>" for g in guidelines)
    guidelines_html = f"<ul style='margin:4px 0 0 18px;padding:0;'>{guidelines_items}</ul>"
    guidelines_attr = xml_escape(guidelines_html, {'"': "&quot;"})
    return f"""
<View>
  <View style="background:#f0f4f8;border:1px solid #cbd5e1;padding:12px;border-radius:4px;margin-bottom:16px;">
    <Header value="Reviewer guidelines" size="4"/>
    <HyperText name="guidelines" value="{guidelines_attr}"/>
  </View>

  <Header value="{source_label}"/>
  <Text name="source" value="$english_source"/>
  <Header value="{target_label}"/>
  <Text name="target" value="$target_text"/>

  <HyperText name="qa_warning" value="$qa_warning_html"/>

  <Header value="Is this correct?"/>
  <Choices name="correctness" toName="target" choice="single" required="true" showInLine="true">
    <Choice value="Correct"/>
    <Choice value="Incorrect"/>
  </Choices>

  <View visibleWhen="choice-selected" whenTagName="correctness" whenChoiceValue="Incorrect">
    <Header value="What's wrong? (select all that apply)"/>
    <Choices name="issue_type" toName="target" choice="multiple">
{issue_choices}
    </Choices>

    <Header value="Corrected version"/>
    <TextArea name="corrected_text" toName="target" editable="true" rows="3"
              placeholder="Type or paste the correct version here"/>

    <Header value="Notes (optional)"/>
    <TextArea name="notes" toName="target" editable="true" rows="2"
              placeholder="e.g. 'check units', anything worth flagging"/>
  </View>
</View>
""".strip()


def build_perturbation_pair_config():
    """PARA and SYNO shown together: the source is read once, then two
    independently-labeled, independently-judged blocks below it -- one
    per perturbation type, each with its own Correct/Incorrect, issue
    checklist, correction box, and notes, tracked as separate
    control names (correctness_para vs correctness_syno, etc.). This is
    purely a review-time presentation choice -- the two judgments stay
    fully separable in the stored annotation, decomposing back into the
    same two-independent-records shape the downstream pipeline expects
    from PARA and SYNO as distinct conditions."""
    issue_choices = "\n".join(f'        <Choice value="{c}"/>' for c in ISSUE_TYPES)
    guidelines_items = "".join(f"<li>{g}</li>" for g in TRANSLATION_GUIDELINES)
    guidelines_html = f"<ul style='margin:4px 0 0 18px;padding:0;'>{guidelines_items}</ul>"
    guidelines_attr = xml_escape(guidelines_html, {'"': "&quot;"})

    def block(kind, label, reminder):
        return f"""
  <View style="border-top:2px solid #cbd5e1;margin-top:18px;padding-top:16px;">
    <Header value="{label}" size="3"/>
    <Text name="{kind}_target" value="${kind}_text"/>
    <View style="font-style:italic;color:#6b6580;font-size:0.9em;margin:2px 0 10px;">
      <Text name="{kind}_reminder" value="{reminder}"/>
    </View>

    <HyperText name="{kind}_qa_warning" value="${kind}_qa_warning_html"/>

    <Header value="Is this correct?"/>
    <Choices name="correctness_{kind}" toName="{kind}_target" choice="single" required="true" showInLine="true">
      <Choice value="Correct"/>
      <Choice value="Incorrect"/>
    </Choices>

    <View visibleWhen="choice-selected" whenTagName="correctness_{kind}" whenChoiceValue="Incorrect">
      <Header value="What's wrong? (select all that apply)"/>
      <Choices name="issue_type_{kind}" toName="{kind}_target" choice="multiple">
{issue_choices}
      </Choices>

      <Header value="Corrected version"/>
      <TextArea name="corrected_text_{kind}" toName="{kind}_target" editable="true" rows="3"
                placeholder="Type or paste the correct version here"/>

      <Header value="Notes (optional)"/>
      <TextArea name="notes_{kind}" toName="{kind}_target" editable="true" rows="2"
                placeholder="e.g. 'check units', anything worth flagging"/>
    </View>
  </View>"""

    para_block = block("para", "PARA (Paraphrase)",
                        "Remember: PARA should mean exactly the same thing as the original, just phrased differently.")
    syno_block = block("syno", "SYNO (Synonym Substitution)",
                        "Remember: SYNO should be a word-for-word synonym swap, not a full rewrite.")

    return f"""
<View>
  <View style="background:#f0f4f8;border:1px solid #cbd5e1;padding:12px;border-radius:4px;margin-bottom:16px;">
    <Header value="Reviewer guidelines" size="4"/>
    <HyperText name="guidelines" value="{guidelines_attr}"/>
  </View>

  <Header value="Original English Query"/>
  <Text name="source" value="$english_source"/>
{para_block}
{syno_block}
</View>
""".strip()


def delete_project_if_exists(s, title):
    resp = s.get(f"{LS_URL}/api/projects", params={"page_size": 200})
    resp.raise_for_status()
    for p in resp.json().get("results", []):
        if p["title"] == title:
            s.delete(f"{LS_URL}/api/projects/{p['id']}").raise_for_status()
            print(f"  Deleted existing project '{title}' (id={p['id']}) -- rebuilding with QA warnings.")


def get_or_create_project(s, title, label_config):
    resp = s.get(f"{LS_URL}/api/projects", params={"page_size": 200})
    resp.raise_for_status()
    for p in resp.json().get("results", []):
        if p["title"] == title:
            print(f"  Project '{title}' already exists (id={p['id']}).")
            return p["id"]
    resp = s.post(f"{LS_URL}/api/projects", json={"title": title, "label_config": label_config})
    resp.raise_for_status()
    project_id = resp.json()["id"]
    print(f"  Created project '{title}' (id={project_id}).")
    return project_id


def format_qa_warning(qa_row):
    """Builds an HTML warning box from a QA row. Always returns a real,
    same-shaped box (same padding/border/margin) so there's no layout
    jump between flagged and clean rows and no risk of the HyperText
    field hitting an empty-value loading bug (confirmed real -- see
    LOG.md 2026-08-24) -- only the color changes: yellow and readable
    when something was flagged, white-on-white (present but invisible)
    when clean. Deliberately not a "no issues" message even in white: a
    checker-approved-looking badge, however subtle, risks automation
    bias -- reviewers trusting the verdict instead of reading closely.
    This box lives only in Label Studio's own (disposable, regenerated-
    from-source) task store, never in the canonical data/*.jsonl files --
    per the user's explicit acceptance of that tradeoff, on the condition
    that the eventual review-import script only pulls the reviewer's own
    annotation output, never a raw dump of task.data."""
    flags = None
    missing, added, dropped = [], [], {}
    if qa_row is not None:
        flags = qa_row.get("flags")
        if flags is None:
            flags = [qa_row.get("flag", "ok")]
        missing = qa_row.get("missing_numbers", [])
        added = qa_row.get("added_numbers", [])
        dropped = qa_row.get("dropped_markers", {})

    is_flagged = bool(flags) and flags != ["ok"]

    if not is_flagged:
        return (
            '<div style="background:#ffffff;border:1px solid #ffffff;padding:10px;'
            'border-radius:4px;margin-bottom:12px;">&nbsp;</div>'
        )

    parts = []
    if "number_mismatch" in flags:
        detail = []
        if missing:
            detail.append(f"number(s) present in the source but not found in this text: {missing}")
        if added:
            detail.append(f"number(s) in this text not found in the source: {added}")
        parts.append("Possible number mismatch -- " + "; ".join(detail))
    if "marker_dropped" in flags:
        parts.append(f"Possible dropped unit/exponent marker ({', '.join(dropped.keys())}) -- "
                      f"check units like m/s^2, x^2, etc. are still correctly conveyed")

    message = " | ".join(parts)
    return (
        '<div style="background:#fff3cd;border:1px solid #ffc107;padding:10px;'
        'border-radius:4px;margin-bottom:12px;">'
        "<strong>⚠️ Automated check flagged this item:</strong><br/>"
        f"{message}"
        "</div>"
    )


def build_qa_lookup(qa_path, key_fields):
    if not qa_path.exists():
        return {}
    lookup = {}
    with open(qa_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = tuple(row[k] for k in key_fields)
            lookup[key] = row
    return lookup


def get_existing_task_keys(s, project_id):
    """Returns the set of (base_id, perturbation_type) already imported, read from each task's data."""
    keys = set()
    page = 1
    while True:
        resp = s.get(f"{LS_URL}/api/tasks", params={"project": project_id, "page": page, "page_size": 200})
        if resp.status_code == 404:
            # Task count is an exact multiple of page_size -- the next
            # page is legitimately empty, but the API 404s instead of
            # returning an empty list. Treat as "no more pages."
            break
        resp.raise_for_status()
        results = resp.json().get("tasks", [])
        if not results:
            break
        for t in results:
            d = t["data"]
            keys.add((d["base_id"], d["perturbation_type"]))
        if len(results) < 200:
            break
        page += 1
    return keys


def import_tasks(s, project_id, tasks):
    if not tasks:
        print("  Nothing new to import.")
        return
    resp = s.post(f"{LS_URL}/api/projects/{project_id}/import", json=tasks)
    resp.raise_for_status()
    print(f"  Imported {len(tasks)} new task(s).")


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def setup_perturbation_review(s, reviewer_name=None, reset=False):
    """One task per question, source read once, PARA and SYNO shown
    together below it (see build_perturbation_pair_config) -- so the
    task key is base_id alone, not (base_id, perturbation_type) like
    every other project here. Kept as its own idempotency check rather
    than reusing get_existing_task_keys, which assumes the older
    per-type shape."""
    label = f"PARA/SYNO ({reviewer_name})" if reviewer_name else "PARA/SYNO"
    print(f"\n=== English {label} perturbation review ===")
    entries = load_jsonl(PERTURBATIONS_PATH)
    by_base_id = {}
    for e in entries:
        if e["perturbation_type"] in ("PARA", "SYNO"):
            by_base_id.setdefault(e["base_id"], {})[e["perturbation_type"]] = e
    qa_lookup = build_qa_lookup(PERTURBATIONS_QA_PATH, ("base_id", "perturbation_type"))

    title = f"PARA-SYNO Review (English) — {reviewer_name}" if reviewer_name else "PARA-SYNO Review (English)"
    if reset:
        delete_project_if_exists(s, title)
    config = build_perturbation_pair_config()
    project_id = get_or_create_project(s, title, config)

    existing_base_ids = set()
    page = 1
    while True:
        resp = s.get(f"{LS_URL}/api/tasks", params={"project": project_id, "page": page, "page_size": 200})
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        results = resp.json().get("tasks", [])
        if not results:
            break
        existing_base_ids.update(t["data"]["base_id"] for t in results)
        if len(results) < 200:
            break
        page += 1

    tasks = []
    for base_id, by_type in by_base_id.items():
        if base_id in existing_base_ids:
            continue
        if "PARA" not in by_type or "SYNO" not in by_type:
            print(f"  WARNING: {base_id} missing PARA or SYNO row, skipping.")
            continue
        para_qa = qa_lookup.get((base_id, "PARA"))
        syno_qa = qa_lookup.get((base_id, "SYNO"))
        tasks.append({"data": {
            "base_id": base_id,
            "english_source": by_type["PARA"]["source_text"],
            "para_text": by_type["PARA"]["text"],
            "para_qa_warning_html": format_qa_warning(para_qa),
            "syno_text": by_type["SYNO"]["text"],
            "syno_qa_warning_html": format_qa_warning(syno_qa),
        }})
    import_tasks(s, project_id, tasks)


def setup_translation_review(s, lang, reviewer_name=None, reset=False):
    """reviewer_name, when given, makes this an independent, fully-separate
    copy of the language's task set for that specific person -- see
    LOG.md 2026-08-24 (two-reviewer design) for why: Label Studio can't
    reliably hide one reviewer's answers from another within a shared
    project, so each reviewer gets their own project instead."""
    lang_name = LANG_NAMES[lang]
    label = f"{lang_name} ({reviewer_name})" if reviewer_name else lang_name
    print(f"\n=== {label} translation review ===")
    entries = load_jsonl(TRANSLATIONS_PATH)
    rows = [e for e in entries if e["language"] == lang]
    if not rows:
        print(f"  No {lang_name} translation data found, skipping.")
        return
    qa_lookup = build_qa_lookup(TRANSLATIONS_QA_PATH, ("base_id", "language", "perturbation_type"))

    title = f"{lang_name} Translation Review — {reviewer_name}" if reviewer_name else f"{lang_name} Translation Review"
    if reset:
        delete_project_if_exists(s, title)
    config = build_labeling_config("English Source", f"{lang_name} Translation", TRANSLATION_GUIDELINES)
    project_id = get_or_create_project(s, title, config)
    existing = get_existing_task_keys(s, project_id)

    tasks = []
    for r in rows:
        key = (r["base_id"], r["perturbation_type"])
        if key in existing:
            continue
        qa_row = qa_lookup.get((r["base_id"], lang, r["perturbation_type"]))
        tasks.append({"data": {
            "base_id": r["base_id"],
            "perturbation_type": r["perturbation_type"],
            "language": lang,
            "english_source": r["source_text"],
            "target_text": r["text"],
            "qa_warning_html": format_qa_warning(qa_row),
        }})
    import_tasks(s, project_id, tasks)


def main():
    global LS_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["local", "render"], default="local")
    args = parser.parse_args()

    if args.target == "render":
        if not (RENDER_LS_URL and RENDER_LS_EMAIL and RENDER_LS_PASSWORD):
            print("ERROR: RENDER_LS_URL / RENDER_LS_EMAIL / RENDER_LS_PASSWORD not found in .env.")
            return
        LS_URL = RENDER_LS_URL
    else:
        if not LS_TOKEN:
            print("ERROR: LABEL_STUDIO_API_TOKEN not found in .env.")
            return

    s = session(args.target)
    try:
        resp = s.get(f"{LS_URL}/api/version", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: could not reach Label Studio at {LS_URL} ({e}). Is the server running?")
        return

    # Current annotator roster (updated 2026-08-25). Tamil, Gujarati, and
    # now Hindi each have two independent reviewers -- each gets their
    # own full copy per the two-reviewer design (LOG.md), so Cycle 1
    # answers stay hidden from each other until Cycle 2 adjudication.
    REVIEWERS = {
        "ta": ["Rohan", "Dhayanidhi"],
        "gu": ["Dhruv Kunvarani", "Samarth"],
        "hi": ["Jayant Kapoor", "Anshul"],
    }
    PARA_SYNO_REVIEWERS = ["Jayant Kapoor", "Anshul"]

    # Delete the old generic (un-named) language projects -- superseded
    # by per-reviewer named ones below.
    for lang in REVIEWERS:
        delete_project_if_exists(s, f"{LANG_NAMES[lang]} Translation Review")
    delete_project_if_exists(s, "PARA-SYNO Review (English)")

    # reset=False throughout: these projects may already have real
    # reviewer progress on them -- resetting would destroy it. A brand
    # new reviewer_name always creates fresh regardless of this flag;
    # reset only matters for a project that already exists, which is
    # exactly the case to protect. (Lesson from the 2026-08-25
    # accidental-reset incident on the PARA-SYNO project.)
    for name in PARA_SYNO_REVIEWERS:
        setup_perturbation_review(s, reviewer_name=name, reset=False)
    for lang, names in REVIEWERS.items():
        for name in names:
            setup_translation_review(s, lang, reviewer_name=name, reset=False)

    print("\nDone. Reviewers can log in and will see only their own named project(s).")


if __name__ == "__main__":
    main()
