# GR00T-N1-2B Fine-tuning on LIBERO

Fine-tune NVIDIA [GR00T-N1-2B](https://huggingface.co/nvidia/GR00T-N1-2B) on the [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO) robotic manipulation benchmark. The project includes training scripts, a WebSocket-based inference server, and a LIBERO simulation client for evaluation.

## Project Tree

```
.
├── README.md
├── .dockerignore
├── .gitignore
├── check_4070_sim_env.py               # Check local sim (4070) environment
├── check_autodl_env.py                 # Check AutoDL server/training environment
├── download_from_oss.py                # Download dataset from Alibaba Cloud OSS
├── upload_to_oss.py                    # Upload dataset to Alibaba Cloud OSS
├── gr00t_finetune_libero.py            # Main training script (full fine-tune)
├── gr00t_primitive_libero.py           # Primitive action-head-only training
├── modality.json                       # Modality layout (state/action/video)
│
├── server/                             # Inference server (A100 cloud)
│   ├── Dockerfile                      # Server Docker build
│   ├── serve_policy.py                 # Policy serving entrypoint
│   ├── websocket_policy_server.py      # WebSocket-based policy server
│   ├── inference_service.py            # Inference service helpers
│   ├── patches/
│   │   ├── apply.py                    # Inject patches into Isaac-GR00T
│   │   ├── franka_data_config.py       # FrankaDataConfig for LIBERO
│   │   └── libero_single_dataset.py    # LiberoSingleDataset loader
│   └── openpi-client/                  # WebSocket client library
│       ├── pyproject.toml
│       └── src/openpi_client/
│           ├── base_policy.py
│           ├── websocket_client_policy.py
│           ├── msgpack_numpy.py
│           ├── image_tools.py
│           └── runtime/
│
└── sim/                                # LIBERO simulation client (RTX 4070)
    ├── libero/
    │   ├── README.md
    │   ├── Dockerfile
    │   ├── compose.yml
    │   ├── main.py                     # Eval entrypoint (connect to server)
    │   ├── requirements.in
    │   ├── requirements.txt
    │   └── convert_libero_data_to_lerobot.py
    └── openpi-client/                  # WebSocket client library (sim side)
        ├── pyproject.toml
        └── src/openpi_client/
```

**Directories NOT in this repo** (download/clone separately):

| Directory | Source | Size |
|-----------|--------|------|
| `Isaac-GR00T/` | `git clone https://github.com/NVIDIA/Isaac-GR00T.git` | ~426 MB |
| `GR00T-N1-2B/` | HuggingFace `nvidia/GR00T-N1-2B` | ~4 GB |
| `libero_object_no_noops_lerobot/` | Alibaba Cloud OSS (`gr00t` bucket) | dataset |
| `sim/third_party/` | `git submodule update --init` inside LIBERO | ~426 MB |
| `output/` | Created at runtime (training checkpoints) | - |

---

## Setup — Training Server (AutoDL A100)

### 1. Clone this repo

```bash
git clone <this-repo-url>
cd Project7
```

### 2. Clone Isaac-GR00T

```bash
git clone https://github.com/NVIDIA/Isaac-GR00T.git
cd Isaac-GR00T && git checkout n1-release && cd ..
```

### 3. Download the base model

```bash
# Option A: from HuggingFace (if network allows)
pip install huggingface_hub
huggingface-cli download nvidia/GR00T-N1-2B --local-dir GR00T-N1-2B

# Option B: from mirror
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download nvidia/GR00T-N1-2B --local-dir GR00T-N1-2B
```

### 4. Download the LIBERO dataset from OSS

```bash
export OSS_AK=<your-access-key>
export OSS_SK=<your-secret-key>
python download_from_oss.py
```

### 5. Install dependencies

```bash
conda create -n gr00t python=3.10 -y
conda activate gr00t

# Install Isaac-GR00T
cd Isaac-GR00T
pip install -e . --no-deps
pip install -e .
cd ..

# Install openpi-client (server side)
pip install -e server/openpi-client

# Additional deps
pip install transformers accelerate datasets decord tyro websockets msgpack wandb tensorboard
```

### 6. Apply LIBERO patches to Isaac-GR00T

```bash
python server/patches/apply.py
```

This injects `FrankaDataConfig` and `LiberoSingleDataset` into Isaac-GR00T's source.

### 7. Verify environment

```bash
conda activate gr00t
python check_autodl_env.py
```

---

## Training

Run training on the AutoDL A100. The inference server and the RTX 4070 simulation client are not needed during training; they are only needed when evaluating a saved checkpoint.

Set common paths first:

```bash
conda activate gr00t

export PROJECT_ROOT=/root/autodl-tmp/Project7
export ISAAC_ROOT=$PROJECT_ROOT/Isaac-GR00T
export DATASET_PATH=$PROJECT_ROOT/libero_object_no_noops_lerobot
export BASE_MODEL_PATH=$PROJECT_ROOT/GR00T-N1-2B
export OUTPUT_ROOT=$PROJECT_ROOT/output

cd $ISAAC_ROOT
```

### Control Group: checkpoint-1

This is the "before fine-tuning" baseline used by this project. It runs the same training script for only one optimization step, so the model becomes runnable with the Franka/LIBERO data config but is still almost the original GR00T-N1-2B behavior.

```bash
python scripts/gr00t_finetune_libero.py \
    --dataset-path $DATASET_PATH \
    --base-model-path $BASE_MODEL_PATH \
    --output-dir $OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_1 \
    --data-config franka \
    --batch-size 1 \
    --max-steps 1 \
    --save-steps 1 \
    --tune-visual \
    --tune-projector \
    --tune-diffusion-model \
    --num-gpus 1 \
    --learning-rate 1e-4 \
    --report-to tensorboard
```

Expected checkpoint:

```bash
$OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_1/checkpoint-1
```

### Fine-tuned Group: checkpoint-20000

This is the main experimental model. Keep the hyperparameters the same as the control group and change only the number of training steps, save interval, and output directory.

```bash
python scripts/gr00t_finetune_libero.py \
    --dataset-path $DATASET_PATH \
    --base-model-path $BASE_MODEL_PATH \
    --output-dir $OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_20000 \
    --data-config franka \
    --batch-size 1 \
    --max-steps 20000 \
    --save-steps 5000 \
    --tune-visual \
    --tune-projector \
    --tune-diffusion-model \
    --num-gpus 1 \
    --learning-rate 1e-4 \
    --report-to tensorboard
```

Expected final checkpoint:

```bash
$OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_20000/checkpoint-20000
```

Resume from the latest checkpoint:

```bash
python scripts/gr00t_finetune_libero.py \
    --dataset-path $DATASET_PATH \
    --base-model-path $BASE_MODEL_PATH \
    --output-dir $OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_20000 \
    --data-config franka \
    --batch-size 1 \
    --max-steps 20000 \
    --save-steps 5000 \
    --tune-visual \
    --tune-projector \
    --tune-diffusion-model \
    --num-gpus 1 \
    --learning-rate 1e-4 \
    --report-to tensorboard \
    --resume
```

### Experiment Comparison

| Group | Checkpoint | Training steps | Purpose |
|-------|------------|----------------|---------|
| Control | `checkpoint-1` | 1 | Baseline behavior before meaningful LIBERO fine-tuning |
| Fine-tuned | `checkpoint-20000` | 20000 | Main GR00T-N1 result after LIBERO fine-tuning |

Use the same evaluation settings for both checkpoints. For a quick smoke test, use `--num-trials-per-task 1`; for the final comparison, use `--num-trials-per-task 50`.

On the AutoDL server, start the policy server with one checkpoint at a time:

```bash
cd $PROJECT_ROOT

# Control group
python server/serve_policy.py \
    --server \
    --model_path $OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_1/checkpoint-1 \
    --data_config franka \
    --embodiment_tag new_embodiment \
    --port 5555

# Fine-tuned group
python server/serve_policy.py \
    --server \
    --model_path $OUTPUT_ROOT/franka_libero_object_no_noops_lerobot_20000/checkpoint-20000 \
    --data_config franka \
    --embodiment_tag new_embodiment \
    --port 5555
```

On the RTX 4070 simulation machine, create the SSH tunnel and run the same LIBERO evaluation:

```bash
# Terminal 1: keep this process running
ssh -N -p <autodl-ssh-port> -L 5555:127.0.0.1:5555 root@<autodl-host>

# Terminal 2: run evaluation
cd /home/star/Desktop/RoboticGrasping-Manipulation/Project7/sim/libero
python main.py \
    --host 127.0.0.1 \
    --port 5555 \
    --task-suite-name libero_object \
    --num-trials-per-task 50 \
    --video-out-path /home/star/Desktop/RoboticGrasping-Manipulation/Project7/output/sim/checkpoint_1
```

When switching from `checkpoint-1` to `checkpoint-20000`, stop the server, restart it with the other `--model_path`, and run the same simulation command again with a different `--video-out-path`, for example `output/sim/checkpoint_20000`.

Record the final results in this format:

| Model | Checkpoint | Tasks | Trials per task | Total rollouts | Success rate | Notes |
|-------|------------|-------|-----------------|----------------|--------------|-------|
| GR00T-N1 LIBERO baseline | `checkpoint-1` | `libero_object` | 50 | 500 | TBD | Control group |
| GR00T-N1 LIBERO fine-tuned | `checkpoint-20000` | `libero_object` | 50 | 500 | TBD | Main experiment |

---

## Setup — Simulation Client (RTX 4070)

The simulation runs LIBERO with MuJoCo and connects to the inference server via WebSocket.

### 1. Clone this repo

```bash
git clone <this-repo-url>
cd Project7
```

### 2. Clone LIBERO submodule

```bash
# From sim/libero/README.md: requires submodule init
cd sim/libero
git submodule update --init --recursive   # pulls sim/third_party/libero
cd ../..
```

### 3. Create conda environment

```bash
conda create -n gr00t_sim python=3.8 -y
conda activate gr00t_sim
```

### 4. Install dependencies

```bash
# LIBERO + robosuite + MuJoCo
pip install -r sim/libero/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cu113 \
    --index-strategy=unsafe-best-match

# LIBERO third-party
pip install -r sim/third_party/libero/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cu113 \
    --index-strategy=unsafe-best-match

pip install -e sim/third_party/libero

# openpi-client (sim side)
pip install -e sim/openpi-client
```

### 5. Verify environment

```bash
conda activate gr00t_sim
python check_4070_sim_env.py
```

### 6. Run evaluation

```bash
conda activate gr00t_sim

# Create SSH tunnel to the server first:
#   ssh -N -p <autodl-port> -L 5555:127.0.0.1:5555 root@<autodl-host>

# Then run eval:
cd sim/libero
python main.py --host 127.0.0.1 --port 5555 --task-suite-name libero_object --num-trials-per-task 50
```

---

## Server Deployment (Docker)

Build and run the inference server as a Docker container on the A100:

```bash
docker build -f server/Dockerfile -t gr00t-server .
docker run --gpus all -p 5555:5555 -v $(pwd)/GR00T-N1-2B:/workspace/GR00T-N1-2B gr00t-server \
    python server/serve_policy.py --model_path /workspace/GR00T-N1-2B --data_config franka --port 5555 --server
```

---

## Architecture

```
┌──────────────────────┐         WebSocket          ┌──────────────────────┐
│   RTX 4070 (Sim)     │ ◄─────────────────────────► │  A100 (Server)       │
│                      │    images + state → action  │                      │
│  sim/libero/main.py  │                             │  server/serve_       │
│  LIBERO + MuJoCo     │                             │  policy.py           │
│  openpi-client       │                             │  GR00T-N1-2B         │
└──────────────────────┘                             └──────────────────────┘
```
