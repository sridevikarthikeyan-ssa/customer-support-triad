import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

URL = "http://localhost:11434/api/generate"

def call_llm(prompt):
    start_time = datetime.now()
    start_ts = time.time()
    print(f"[{start_time.strftime('%H:%M:%S')}] ⏳ Started: {prompt}")

    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    try:
        resp = requests.post(URL, json=payload, timeout=60)
        resp.raise_for_status()
        output = resp.json().get("response", "")
    except Exception as e:
        output = f"Error: {e}"

    end_time = datetime.now()
    end_ts = time.time()
    elapsed = round(end_ts - start_ts, 2)

    print(f"[{end_time.strftime('%H:%M:%S')}] ✅ Finished: {prompt} in {elapsed} sec")
    return {
        "prompt": prompt,
        "start": start_time.strftime('%H:%M:%S'),
        "end": end_time.strftime('%H:%M:%S'),
        "time": elapsed,
        "output": output
    }

def main():
    # Generate 20 short prompts to test parallelism
    prompts = [f"Short prompt {i}" for i in range(1, 21)]

    results = []
    with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
        futures = [executor.submit(call_llm, p) for p in prompts]
        for f in as_completed(futures):
            results.append(f.result())

    print("\n=== Summary ===")
    for r in results:
        print(f"{r['prompt']} | Start: {r['start']} | End: {r['end']} | Time: {r['time']} sec")

if __name__ == "__main__":
    main()
