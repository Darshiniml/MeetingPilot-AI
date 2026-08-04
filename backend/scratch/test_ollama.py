import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url_embed = "http://127.0.0.1:11434/api/embed"
url_embeddings = "http://127.0.0.1:11434/api/embeddings"
model = "nomic-embed-text"

def try_endpoint(url, payload):
    print(f"Testing URL: {url} ...")
    req = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f" -> SUCCESS! Keys returned: {list(data.keys())}")
            if "embeddings" in data:
                print(f" -> Number of embeddings: {len(data['embeddings'])}")
            if "embedding" in data:
                print(f" -> Embedding length: {len(data['embedding'])}")
            return True
    except HTTPError as e:
        print(f" -> HTTP Error: {e.code} {e.reason}")
    except Exception as e:
        print(f" -> Connection Error: {e}")
    return False

print("=== Ollama Embedding Test ===")
try:
    with urlopen("http://127.0.0.1:11434/api/tags") as resp:
        print("Models list:", json.loads(resp.read().decode()))
except Exception as e:
    print("Error listing tags:", e)

# Try batch /api/embed
payload_embed = {"model": model, "input": ["Hello world"]}
success_embed = try_endpoint(url_embed, payload_embed)

# Try single /api/embeddings
payload_embeddings = {"model": model, "prompt": "Hello world"}
success_embeddings = try_endpoint(url_embeddings, payload_embeddings)
