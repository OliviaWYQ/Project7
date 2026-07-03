#!/usr/bin/env python3
"""Check the AutoDL GR00T/LIBERO server and training environment.

Run from the Project7 root:
    conda activate gr00t
    python check_autodl_env.py
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
ISAAC_ROOT = PROJECT_ROOT / "Isaac-GR00T"
DATASET_ROOT = PROJECT_ROOT / "libero_object_no_noops_lerobot"
MODEL_ROOT = PROJECT_ROOT / "GR00T-N1-2B"
SERVER_ROOT = PROJECT_ROOT / "server"

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


def file_size_mb(path: Path) -> float:
    return path.stat().st_size / 1024 / 1024


def dir_size(path: Path) -> str:
    if not path.exists():
        return "missing"
    output = command_output(["du", "-sh", str(path)])
    return output.split()[0] if output and not output.startswith("<failed") else "unknown"


def check_python() -> None:
    print("\n== Python / Conda ==")
    version = sys.version_info
    py_detail = f"{platform.python_version()} ({sys.executable})"
    if version.major == 3 and version.minor == 10:
        ok("Python version", py_detail)
    else:
        fail("Python version", f"{py_detail}; GR00T N1 scripts expect Python 3.10.x")

    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if conda_env == "gr00t":
        ok("Conda env", conda_env)
    else:
        warn("Conda env", f"{conda_env or '<none>'}; expected gr00t")

    proxy_vars = {
        key: value
        for key, value in os.environ.items()
        if "proxy" in key.lower() and value
    }
    if not proxy_vars:
        ok("Proxy variables", "none")
    elif any("127.0.0.1:7890" in value for value in proxy_vars.values()):
        warn("Proxy variables", f"{proxy_vars}; unset if pip cannot connect")
    else:
        warn("Proxy variables", str(proxy_vars))


def check_paths() -> None:
    print("\n== Project Paths ==")
    ok("Project root", str(PROJECT_ROOT))

    for name, path in [
        ("Isaac-GR00T", ISAAC_ROOT),
        ("server", SERVER_ROOT),
        ("dataset", DATASET_ROOT),
        ("GR00T-N1-2B", MODEL_ROOT),
    ]:
        if path.exists():
            ok(name, str(path))
        else:
            fail(name, f"missing: {path}")


def check_isaac_structure() -> None:
    print("\n== Isaac-GR00T Source Structure ==")
    required = [
        ISAAC_ROOT / "pyproject.toml",
        ISAAC_ROOT / "gr00t/experiment/data_config.py",
        ISAAC_ROOT / "gr00t/data/dataset.py",
        ISAAC_ROOT / "scripts/gr00t_finetune.py",
    ]
    for path in required:
        if path.exists():
            ok("required source file", str(path.relative_to(PROJECT_ROOT)))
        else:
            fail("required source file", f"missing: {path.relative_to(PROJECT_ROOT)}")

    if (ISAAC_ROOT / ".git").exists():
        branch = command_output(["git", "-C", str(ISAAC_ROOT), "branch", "--show-current"])
        commit = command_output(["git", "-C", str(ISAAC_ROOT), "rev-parse", "--short", "HEAD"])
        if branch == "n1-release":
            ok("Isaac-GR00T branch", f"{branch} @ {commit}")
        else:
            warn("Isaac-GR00T branch", f"{branch or '<detached>'} @ {commit}; expected n1-release")

    copied_scripts = [
        ISAAC_ROOT / "scripts/gr00t_finetune_libero.py",
        ISAAC_ROOT / "scripts/gr00t_primitive_libero.py",
    ]
    for path in copied_scripts:
        if path.exists():
            ok("copied training script", str(path.relative_to(PROJECT_ROOT)))
        else:
            warn("copied training script", f"missing: {path.relative_to(PROJECT_ROOT)}")


def check_torch() -> None:
    print("\n== Torch / CUDA ==")
    torch = import_module("torch")
    if torch is None:
        return

    detail = f"torch={torch.__version__}, torch.cuda={getattr(torch.version, 'cuda', None)}"
    ok("import torch", detail)

    if torch.cuda.is_available():
        try:
            device = torch.cuda.get_device_name(0)
        except Exception as exc:  # noqa: BLE001
            device = f"<device name failed: {exc}>"
        ok("CUDA available", device)
    else:
        fail("CUDA available", "torch.cuda.is_available() is False")


def check_python_imports() -> None:
    print("\n== Python Imports ==")
    for module_name in [
        "gr00t",
        "openpi_client",
        "transformers",
        "decord",
        "tyro",
        "websockets",
        "msgpack",
    ]:
        module = import_module(module_name)
        if module is not None:
            ok(f"import {module_name}", getattr(module, "__file__", "<namespace>"))

    flash_attn = importlib.util.find_spec("flash_attn")
    if flash_attn is not None:
        ok("flash_attn", "installed")
    else:
        warn("flash_attn", "not installed; can continue if PyTorch attention fallback works")


def check_gr00t_patches() -> None:
    print("\n== GR00T LIBERO Patches ==")
    try:
        from gr00t.experiment.data_config import DATA_CONFIG_MAP

        if "franka" in DATA_CONFIG_MAP:
            ok("DATA_CONFIG_MAP['franka']", "present")
        else:
            fail("DATA_CONFIG_MAP['franka']", f"missing; keys={list(DATA_CONFIG_MAP.keys())}")
    except Exception as exc:  # noqa: BLE001
        fail("DATA_CONFIG_MAP import", repr(exc))

    try:
        from gr00t.data.dataset import LiberoSingleDataset

        ok("LiberoSingleDataset", str(LiberoSingleDataset))
    except Exception as exc:  # noqa: BLE001
        fail("LiberoSingleDataset import", repr(exc))


def check_dataset() -> None:
    print("\n== LIBERO Dataset ==")
    if not DATASET_ROOT.exists():
        fail("dataset directory", f"missing: {DATASET_ROOT}")
        return

    ok("dataset size", dir_size(DATASET_ROOT))
    file_count = sum(1 for path in DATASET_ROOT.rglob("*") if path.is_file())
    if file_count > 0:
        ok("dataset files", str(file_count))
    else:
        fail("dataset files", "0")

    meta_dir = DATASET_ROOT / "meta"
    required_meta = [
        "info.json",
        "episodes.jsonl",
        "episodes_stats.jsonl",
        "tasks.jsonl",
        "modality.json",
    ]
    for filename in required_meta:
        path = meta_dir / filename
        if path.exists():
            ok("dataset meta", str(path.relative_to(PROJECT_ROOT)))
        else:
            fail("dataset meta", f"missing: {path.relative_to(PROJECT_ROOT)}")

    info_path = meta_dir / "info.json"
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text())
            detail = (
                f"episodes={info.get('total_episodes')}, "
                f"frames={info.get('total_frames')}, "
                f"videos={info.get('total_videos')}, fps={info.get('fps')}"
            )
            ok("dataset info", detail)
        except Exception as exc:  # noqa: BLE001
            fail("dataset info", repr(exc))


def check_model() -> None:
    print("\n== Base Model / Checkpoints ==")
    if not MODEL_ROOT.exists():
        fail("base model directory", f"missing: {MODEL_ROOT}")
        return

    ok("base model size", dir_size(MODEL_ROOT))
    for filename in ["config.json", "model.safetensors"]:
        path = MODEL_ROOT / filename
        if not path.exists():
            fail("base model file", f"missing: {path.relative_to(PROJECT_ROOT)}")
            continue
        size = file_size_mb(path)
        if filename == "model.safetensors" and size < 1024:
            fail(
                "base model file",
                f"{path.relative_to(PROJECT_ROOT)} is only {size:.1f} MB; git-lfs may not have downloaded weights",
            )
        else:
            ok("base model file", f"{path.relative_to(PROJECT_ROOT)} ({size:.1f} MB)")

    output_dir = PROJECT_ROOT / "output"
    if output_dir.exists():
        checkpoints = sorted(output_dir.rglob("checkpoint-*"))
        if checkpoints:
            ok("checkpoints", ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in checkpoints[:5]))
        else:
            warn("checkpoints", f"none under {output_dir.relative_to(PROJECT_ROOT)} yet")
    else:
        warn("checkpoints", "output directory does not exist yet")


def check_server_files() -> None:
    print("\n== Server Files ==")
    for path in [
        SERVER_ROOT / "serve_policy.py",
        SERVER_ROOT / "websocket_policy_server.py",
        SERVER_ROOT / "openpi-client/pyproject.toml",
        SERVER_ROOT / "patches/apply.py",
    ]:
        if path.exists():
            ok("server file", str(path.relative_to(PROJECT_ROOT)))
        else:
            fail("server file", f"missing: {path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    check_python()
    check_paths()
    check_isaac_structure()
    check_torch()
    check_python_imports()
    check_gr00t_patches()
    check_dataset()
    check_model()
    check_server_files()

    failed = [item for item in results if not item[1]]
    warnings = [item for item in results if item[1] and item[2].startswith("WARN:")]

    print("\n== Summary ==")
    print(f"checks={len(results)}, failed={len(failed)}, warnings={len(warnings)}")
    if failed:
        print("\nFailed checks:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1

    print("Environment looks ready for 1-step training / server smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
