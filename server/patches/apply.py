#!/usr/bin/env python3
"""将文档要求的代码修改自动注入到 Isaac-GR00T 源码中。

由 server/Dockerfile 在构建时调用：
    python /workspace/server/patches/apply.py
"""

import re
import shutil
from pathlib import Path

PATCHES_DIR = Path(__file__).resolve().parent
GR00T_ROOT = Path("/workspace/Isaac-GR00T")

# ── 补丁 1: data_config.py ──────────────────────────────────
# 1a. 追加 FrankaDataConfig 类
# 1b. 在 DATA_CONFIG_MAP 末尾插入 "franka" 条目

DATA_CONFIG_PATH = GR00T_ROOT / "gr00t/experiment/data_config.py"
franka_class = (PATCHES_DIR / "franka_data_config.py").read_text()

with open(DATA_CONFIG_PATH, "r") as f:
    content = f.read()

# 1a: 追加 FrankaDataConfig 类（如果还没加过）
if "class FrankaDataConfig" not in content:
    content += "\n\n" + franka_class
    print("✅ 已注入 FrankaDataConfig")

# 1b: 在 DATA_CONFIG_MAP 末尾插入 "franka" 条目
if '"franka"' not in content:
    # 找 DATA_CONFIG_MAP = { 后，最后一个独立的 }
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
shutil.copy2(DATA_CONFIG_PATH, str(DATA_CONFIG_PATH) + ".bak")
with open(DATA_CONFIG_PATH, "w") as f:
    f.write(content)

# ── 补丁 2: dataset.py ──────────────────────────────────────
# 追加 LiberoSingleDataset 类

DATASET_PATH = GR00T_ROOT / "gr00t/data/dataset.py"
libero_class = (PATCHES_DIR / "libero_single_dataset.py").read_text()

with open(DATASET_PATH, "r") as f:
    content = f.read()

if "class LiberoSingleDataset" not in content:
    content += "\n\n" + libero_class
    print("✅ 已注入 LiberoSingleDataset")
else:
    print("ℹ️  dataset.py 已包含 LiberoSingleDataset，跳过")

shutil.copy2(DATASET_PATH, str(DATASET_PATH) + ".bak")
with open(DATASET_PATH, "w") as f:
    f.write(content)

print("🎉 所有补丁已应用")
