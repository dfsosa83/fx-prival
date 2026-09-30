"""Inspect the reference notebook structure."""
import json
from pathlib import Path

p = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\notebooks\eurusd\eurusd_sell_improved.ipynb")
with open(p, "r", encoding="utf-8") as f:
    nb = json.load(f)

print("Cells:", len(nb["cells"]))
for i, c in enumerate(nb["cells"]):
    src = "".join(c["source"])
    first_line = src.strip().split("\n")[0][:120] if src.strip() else "(empty)"
    print(f"Cell {i} [{c['cell_type']}]: {first_line}")