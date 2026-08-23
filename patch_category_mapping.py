"""
patch_category_mapping.py

Registers "simple_python_hi" and "simple_python_ta" as valid BFCL test
categories by adding them to NON_LIVE_CATEGORY in category_mapping.py.

Run this once, from inside the berkeley-function-call-leaderboard folder:
    python patch_category_mapping.py
"""

path = "bfcl_eval/constants/category_mapping.py"

with open(path, "r") as f:
    content = f.read()

old = '    "simple_python",\n    "simple_java",'
new = '    "simple_python",\n    "simple_python_hi",\n    "simple_python_ta",\n    "simple_java",'

if "simple_python_hi" in content:
    print("Already patched -- no changes made.")
elif old not in content:
    print("ERROR: expected text not found in the file. Paste this message back to Claude.")
else:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Patched:", path)
    print("Added simple_python_hi and simple_python_ta as valid test categories.")
