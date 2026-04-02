import json
import urllib.request

base_url = "http://localhost:8000/api"

def get_json(path):
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error {url}: {e}")
        return None

def inventory():
    workspaces = get_json("workspaces")
    if not workspaces:
        print("No workspaces found.")
        return
    
    for ws in workspaces:
        wid = ws["id"]
        print(f"Workspace: {ws.get('name', wid)} ({wid})")
        docs = get_json(f"workspaces/{wid}/docs")
        if not docs:
            print("  No documents.")
            continue
        for doc in docs:
            print(f"  Doc: {doc['file_name']} (ID: {doc['id']})")
            print(f"    Status: {doc['status']}, Mime: {doc.get('mime_type', doc.get('mime'))}")
            if doc.get('fail_reason'):
                print(f"    Fail Reason: {doc['fail_reason']}")

if __name__ == "__main__":
    inventory()
