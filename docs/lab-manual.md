# 配套实验手册

## 实验工件与责任边界

| 工件 | 产生章节 | 后续用途 | 不代表 |
| --- | --- | --- | --- |
| `SceneState` | 第1章 | 语义绑定、计划与物理检查 | 用户的任务目标 |
| `TaskSpec` | 第2章 | 规定目标、约束、证据和未知项 | 技能顺序或轨迹 |
| `PlanSpec` | 第3章 | 组织技能、分支和重规划条件 | 连续空间运动 |
| `MotionCheck` | 第4章 | 说明条件化物理可行性 | 实机必然成功 |
| 学得策略与评价 | 第5章 | 为能力接口提供参数和证据 | 系统执行权 |
| `RuntimeState` | 第6章 | 记录执行、取消、恢复和完成证据 | 对原始任务的静默改写 |

## 基础实验

Python后端每次从原始场景副本开始，因此同一命令可以重复。

```bash
./lab demo
./lab demo --scenario depth_invalid
./lab demo --fault human_entered
./lab matrix
```

检查 `result.json` 时应先看状态和失效理由，再看具体数值。例如，深度无效时对象仍可保留语义候选，但 `for_manipulation` 必须为假；反馈丢失时运行时结果必须为 `blocked`，不得根据已发送命令推断物理成功。

## ROS 2实验

`./lab ros2` 在容器内编译两个包：

1. `embodied_book_interfaces` 生成消息、服务和Action类型；
2. `embodied_book_bridge` 启动场景发布者、技能服务器和任务执行器。

正常运行的每个技能都会经过 `accepted`、`executing`、`verifying` 三类反馈，随后返回结果。输入的 `scene_version` 与技能服务器当前版本不一致时，Action目标会被拒绝。

取消试验：

```bash
./lab ros2 user_cancel
```

执行器在抓取反馈达到50%时发送取消。技能服务器确认取消后返回 `canceled_safe_hold`和 `physical_stop_verified`。

## Isaac G1实验

`g1-verify` 运行宇树官方Isaac Lab任务的有限步版。容器补丁只做两类改动：

1. 把圆柱教具调整为蓝色杯子代理的尺寸、质量和颜色；
2. 增加 `max_steps` 和 `book_report`，使进程可自动退出并导出仿真状态。

运行：

```bash
./lab isaac run g1-verify
python3 -m json.tool artifacts/isaac/g1-validation.json >/dev/null
```

验收时检查 `backend`、`task`、`robot`、`object_id`、`seed`、`steps` 和 `scene_state`。报告中的数据来自实际启动的Isaac任务，不是Python基础后端的复制。

GUI试验要求服务器存在Xorg `:0` 与可读的Xauthority：

```bash
./lab isaac run g1-gui
```

仿真验证到资产、场景、观测、物理时钟和软件接口。需要力、摩擦、全身平衡或真实杯子抓取结论时，必须另行指定控制器、物理参数和重复试验。

## 学生提交物

每组提交：

- 一份 `result.json` 和 `timeline.csv`；
- 正常场景、一个可恢复故障和一个不能自动恢复故障；
- 对每个故障说明检测证据、恢复级别和最终状态；
- 声明使用的后端、版本、随机种子与结论边界。
