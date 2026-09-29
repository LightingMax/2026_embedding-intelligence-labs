# 具身智能原理与方法：配套实验

本仓库把教材中的“递送蓝色杯子”主线实现为六个逐章实验和一个可恢复智能体。普通电脑可直接运行确定性教学后端；ROS 2 Jazzy与Isaac Sim 5.0用于验证通信契约、仿真场景、宇树G1资产和运行时证据。

项目主页：<https://github.com/LightingMax/2026_embedding-intelligence-labs>

## 五分钟体验

```bash
./lab demo
./lab matrix
./lab serve
```

- `demo`：运行一次正常六章数据链。
- `matrix`：运行感知退化、语义歧义、规则冲突、计划失效、运动拒绝和六类运行时故障。
- `serve`：在 <http://127.0.0.1:8000> 查看报告。

结果写入 `artifacts/latest/`：

- `index.html`：逐章结果、运行时间线和证据摘要；
- `result.json`：完整结构化输出；
- `timeline.csv`：便于课程报告分析的事件表。

## 六章实验

| 章节 | 输入 | 主要输出 | 可验证失效 |
| --- | --- | --- | --- |
| 第1章 感知 | 关节、IMU、接触、SLAM、视觉 | `SceneState` | 相机黑屏、重定位、深度无效、目标移动 |
| 第2章 认知 | `SceneState`、用户指令、规则 | `TaskSpec` | 颜色歧义、类别歧义、展示品规则冲突 |
| 第3章 规划 | `TaskSpec`、技能目录 | `PlanSpec` | 技能缺失、场景版本过期、被阻断的执行门槛 |
| 第4章 运动 | 本体、目标、通道和障碍 | `MotionCheck` | 状态无效、间隙不足、不可达、需绕行 |
| 第5章 学习 | 示范轨迹和随机化动力学 | 行为克隆策略、到达策略评价 | 数据覆盖不足、范围外动力学 |
| 第6章 智能体 | 前五章接口和异步事件 | `RuntimeState`、时间线 | 目标移动、路径受阻、抓取失败、人员侵入、反馈丢失、取消 |

```bash
./lab chapter 1
./lab chapter 2 --scenario ambiguous_target
./lab chapter 4 --scenario clearance_blocked
./lab demo --fault grasp_failed
./lab demo --fault feedback_lost
```

## ROS 2 Jazzy闭环

ROS 2工作空间包含：

- `BookState.msg`：带时间、关联ID、结构版本和数据版本的状态载体；
- `QuerySkills.srv`：查询当前技能目录；
- `ExecuteSkill.action`：输入技能、参数和场景版本，返回进度、结果和取消后安全状态。

```bash
./lab ros2
./lab ros2 user_cancel
./lab ros2 path_blocked
```

正常运行会依次执行六个技能并在 `artifacts/ros2/result.json` 保存Action反馈。取消实验要求服务器返回 `canceled_safe_hold`，而不是把未知物理结果写成成功。

## Unitree G1 + Isaac Sim

GPU增强后端固定Isaac Sim 5.0.0、Isaac Lab 2.2.0与宇树官方 `unitree_sim_isaaclab` 提交。场景使用G1 29自由度与Dex1夹爪，蓝色圆柱作为课堂用杯子几何代理。

```bash
./lab isaac doctor
./lab isaac setup
./lab isaac run smoke
./lab isaac run g1-verify
./lab isaac run g1-gui
```

`g1-verify` 会加载G1、桌面、教学杯子、相机和仿真时钟，运行固定步数后自动退出，并写入 `artifacts/isaac/g1-validation.json`。`g1-gui` 在服务器Xorg桌面显示，可通过Sunshine/Moonlight查看。

G1默认入口只启用仿真DDS域，不连接实体机器人。有限步验证证明资产、任务、观测和控制循环能启动；它不等于真实杯子的抓取成功率证据。

## 可选Qwen与讯飞语音

核心实验不需要密钥。Qwen只审查候选计划，不获得技能执行权；讯飞接口用于语音输入输出。

```bash
export DASHSCOPE_API_KEY=...
./lab demo --llm qwen

python3 -m pip install -e '.[speech]'
export XUNFEI_APP_ID=...
export XUNFEI_API_KEY=...
export XUNFEI_API_SECRET=...
./lab speech tts --text "请接好蓝色杯子"
./lab speech asr --input sample-16k-mono.pcm
```

密钥只从进程环境读取，不应写入课程数据、日志或仓库。

## 验证

```bash
./lab test
docker compose run --rm labs
```

版本锁定、系统边界和逐项验收见 `docs/`。
