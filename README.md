# 具身智能原理与方法：配套实验

本仓库把教材中的“递送蓝色杯子”主线实现为六个逐章实验和一个完整智能体。默认后端只需要 Python 3.9+；ROS 2 与 Isaac Sim 作为增强后端接入同一组数据结构和验收测试。

项目主页：<https://github.com/LightingMax/2026_embedding-intelligence-labs>

## 一键体验

```bash
./lab demo
```

命令会依次运行感知、任务理解、任务规划、运动可行性、示范学习和智能体编排，并在 `artifacts/latest/index.html` 生成可视化报告。

```bash
./lab test                 # 运行测试
./lab chapter 1            # 只运行某一章
./lab demo --fault target_moved
./lab serve                # 在 http://127.0.0.1:8000 查看报告
```

## 六章与实验

| 章节 | 实验 | 输入 | 输出 |
| --- | --- | --- | --- |
| 第1章 感知 | 从多源观测形成状态 | 本体、定位、视觉与系统观测 | `SceneState` |
| 第2章 认知 | 从场景与指令形成任务 | `SceneState`、用户指令与规则 | `TaskSpec` |
| 第3章 规划 | 生成并验证离散技能计划 | `TaskSpec`、技能目录 | `PlanSpec` |
| 第4章 运动 | 检查可达性并生成参考路径 | 技能目标、本体与障碍 | `MotionCheck` |
| 第5章 学习 | 从示范学习阶段动作 | 轨迹样本 | `LearnedPolicy` |
| 第6章 智能体 | 编排、取消、恢复与取证 | 前五章接口与事件 | `RuntimeState`、事件日志 |

每一章都可以单独运行；第六章只通过稳定接口调用前五章能力。教材中的理论定义不依赖某个仿真器。

## 后端

### Mock 后端

默认后端使用仓库内的小型场景和示范数据，适合课堂、CI和没有GPU的电脑。它完整执行数据流，但不声称替代物理仿真。

### ROS 2 后端

`ros_ws/` 提供ROS 2 Jazzy示例节点，把相同结构发布到 `/book/scene_state`、`/book/task_spec`、`/book/plan_spec` 和 `/book/runtime_events`。运行：

```bash
docker compose --profile ros2 up --build
```

### Unitree G1 + Isaac Sim 后端

服务器方案基于宇树官方 `unitree_sim_isaaclab`，固定到仓库记录的提交，并使用其G1 29自由度夹爪场景。RTX 50系列使用Isaac Sim 5.0.0。安装体积较大，首次运行会下载NVIDIA与宇树资产：

```bash
./lab isaac doctor
./lab isaac setup
./lab isaac run
```

该后端通过适配器把相机、本体状态与DDS反馈转换为教材接口。仿真策略权重只用于仿真验证；实机控制不在默认脚本中启用。

## 可选模型和语音服务

核心实验不需要密钥。Qwen只参与候选计划复核，不直接调用机器人技能；可选服务只从进程环境读取凭据，仓库不会保存密钥：

```bash
export DASHSCOPE_API_KEY=...
./lab demo --llm qwen
```

讯飞语音和其他语音服务通过 `SpeechProvider` 接口接入。课堂发布时由教师端代理保管凭据，学生浏览器不直接持有供应商密钥。语音服务属于输入输出通道，任务语义仍由第2章接口校验。

## 目录

- `data/`：可提交的小型场景、事件与示范数据。
- `src/embodied_book_labs/`：六章可运行逻辑与统一数据接口。
- `ros_ws/`：ROS 2教学桥接包。
- `scripts/`：本地、服务器和Isaac环境入口。
- `docs/`：系统边界、版本矩阵与实验验收标准。
- `tests/`：接口、故障恢复和端到端测试。

## 安全边界

默认配置只运行仿真或确定性Mock数据，不连接实体机器人。任何实机适配都必须显式选择网络接口、关闭仿真DDS域并经过平台侧安全流程。
