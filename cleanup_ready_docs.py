import json
import urllib.request
import urllib.error

base_url = "http://localhost:8000/api"

def request(path, method="GET"):
    url = f"{base_url}/{path.lstrip('/')}"
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def cleanup():
    # 1. Get all workspaces
    workspaces = request("workspaces")
    if workspaces is None:
        return
    
    for ws in workspaces:
        wid = ws["id"]
        print(f"Checking workspace: {ws.get('name', wid)} ({wid})")
        
        # 2. Get all documents in workspace
        docs = request(f"workspaces/{wid}/docs")
        if docs is None:
            continue
            
        for doc in docs:
            if doc["status"] == "ready":
                did = doc["id"]
                file_name = doc["file_name"]
                print(f"  Deleting ready document: {file_name} ({did})")
                
                # 3. Delete document
                request(f"workspaces/{wid}/docs/{did}", method="DELETE")
                print(f"    Successfully deleted {file_name}")

if __name__ == "__main__":
    cleanup()
