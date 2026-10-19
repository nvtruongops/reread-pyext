import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from reread_pyext.models import ModelDownloader

def progress_cb(msg: str, current: int, total: int):
    if total > 0:
        pct = (current / total) * 100
        print(f"\r[{pct:5.1f}%] {msg}", end="", flush=True)
    else:
        print(f"\n{msg}")

def main():
    downloader = ModelDownloader()
    target_pairs = ["zhen", "jaen"]
    print(f"Starting download of requested models: {target_pairs}...")

    for pair in target_pairs:
        print(f"\n=== Downloading model pair: {pair} ===")
        try:
            downloader.download_pair(pair, on_progress=progress_cb)
            print(f"\nSuccessfully downloaded and verified pair: {pair}")
        except Exception as e:
            print(f"\nFailed to download {pair}: {e}")

if __name__ == "__main__":
    main()
