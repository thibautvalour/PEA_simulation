"""Parameter loader"""

import json

with open("parameters.json", encoding="utf-8") as f:
    params = json.load(f)
