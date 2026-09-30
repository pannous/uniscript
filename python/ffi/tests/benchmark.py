"""Native (pure Python) vs FFI (Rust through PyO3): python3 benchmark.py [repetitions]"""

import subprocess
import sys
import time
from pathlib import Path

import native_package
import uniscript

REPOSITORY = Path(__file__).resolve().parents[3]
DOCUMENT = (REPOSITORY / "README.md").read_text() + (REPOSITORY / "docs" / "uniscript.md").read_text()
SHORT = "<:alpha> <:fracture A> <:mirror red R>"
REPETITIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
SHORT_REPETITIONS = REPETITIONS * 500


def seconds(action, repetitions):
    start = time.perf_counter()
    for _ in range(repetitions):
        action()
    return (time.perf_counter() - start) / repetitions


def import_seconds(code):
    start = time.perf_counter()
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).parent)
    return time.perf_counter() - start


def main():
    native = native_package.load()
    unicode = uniscript.convert(DOCUMENT)[0]
    tasks = {
        f"convert document ({len(DOCUMENT.encode()) // 1000} kB)": (lambda module: module.convert(DOCUMENT), REPETITIONS),
        f"to_uniscript document ({len(unicode.encode()) // 1000} kB)": (lambda module: module.to_uniscript(unicode), REPETITIONS),
        f"convert '{SHORT}'": (lambda module: module.convert(SHORT), SHORT_REPETITIONS),
    }
    print(f"{'task':<52}{'native':>12}{'ffi':>12}{'speedup':>10}")
    for task, (action, repetitions) in tasks.items():
        native_time = seconds(lambda: action(native), repetitions)
        ffi_time = seconds(lambda: action(uniscript), repetitions)
        print(f"{task:<52}{native_time * 1e3:>10.3f}ms{ffi_time * 1e3:>10.3f}ms{native_time / ffi_time:>9.1f}x")
    native_import = import_seconds("import native_package; native_package.load().convert('<:alpha>')")
    ffi_import = import_seconds("import uniscript; uniscript.convert('<:alpha>')")
    print(f"{'python start + import + first convert':<52}{native_import * 1e3:>10.1f}ms{ffi_import * 1e3:>10.1f}ms{native_import / ffi_import:>9.1f}x")


if __name__ == "__main__":
    main()
