"""Extract key methodology cells from the reference notebook."""
import json
from pathlib import Path

p = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\notebooks\eurusd\eurusd_sell_improved.ipynb")
with open(p, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Print cells 11 (feature engineering), 15-16 (label tuning), 25-30 (feature selection)
target_cells = [11, 15, 16, 24, 25, 26, 27, 28, 29, 30, 40]
for i in target_cells:
    if i >= len(nb["cells"]):
        continue
    c = nb["cells"][i]
    src = "".join(c["source"])
    print(f"=== CELL {i} ({c['cell_type']}) ===")
    print(src[:3000])
    print()