#!/usr/bin/env python3
"""Check the local RTX 4070 LIBERO simulation/client environment.

Run from the Project7 root on the 4070 machine:
    conda activate gr00t_sim
    python check_4070_sim_env.py
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
SIM_ROOT = PROJECT_ROOT / "sim"
LIBERO_APP = SIM_ROOT / "libero"
LIBERO_THIRD_PARTY = SIM_ROOT / "third_party/libero"
OPENPI_CLIENT = SIM_ROOT / "openpi-client"

results: list[tuple[str, bool, str]] = []


def ok(name: str, detail: str = "") -> None:
    results.append((name, True, detail))
    print(f"[OK]   {name}{': ' + detail if detail else ''}")


def warn(name: str, detail: str = "") -> None:
    results.append((name, True, "WARN: " + detail))
    print(f"[WARN] {name}{': ' + detail if detail else ''}")


def fail(name: str, detail: str = "") -> None:
    results.append((name, False, detail))
    print(f"[FAIL] {name}{': ' + detail if detail else ''}")


def import_module(name: str) -> Any | None:
    try:
        return importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001
        fail(f"import {name}", repr(exc))
        return None


def command_output(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:  # noqa: BLE001
        return f"<failed: {exc}>"


def check_python() -> None:
    print("\n== Python / Conda ==")
    py_detail = f"{platform.python_version()} ({sys.executable})"
    if sys.version_info.major == 3 and sys.version_info.minor == 8:
        ok("Python version", py_detail)
    else:
        warn("Python version", f"{py_detail}; LIBERO example expects Python 3.8")

    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if conda_env == "gr00t_sim":
        ok("Conda env", conda_env)
    else:
        warn("Conda env", f"{conda_env or '<none>'}; expected gr00t_sim")

    proxy_vars = {
        key: value
        for key, value in os.environ.items()
        if "proxy" in key.lower() and value
    }
    if proxy_vars:
        warn("Proxy variables", str(proxy_vars))
    else:
        ok("Proxy variables", "none")


def check_paths() -> None:
    print("\n== Project Paths ==")
    ok("Project root", str(PROJECT_ROOT))
    for name, path in [
        ("sim", SIM_ROOT),
        ("sim/libero", LIBERO_APP),
        ("sim/openpi-client", OPENPI_CLIENT),
        ("sim/third_party/libero", LIBERO_THIRD_PARTY),
    ]:
        if path.exists():
            ok(name, str(path))
        else:
            fail(name, f"missing: {path}")

    for path in [
        LIBERO_APP / "main.py",
        LIBERO_APP / "requirements.txt",
        OPENPI_CLIENT / "pyproject.toml",
        LIBERO_THIRD_PARTY / "setup.py",
        LIBERO_THIRD_PARTY / "requirements.txt",
    ]:
        if path.exists():
            ok("required file", str(path.relative_to(PROJECT_ROOT)))
        else:
            fail("required file", f"missing: {path.relative_to(PROJECT_ROOT)}")


def check_nvidia() -> None:
    print("\n== NVIDIA / Torch ==")
    nvidia = command_output(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    if nvidia.startswith("<failed"):
        warn("nvidia-smi", nvidia)
    else:
        ok("nvidia-smi", nvidia)

    torch = importlib.util.find_spec("torch")
    if torch is None:
        warn("torch", "not installed; LIBERO sim may still run CPU/OpenGL, but robosuite deps often install torch")
        return

    torch_mod = import_module("torch")
    if torch_mod is None:
        return
    detail = f"torch={torch_mod.__version__}, cuda={getattr(torch_mod.version, 'cuda', None)}"
    if torch_mod.cuda.is_available():
        try:
            device = torch_mod.cuda.get_device_name(0)
        except Exception as exc:  # noqa: BLE001
            device = f"<device name failed: {exc}>"
        ok("torch CUDA", f"{detail}, device={device}")
    else:
        warn("torch CUDA", f"{detail}, torch.cuda.is_available() is False")


def check_imports() -> None:
    print("\n== Python Imports ==")
    for module_name in [
        "openpi_client",
        "websockets",
        "msgpack",
        "imageio",
        "numpy",
        "tyro",
        "tqdm",
        "libero",
        "robosuite",
        "mujoco",
    ]:
        module = import_module(module_name)
        if module is not None:
            ok(f"import {module_name}", getattr(module, "__file__", "<namespace>"))

    try:
        from libero.libero import benchmark
        from libero.libero.envs import OffScreenRenderEnv

        bench = benchmark.get_benchmark_dict()
        ok("LIBERO benchmark suites", ", ".join(sorted(bench.keys())[:8]))
        ok("OffScreenRenderEnv", str(OffScreenRenderEnv))
    except Exception as exc:  # noqa: BLE001
        fail("LIBERO benchmark import", repr(exc))


def check_main_import() -> None:
    print("\n== sim/libero/main.py ==")
    if str(LIBERO_APP) not in sys.path:
        sys.path.insert(0, str(LIBERO_APP))

    try:
        spec = importlib.util.spec_from_file_location("project7_libero_main", LIBERO_APP / "main.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot create import spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ok("load sim/libero/main.py", "module loaded")
        args_cls = getattr(module, "Args", None)
        if args_cls is not None:
            args = args_cls()
            ok("default server target", f"{args.host}:{args.port}")
            ok("default task suite", args.task_suite_name)
    except Exception as exc:  # noqa: BLE001
        fail("load sim/libero/main.py", repr(exc))


def check_runtime_hints() -> None:
    print("\n== Runtime Hints ==")
    display = os.environ.get("DISPLAY")
    if display:
        ok("DISPLAY", display)
    else:
        warn("DISPLAY", "not set; OffScreenRenderEnv may still work, but GUI rendering will not")

    gl = command_output(["bash", "-lc", "ldconfig -p | grep -E 'libGL.so|libEGL.so' | head -5"])
    if gl.startswith("<failed") or not gl:
        warn("OpenGL libs", "libGL/libEGL not found via ldconfig")
    else:
        ok("OpenGL libs", gl.replace("\n", " | "))

    print("\nServer tunnel command example:")
    print("  ssh -N -p 34087 -L 5555:127.0.0.1:5555 root@region-9.autodl.pro")
    print("\nSim smoke-test command example:")
    print("  cd sim/libero")
    print("  python main.py --host 127.0.0.1 --port 5555 --num-trials-per-task 1")


def main() -> int:
    check_python()
    check_paths()
    check_nvidia()
    check_imports()
    check_main_import()
    check_runtime_hints()

    failed = [item for item in results if not item[1]]
    warnings = [item for item in results if item[1] and str(item[2]).startswith("WARN:")]

    print("\n== Summary ==")
    print(f"checks={len(results)}, failed={len(failed)}, warnings={len(warnings)}")
    if failed:
        print("\nFailed checks:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1

    print("4070 sim environment looks ready for a server-connection smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
