

# Project6  grootn1在libero数据上微调对比

2025年3月18日，英伟达推出开源通用机器人模型GR00T N1，是全球首个面向通用机器人的开放基础模型。它不仅拥有理解视觉与语言指令的“智慧之眼”，还能通过实时生成流畅动作的“敏捷之手”，在复杂多变的环境中完成多样化任务。

该项目实现了如何使用[IPEC-COMMUNITY/libero_object_no_noops_lerobot](https://hf-mirror.com/datasets/IPEC-COMMUNITY/libero_object_no_noops_lerobot)数据集对VLA模型[GR00T N1](https://github.com/NVIDIA/Isaac-GR00T)微调，并使用[libero仿真](https://github.com/Lifelong-Robot-Learning/LIBERO)进行验证，可视化结果如下。

微调前：测试未微调的grootn1模型在libero上测试 **total 500, success rate: 0**

![](C:\Users\simon\Desktop\机器人抓取与操作\抓取与操作Project6\微调前.gif)



微调后：测试微调的grootn1模型在libero上测试 **total 500, success rate: 96.2**

![](C:\Users\simon\Desktop\机器人抓取与操作\抓取与操作Project6\微调后.gif)



#### 本项目所用到的文档下载链接如下：

链接: https://pan.baidu.com/s/1_Q_utsZCn19dk1OXVCwC7w
提取码: 9m7s

### 系统配置建议

本次实践配置要求较高，最低建议A100显卡，显存≥40g，可以尝试使用云服务器。

### docker 环境安装
服务端采用docker,客户端在主机上运行,参考客户端环境安装
GR00T N1环境安装
修改dockerfile:

```dockerfile
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/workspace:${PYTHONPATH}

# 修改软件源为阿里云镜像源
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list

# System dependencies
RUN apt update && \
    apt install -y tzdata && \
    ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    apt install -y netcat dnsutils && \
    apt-get update && \
    apt-get install -y libgl1-mesa-glx git libvulkan-dev \
    zip unzip wget curl git git-lfs build-essential cmake \
    vim less sudo htop ca-certificates man tmux ffmpeg \
    # Add OpenCV system dependencies
    libglib2.0-0 libsm6 libxext6 libxrender-dev
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --upgrade pip setuptools
RUN pip install gpustat wandb==0.19.0
# Create and set working directory
WORKDIR /workspace
# Copy pyproject.toml for dependencies
COPY pyproject.toml .
# Install dependencies from pyproject.toml
RUN pip install -e .
# There's a conflict in the native python, so we have to resolve it by
RUN pip uninstall -y transformer-engine
RUN pip install flash_attn==2.7.1.post4 -U --force-reinstall
# Clean any existing OpenCV installations
RUN pip uninstall -y opencv-python opencv-python-headless || true
RUN rm -rf /usr/local/lib/python3.10/dist-packages/cv2 || true
RUN pip install opencv-python==4.8.0.74
RUN pip install --force-reinstall torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 numpy==1.26.4
COPY getting_started /workspace/getting_started
COPY scripts /workspace/scripts
COPY demo_data /workspace/demo_data
RUN pip install -e . --no-deps
# need to install accelerate explicitly to avoid version conflicts
RUN pip install accelerate>=0.26.0
```
配置国内镜像
```bash
{
  "data-root": "/mnt/data/docker",
   "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://dockerproxy.com"
  ]
}
```

构建
` docker build . -t isaac_gr00t`
可以多构建几次

运行示例

```bash
docker run -d --shm-size=5G --gpus=all -it --name isaac_gr00t \
  --privileged \
  --net=host \
  -v $HOME/grasp_Project6:$HOME \
  -v /etc/apt/sources.list:/etc/apt/sources.list \
  -w $HOME \
  -h $USER \
  -v /dev:/dev \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY \
  -e GDK_SCALE \
  -e GDK_DPI_SCALE \
  isaac_gr00t:latest sleep infinity
```
然后可以通过vscode远程管理容器，在容器中安装服务端环境。

这里注意运行服务端的时候检查 /etc/hostname里的hostname  和 /etc/hosts里的 IP hostname 值是否一致不然会出现
`python socket.gethostbyname() 报错socket.gaierror: [Errno -2] Name or service not known
`

## 环境安装

- 建议使用anaconda来管理环境
- GR00T N1部署，采用的是客户端-服务端模式， 服务端负责模型推理，客户端负责收集仿真/真机的状态、视觉等信息，然后送入服务端以获得action结果， 因此需要装客户端环境和服务端环境。



### GR00T N1环境安装

* 注意CUDA Version: 12.4 !!!

```python
cd $HOME
git clone https://github.com/NVIDIA/Isaac-GR00T
conda create -n gr00t python=3.10
conda activate gr00t

pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade setuptools
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple jupyter
pip install ninja
pip install --no-build-isolation flash-attn==2.7.1.post4 
```

### 服务端环境安装

服务端环境和GR00T N1环境放在一个虚拟环境中, 服务端环境需要安装一个openpi-client的库，openpi-client是[openpi](https://github.com/Physical-Intelligence/openpi.git)的一个子包，然后需要对服务端代码做下简单修改，将修改后的代码打包放到了下面， 修改了哪些内容后续会补充到说明部分。

- 下载server.zip文件

把server.zip放到$HOME目录下：

```python
cd $HOME
unzip server.zip

conda activate gr00t
cd $HOME/server/openpi-client
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .
```

### 客户端环境安装

客户端环境需要安装libero库、openpi-client库，然后需要对代码做下简单修改， 将修改后的代码打包放到了下面，修改了那些内容后续会补充到说明部分。

- 下载sim.zip文件

把sim.zip放到$HOME目录下：

```python
conda create -n gr00t_sim python=3.8
conda activate gr00t_sim

cd $HOME
unzip sim.zip

cd sim/openpi-client
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .

cd $HOME/sim/third_party/libero
apt update
apt install cmake
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple robosuite==1.4.1 tyro
```

## 微调

### 准备数据

GR00T N1采用的数据格式在lerobot数据格式上做了修改，详细请看[lerobot数据说明](https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/LeRobot_compatible_data_schema.md)。

为了快速验证， 这里没有用libero仿真从头生成数据， 而是使用他人已经生成好的libero数据，且已经转成lerobot格式， 地址https://hf-mirror.com/datasets/IPEC-COMMUNITY/libero_object_no_noops_lerobot。

#### **下载数据**

```python
cd $HOME
apt install git-lfs
git lfs install
git clone https://hf-mirror.com/datasets/IPEC-COMMUNITY/libero_object_no_noops_lerobot
```

#### **添加madality.json**

- 下载modality.json文件

GR00T N1用的数据格式和lerobot数据格式就相差一个modality.json文件， 所以需要把上面的modality.json文件拷贝到`$HOME/libero_object_no_noops_lerobot/meta`目录下。

#### 修改代码

libero_object_no_noops_lerobot数据集是新的数据类型，GR00T N1库需要加些配置代码，才可以让GR00T N1兼容新的数据类型。

#### **添加FrankaDataConfig**

把下面代码添加到`$HOME/Isaac-GR00T/gr00t/experiment/data_config.py`文件中

```python
class FrankaDataConfig(BaseDataConfig):
    video_keys = ["video.image", "video.wrist_image"]
    state_keys = ["state.x", "state.y", "state.z", "state.roll", "state.pitch", "state.yaw", "state.gripper"]
    action_keys = ["action.x", "action.y", "action.z", "action.roll", "action.pitch", "action.yaw", "action.gripper"]
    language_keys = ["annotation.human.task_description"]
    observation_indices = [0]
    action_indices = list(range(16))

    def modality_config(self) -> dict[str, ModalityConfig]:
        video_modality = ModalityConfig(
            delta_indices=self.observation_indices,
            modality_keys=self.video_keys,
        )

        state_modality = ModalityConfig(
            delta_indices=self.observation_indices,
            modality_keys=self.state_keys,
        )

        action_modality = ModalityConfig(
            delta_indices=self.action_indices,
            modality_keys=self.action_keys,
        )

        language_modality = ModalityConfig(
            delta_indices=self.observation_indices,
            modality_keys=self.language_keys,
        )

        modality_configs = {
            "video": video_modality,
            "state": state_modality,
            "action": action_modality,
            "language": language_modality,
        }

        return modality_configs

    def transform(self) -> ModalityTransform:
        transforms = [
            # video transforms
            VideoToTensor(apply_to=self.video_keys),
            VideoCrop(apply_to=self.video_keys, scale=0.95),
            VideoResize(apply_to=self.video_keys, height=224, width=224, interpolation="linear"),
            VideoColorJitter(
                apply_to=self.video_keys,
                brightness=0.3,
                contrast=0.4,
                saturation=0.5,
                hue=0.08,
            ),
            VideoToNumpy(apply_to=self.video_keys),
            # state transforms
            StateActionToTensor(apply_to=self.state_keys),
            StateActionTransform(
                apply_to=self.state_keys,
                normalization_modes={key: "min_max" for key in self.state_keys},
            ),
            # action transforms
            StateActionToTensor(apply_to=self.action_keys),
            StateActionTransform(
                apply_to=self.action_keys,
                normalization_modes={key: "min_max" for key in self.action_keys},
            ),
            # concat transforms
            ConcatTransform(
                video_concat_order=self.video_keys,
                state_concat_order=self.state_keys,
                action_concat_order=self.action_keys,
            ),
            # model-specific transform
            GR00TTransform(
                state_horizon=len(self.observation_indices),
                action_horizon=len(self.action_indices),
                max_state_dim=64,
                max_action_dim=32,
            ),
        ]
        return ComposedModalityTransform(transforms=transforms)
```

#### **替换DATA_CONFIG_MAP**

把下面代码替换掉`$HOME/Isaac-GR00T/gr00t/experiment/data_config.py`文件中的DATA_CONFIG_MAP

```json
DATA_CONFIG_MAP = {
    "gr1_arms_waist": Gr1ArmsWaistDataConfig(),
    "gr1_arms_only": Gr1ArmsOnlyDataConfig(),
    "gr1_full_upper_body": Gr1FullUpperBodyDataConfig(),
    "bimanual_panda_gripper": BimanualPandaGripperDataConfig(),
    "bimanual_panda_hand": BimanualPandaHandDataConfig(),
    "single_panda_gripper": SinglePandaGripperDataConfig(),
    "franka": FrankaDataConfig()
}
```

#### **添加LiberoSingleDataset**

把下面代码放到`$HOME/Isaac-GR00T/gr00t/data/dataset.py`中

```python
class LiberoSingleDataset(LeRobotSingleDataset):
    def _get_metadata(self, embodiment_tag: EmbodimentTag) -> DatasetMetadata:
        """Get the metadata for the dataset.

        Returns:
            dict: The metadata for the dataset.
        """

        # 1. Modality metadata
        modality_meta_path = self.dataset_path / LE_ROBOT_MODALITY_FILENAME
        assert (
            modality_meta_path.exists()
        ), f"Please provide a {LE_ROBOT_MODALITY_FILENAME} file in {self.dataset_path}"

        # 1.1. State and action modalities
        simplified_modality_meta: dict[str, dict] = {}
        with open(modality_meta_path, "r") as f:
            le_modality_meta = LeRobotModalityMetadata.model_validate(json.load(f))
        for modality in ["state", "action"]:
            simplified_modality_meta[modality] = {}
            le_state_action_meta: dict[str, LeRobotStateActionMetadata] = getattr(
                le_modality_meta, modality
            )
            for subkey in le_state_action_meta:
                state_action_dtype = np.dtype(le_state_action_meta[subkey].dtype)
                if np.issubdtype(state_action_dtype, np.floating):
                    continuous = True
                else:
                    continuous = False
                simplified_modality_meta[modality][subkey] = {
                    "absolute": le_state_action_meta[subkey].absolute,
                    "rotation_type": le_state_action_meta[subkey].rotation_type,
                    "shape": [
                        le_state_action_meta[subkey].end - le_state_action_meta[subkey].start
                    ],
                    "continuous": continuous,
                }

        # 1.2. Video modalities
        le_info_path = self.dataset_path / LE_ROBOT_INFO_FILENAME
        assert (
            le_info_path.exists()
        ), f"Please provide a {LE_ROBOT_INFO_FILENAME} file in {self.dataset_path}"
        with open(le_info_path, "r") as f:
            le_info = json.load(f)
        simplified_modality_meta["video"] = {}
        for new_key in le_modality_meta.video:
            original_key = le_modality_meta.video[new_key].original_key
            if original_key is None:
                original_key = new_key
            le_video_meta = le_info["features"][original_key]
            height = le_video_meta["shape"][le_video_meta["names"].index("height")]
            width = le_video_meta["shape"][le_video_meta["names"].index("width")]
            # NOTE(FH): different lerobot dataset versions have different keys for the number of channels and fps
            try:
                channels = le_video_meta["shape"][le_video_meta["names"].index("rgb")]
                fps = le_video_meta["info"]["video.fps"]
            except ValueError:
                channels = le_video_meta["shape"][le_video_meta["names"].index("channels")]
                fps = le_video_meta["info"]["video.fps"]
            simplified_modality_meta["video"][new_key] = {
                "resolution": [width, height],
                "channels": channels,
                "fps": fps,
            }

        # 2. Dataset statistics
        stats_path = self.dataset_path / LE_ROBOT_STATS_FILENAME
        try:
            with open(stats_path, "r") as f:
                le_statistics = json.load(f)
            for stat in le_statistics.values():
                DatasetStatisticalValues.model_validate(stat)
        except (FileNotFoundError, ValidationError) as e:
            print(f"Failed to load dataset statistics: {e}")
            print(f"Calculating dataset statistics for {self.dataset_name}")
            # Get all parquet files in the dataset paths
            parquet_files = list((self.dataset_path).glob(LE_ROBOT_DATA_FILENAME))
            le_statistics = calculate_dataset_statistics(parquet_files)
            with open(stats_path, "w") as f:
                json.dump(le_statistics, f, indent=4)
        dataset_statistics = {}
        for our_modality in ["state", "action"]:
            dataset_statistics[our_modality] = {}
            for subkey in simplified_modality_meta[our_modality]:
                dataset_statistics[our_modality][subkey] = {}
                state_action_meta = le_modality_meta.get_key_meta(f"{our_modality}.{subkey}")
                assert isinstance(state_action_meta, LeRobotStateActionMetadata)
                le_modality = state_action_meta.original_key
                for stat_name in le_statistics[le_modality]:
                    indices = np.arange(
                        state_action_meta.start,
                        state_action_meta.end,
                    )
                    stat = np.array(le_statistics[le_modality][stat_name])
                    dataset_statistics[our_modality][subkey][stat_name] = stat[indices].tolist()

        # 3. Full dataset metadata
        metadata = DatasetMetadata(
            statistics=dataset_statistics,  # type: ignore
            modalities=simplified_modality_meta,  # type: ignore
            embodiment_tag=embodiment_tag,
        )

        return metadata
```

#### **添加微调代码**

在`$HOME/Isaac-GR00T/gr00t/scripts/`下有个gr00t_finetune.py文件， 这个是微调模型的启动代码， 为了兼容libero_object_no_noops_lerobot数据格式，需要把gr00t_finetune.py做简单修改， 修改后的文件如下

- 下载gr00t_finetune_libero.py文件

需要把gr00t_finetune_libero.py拷贝到`$HOME/Isaac-GR00T/gr00t/scripts/`下

#### 下载权重

下载GR00T N1的预训练权重

```python
cd $HOME
git clone https://hf-mirror.com/nvidia/GR00T-N1-2B
```

#### 训练

```bash
conda activate gr00t
cd $HOME/Isaac-GR00T

python scripts/gr00t_finetune_libero.py \
--dataset-path $HOME/libero_object_no_noops_lerobot \
--num-gpus 4 \
--output-dir output/franka_libero_object_no_noops_lerobot_20000 \
--max-steps 20000 \
--data-config franka \
--video-backend torchvision_av \
--base-model-path $HOME/GR00T-N1-2B
```

执行完上面的命令， 会在output/franka_libero_object_no_noops_lerobot_20000文件夹中保存好权重。

## 仿真

### 测试未微调的模型在libero上测试

GR00T N1预训练的模型`https://hf-mirror.com/nvidia/GR00T-N1-2B`使用的机器人本体是[gr1](https://www.fftai.com/products-gr1), libero中用的机器臂是franka的某型号机械臂，所以无法在未经微调的GR00T N1模型进行libero仿真测试。

因此把GR00T-N1-2B微调1个iter，把gr00t_finetune_libero.py中Config改成下面配置

```python
@dataclass
class Config:
    """Configuration for GR00T model fine-tuning."""

    # Dataset parameters
    dataset_path: str
    """Path to the dataset directory."""

    output_dir: str = "/tmp/gr00t"
    """Directory to save model checkpoints."""

    data_config: str = "gr1_arms_only"
    """Data configuration name from DATA_CONFIG_MAP."""

    # Training parameters
    batch_size: int = 16
    """Batch size per GPU for training."""

    max_steps: int = 10000
    """Maximum number of training steps."""

    num_gpus: int = 1
    """Number of GPUs to use for training."""

    save_steps: int = 1
    """Number of steps between saving checkpoints."""

    # Model parameters
    base_model_path: str = "nvidia/GR00T-N1-2B"
    """Path or HuggingFace model ID for the base model."""

    tune_llm: bool = False
    """Whether to fine-tune the language model backbone."""

    tune_visual: bool = False
    """Whether to fine-tune the vision tower."""

    tune_projector: bool = False
    """Whether to fine-tune the projector."""

    tune_diffusion_model: bool = False
    """Whether to fine-tune the diffusion model."""

    resume: bool = False
    """Whether to resume from a checkpoint."""

    # Advanced training parameters
    learning_rate: float = 1e-4
    """Learning rate for training."""

    weight_decay: float = 1e-5
    """Weight decay for AdamW optimizer."""

    warmup_ratio: float = 0.05
    """Ratio of total training steps used for warmup."""

    lora_rank: int = 0
    """Rank for the LORA model."""

    lora_alpha: int = 16
    """Alpha value for the LORA model."""

    lora_dropout: float = 0.1
    """Dropout rate for the LORA model."""

    dataloader_num_workers: int = 8
    """Number of workers for data loading."""

    report_to: str = "wandb"
    """Where to report training metrics (e.g., 'wandb', 'tensorboard')."""

    # Data loading parameters
    embodiment_tag: str = "new_embodiment"
    """Embodiment tag to use for training. e.g. 'new_embodiment', 'gr1'"""

    video_backend: str = "decord"
    """Video backend to use for training. [decord, torchvision_av]"""
```

然后测试, 跑完下面代码后，把Config恢复原来的配置

```Shell
python scripts/gr00t_finetune_libero.py \
--dataset-path $HOME/libero_object_no_noops_lerobot \
--num-gpus 1 \
--output-dir output/franka_libero_object_no_noops_lerobot_1 \
--max-steps 1 \
--data-config franka \
--video-backend torchvision_av \
--base-model-path $HOME/GR00T-N1-2B
```

启动服务端

```python
conda activate gr00t
cd $HOME
python server/serve_policy.py \
    --server \
    --model_path $HOME/Isaac-GR00T/output/franka_libero_object_no_noops_lerobot_1/checkpoint-1 \
    --embodiment_tag new_embodiment \
    --data_config franka \
    --denoising_steps 4
```

启动客户端

```python
conda activate gr00t_sim
cd $HOME/sim/libero
python main.py
```

### 测试微调后的模型在libero上测试

启动服务端

```python
conda activate gr00t
cd $HOME
python server/serve_policy.py \
    --server \
    --model_path $HOME/Isaac-GR00T/output/franka_libero_object_no_noops_lerobot_20000/checkpoint-20000 \
    --embodiment_tag new_embodiment \
    --data_config franka \
    --denoising_steps 4
```

启动客户端

```python
conda activate gr00t_sim
cd $HOME/sim/libero
python main.py
```

上面的代码会在10个任务上测试500次，每个任务50次

![](C:\Users\simon\Desktop\机器人抓取与操作\抓取与操作Project6\0915b75e-bde9-4571-9a0a-ec1bdf43b342.png)

成功率如下：

**total 500, success rate: 96.2**





### 本项目学习可参考：

https://github.com/FelixFu520/Isaac-GR00T-injector