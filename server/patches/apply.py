#!/usr/bin/env python3
"""将文档要求的代码修改自动注入到 Isaac-GR00T 源码中。

可以在项目根目录直接运行：
    python server/patches/apply.py

也可以通过环境变量指定 Isaac-GR00T 路径：
    GR00T_ROOT=/path/to/Isaac-GR00T python server/patches/apply.py
"""

import os
import re
import shutil
from pathlib import Path

PATCHES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PATCHES_DIR.parents[1]


def find_gr00t_root() -> Path:
    env_root = os.environ.get("GR00T_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.extend(
        [
            PROJECT_ROOT / "Isaac-GR00T",
            Path.cwd() / "Isaac-GR00T",
            Path("/workspace/Isaac-GR00T"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    searched = "\n  - ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "未找到 Isaac-GR00T 源码目录。请在 Project7 根目录运行，"
        "或设置 GR00T_ROOT=/path/to/Isaac-GR00T。\n已检查：\n  - "
        + searched
    )


GR00T_ROOT = find_gr00t_root()
print(f"使用 Isaac-GR00T 路径: {GR00T_ROOT}")


def find_source_file(root: Path, relative_path: str, filename: str) -> Path:
    preferred = root / relative_path
    if preferred.exists():
        return preferred

    matches = sorted(
        path
        for path in root.rglob(filename)
        if ".git" not in path.parts and path.is_file()
    )
    if len(matches) == 1:
        return matches[0]
    if matches:
        formatted = "\n  - ".join(str(path) for path in matches)
        raise RuntimeError(
            f"找到多个 {filename}，请设置正确的 GR00T_ROOT 或手动检查：\n  - {formatted}"
        )
    raise FileNotFoundError(
        f"在 {root} 下找不到 {relative_path}，也没有搜索到 {filename}。"
        "请确认 Isaac-GR00T 是否 clone 完整，或运行 find Isaac-GR00T -name "
        f"'{filename}' 检查实际路径。"
    )


def backup_once(path: Path) -> None:
    backup_path = path.with_suffix(path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)


def remove_existing_franka_class(content: str) -> str:
    pattern = (
        r"\n\nclass FrankaDataConfig\(BaseDataConfig\):"
        r".*?"
        r"(?=\n\n(?:class |DATA_CONFIG_MAP\s*=|#)|\Z)"
    )
    return re.sub(pattern, "", content, flags=re.DOTALL)


# ── 补丁 1: data_config.py ──────────────────────────────────
# 1a. 追加 FrankaDataConfig 类
# 1b. 在 DATA_CONFIG_MAP 末尾插入 "franka" 条目

DATA_CONFIG_PATH = find_source_file(
    GR00T_ROOT,
    "gr00t/experiment/data_config.py",
    "data_config.py",
)
print(f"修改 data_config.py: {DATA_CONFIG_PATH}")
franka_class = (PATCHES_DIR / "franka_data_config.py").read_text().strip()

with open(DATA_CONFIG_PATH, "r") as f:
    content = f.read()

# 1a: 确保 FrankaDataConfig 定义在 DATA_CONFIG_MAP 之前
content = remove_existing_franka_class(content)
if "DATA_CONFIG_MAP" not in content:
    raise RuntimeError(f"{DATA_CONFIG_PATH} 中未找到 DATA_CONFIG_MAP")
content, count = re.subn(
    r"\n(DATA_CONFIG_MAP\s*=)",
    lambda match: "\n\n" + franka_class + "\n\n" + match.group(1),
    content,
    count=1,
)
if count == 0:
    raise RuntimeError(f"{DATA_CONFIG_PATH} 中 DATA_CONFIG_MAP 格式不符合预期")
print("✅ 已注入 FrankaDataConfig")

# 1b: 在 DATA_CONFIG_MAP 末尾插入 "franka" 条目
if '"franka"' not in content:
    pattern = r'(DATA_CONFIG_MAP\s*=\s*\{[^}]*?)\n(\})'
    replacement = r'\1\n    "franka": FrankaDataConfig(),\n\2'
    content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count > 0:
        print("✅ 已注入 franka 到 DATA_CONFIG_MAP")
    else:
        print("⚠️  DATA_CONFIG_MAP 注入失败，请手动添加")
else:
    print("ℹ️  DATA_CONFIG_MAP 已包含 franka，跳过")

# 写回
backup_once(DATA_CONFIG_PATH)
with open(DATA_CONFIG_PATH, "w") as f:
    f.write(content)

# ── 补丁 2: dataset.py ──────────────────────────────────────
# 追加 LiberoSingleDataset 类

DATASET_PATH = find_source_file(
    GR00T_ROOT,
    "gr00t/data/dataset.py",
    "dataset.py",
)
print(f"修改 dataset.py: {DATASET_PATH}")
libero_class = (PATCHES_DIR / "libero_single_dataset.py").read_text()

with open(DATASET_PATH, "r") as f:
    content = f.read()

if "class LiberoSingleDataset" not in content:
    content += "\n\n" + libero_class
    print("✅ 已注入 LiberoSingleDataset")
else:
    print("ℹ️  dataset.py 已包含 LiberoSingleDataset，跳过")

backup_once(DATASET_PATH)
with open(DATASET_PATH, "w") as f:
    f.write(content)

print("🎉 所有补丁已应用")
