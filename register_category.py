"""
register_category.py

General-purpose version of the earlier patch_category_mapping.py --
registers any number of new category names with BFCL so
--test-category accepts them. Safe to re-run; skips anything already
registered.

USAGE:
    python register_category.py simple_python_hi_pt
    python register_category.py simple_python_hi_pre simple_python_hi_post
"""

import sys

PATH = "bfcl_eval/constants/category_mapping.py"
ANCHOR = '    "simple_python",\n'


def main():
    categories = sys.argv[1:]
    if not categories:
        print("Usage: python register_category.py <category_name> [<category_name> ...]")
        sys.exit(1)

    with open(PATH, "r") as f:
        content = f.read()

    if ANCHOR not in content:
        print("ERROR: expected anchor text not found. Paste this message back to Claude.")
        sys.exit(1)

    added = []
    for cat in categories:
        marker = f'    "{cat}",\n'
        if marker in content:
            print(f"  {cat}: already registered, skipping")
            continue
        content = content.replace(ANCHOR, ANCHOR + marker, 1)
        added.append(cat)

    if added:
        with open(PATH, "w") as f:
            f.write(content)
        print(f"Registered: {', '.join(added)}")
    else:
        print("Nothing new to register.")


if __name__ == "__main__":
    main()
