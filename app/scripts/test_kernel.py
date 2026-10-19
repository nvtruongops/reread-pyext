import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from reread_pyext.kernel import TranslationKernel

def main():
    print("Initializing TranslationKernel...")
    kernel = TranslationKernel()
    test_cases = [
        # English -> Vietnamese
        "Artificial intelligence and deep learning are transforming modern software.",
        # Vietnamese -> English (Reverse translate)
        "Dự án này giúp dịch ngoại tuyến khi bôi đen bất kỳ đoạn văn nào trên máy tính.",
        # Chinese -> Vietnamese (Pivot zh -> en -> vi)
        "深度学习改变了自然语言处理的技术方案。",
        # Japanese -> Vietnamese (Pivot ja -> en -> vi)
        "デスクトップ上で選択したテキストを即座に翻訳します。"
    ]

    print("\n=== Running Multi-Language Kernel Translations ===\n")
    failures = 0
    try:
        kernel.start()
        print("Kernel started successfully!")

        for text in test_cases:
            res = kernel.translate(text)
            print(f"[{res.src_lang.upper()} -> {res.tgt_lang.upper()}] (Route: {' -> '.join(res.pipeline)}, {res.duration_ms:.0f}ms)")
            print(f"SRC: {res.source_text}")
            print(f"TGT: {res.translated_text}")
            if res.error:
                failures += 1
                print(f"ERR: {res.error}")
            elif not res.pipeline or not res.translated_text.strip():
                failures += 1
                print("ERR: Translation returned no result.")
            print("-" * 60)
    finally:
        kernel.stop()
        print("\nKernel stopped cleanly.")

    if failures:
        print(f"Kernel test failed: {failures} of {len(test_cases)} translations failed.")
        return 1

    print("Kernel test passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
