import json

with open('assistant-virtual-463018-4f3563bb2363.json') as f:
    creds = json.load(f)

json_str = json.dumps(creds).replace("\n", "\\n")
print(json_str)
