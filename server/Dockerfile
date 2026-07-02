# ============================================================
# GR00T N1 服务端推理 — A100-PCIE-40GB 云服务器
# 基于 CUDA 13.0 + PyTorch 2.7.0 + Python 3.11
#
# 构建（在 Project7 根目录执行）：
#   docker build -f server/Dockerfile -t gr00t-server .
# ============================================================

FROM nvidia/cuda-samples/CUDA13.0-Torch2.7.0-Python3.11:v2

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/workspace:/workspace/Isaac-GR00T:${PYTHONPATH}

# ---------- 系统依赖 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    git git-lfs \
    build-essential cmake \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
    ffmpeg \
    vim wget curl ca-certificates \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- pip 国内镜像（云服务器加速） ----------
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install --upgrade pip setuptools wheel

# ---------- 基础推理依赖 ----------
RUN pip install \
    gpustat \
    wandb \
    transformers \
    accelerate \
    datasets \
    decord \
    tyro \
    websockets \
    msgpack \
    dm-tree \
    pillow

# ---------- 安装 Isaac-GR00T ----------
WORKDIR /workspace
RUN git clone https://github.com/NVIDIA/Isaac-GR00T.git
WORKDIR /workspace/Isaac-GR00T
# 先装依赖，再装 gr00t（跳过 torch 等已存在的包避免版本冲突）
RUN pip install -e . --no-deps
RUN pip install -e .

# ---------- flash-attn（CUDA 13.0 兼容性需实测） ----------
# 如果编译失败，注释掉这行后重试——推理时无 flash-attn 会 fallback 到 PyTorch 原生 attention
RUN pip install --no-build-isolation flash-attn==2.7.1.post4 2>/dev/null || \
    echo "⚠ flash-attn 编译失败，将使用 PyTorch 原生 attention（推理速度略慢）"

# ---------- 卸载冲突包 ----------
RUN pip uninstall -y transformer-engine 2>/dev/null || true

# ---------- 注入代码补丁（FrankaDataConfig + LiberoSingleDataset） ----------
COPY server/patches /workspace/server/patches
RUN python /workspace/server/patches/apply.py

# ---------- 安装 openpi-client（websocket 通信） ----------
WORKDIR /workspace
COPY server/openpi-client /workspace/server/openpi-client
RUN pip install -e /workspace/server/openpi-client

# ---------- 复制服务端代码 ----------
COPY server/serve_policy.py /workspace/server/serve_policy.py
COPY server/websocket_policy_server.py /workspace/server/websocket_policy_server.py
COPY server/inference_service.py /workspace/server/inference_service.py
COPY modality.json /workspace/modality.json

WORKDIR /workspace

CMD ["/bin/bash"]
