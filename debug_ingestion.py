import json
import urllib.request

base_url = "http://localhost:8000/api"
wid = "09482e8b-bbe8-484d-9959-f928c10ffc46"
did = "d6851bf4-d86e-4db3-a42f-37818ff3f1b3"

def get_json(path):
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error {url}: {e}")
        return None

def debug_doc():
    doc = get_json(f"workspaces/{wid}/docs/{did}")
    if not doc: return
    print(f"File: {doc['file_name']}, Status: {doc['status']}")
    
    report = get_json(f"workspaces/{wid}/docs/{did}/ingestion-report")
    if report:
        print(f"Chunk Count: {report['chunk_count']}")
        print(f"Extracted Pages: {report['extracted_pages']}")
        if report.get('failed_pages'):
            print(f"Failed Pages: {json.dumps(report['failed_pages'], indent=2, ensure_ascii=False)}")

    # List chunks via direct DB model access would be better, 
    # but we can hack it by searching with an empty query (or similar) 
    # if the API supports listing chunks. 
    # Let's check chunks via a retrieval-like approach if possible.
    
    # Actually, I'll just check the search result for the specific query mentioned by the user.
    query_url = f"{base_url}/workspaces/{wid}/chat/query"
    query_data = json.dumps({"query": "アポ長印刷"}).encode("utf-8")
    req = urllib.request.Request(query_url, data=query_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print("\n--- Search Result for 'アポ長印刷' ---")
            if not res.get("citations"):
                print("No citations found.")
                # Show what was actually indexed
                print("Search raw result (conclusion):", res.get("answer", {}).get("conclusion"))
            else:
                for cit in res["citations"]:
                    print(f"File: {cit['file_name']}, Ref: {cit['ref']}, Snippet: {cit['snippet']}")
    except Exception as e:
        print(f"Search error: {e}")

if __name__ == "__main__":
    debug_doc()
