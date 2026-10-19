import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from reread_pyext.models import ModelRegistry, ModelStore

def main():
    registry = ModelRegistry()
    store = ModelStore()

    print(f"Total models registered: {len(registry.list_pairs())}")
    installed = store.list_installed_pairs()
    print(f"Installed pairs locally: {installed}")

    for pair in ["envi", "vien", "zhen", "jaen"]:
        meta = registry.get(pair)
        if meta:
            files_status = store.get_model_files(pair)
            status_str = "READY" if files_status else "NOT LOADED / GZ ONLY"
            print(f" - {pair} ({meta.src_lang} -> {meta.tgt_lang}): {status_str} [Download: {meta.download_bytes / 1024 / 1024:.1f} MB, Unpacked: {meta.unpacked_bytes / 1024 / 1024:.1f} MB]")
        else:
            print(f" - {pair}: NOT FOUND in registry")

if __name__ == "__main__":
    main()
