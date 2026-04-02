import json
import urllib.request
import sys

base_url = "http://localhost:8000/api"

def get_json(path):
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None

def inventory():
    workspaces = get_json("workspaces")
    if not workspaces:
        return
    
    with open("full_inventory.txt", "w", encoding="utf-8") as f:
        for ws in workspaces:
            wid = ws["id"]
            f.write(f"Workspace: {ws.get('name', wid)} ({wid})\n")
            docs = get_json(f"workspaces/{wid}/docs")
            if not docs:
                f.write("  No documents.\n")
                continue
            for doc in docs:
                f.write(f"  Doc: {doc['file_name']} (ID: {doc['id']})\n")
                f.write(f"    Status: {doc['status']}, Mime: {doc.get('mime_type', doc.get('mime'))}\n")
                if doc.get('fail_reason'):
                    f.write(f"    Fail Reason: {doc['fail_reason']}\n")

if __name__ == "__main__":
    inventory()
