# 软件验收清单

## 实测记录（2026-09-29）

| 后端 | 环境 | 验收结果 | 证据 |
| --- | --- | --- | --- |
| Python教学后端 | macOS本机、10.59 | 两端各11项测试通过 | `./lab test` |
| 六章实验矩阵 | macOS本机 | 报告、JSON和CSV生成成功 | `artifacts/latest/` |
| ROS 2 Jazzy | 10.59容器 | 正常链完成6个技能 | `artifacts/ros2/result.json` |
| ROS 2取消链 | 10.59容器 | 抓取阶段取消，确认安全保持 | `canceled_safe_hold`、`physical_stop_verified: true` |
| Isaac Sim 5.0 | 10.59、RTX 5090 | G1场景初始化并完成2个有限物理步 | `artifacts/isaac/g1-validation.json` |

Isaac报告实际记录的任务为 `Isaac-PickPlace-Cylinder-G129-Dex1-Joint`，机器人为 `unitree_g1_29dof_dex1`，教学对象为 `cup_blue`，随机种子为42。验证结束后容器数量为0。当前有限步入口使用CPU保存控制状态，RTX负责Vulkan离屏场景初始化；该结果用于证明资产、任务、观测和仿真循环可运行，不用于宣称抓取成功率。

## 基础后端

- `./lab test` 全部通过。
- `./lab demo` 生成HTML、JSON和CSV。
- `./lab matrix` 覆盖六章的代表性边界条件。
- 歧义输入不会被自动选为唯一目标。
- 禁止移动的展示品会使物理执行门槛关闭。
- 反馈丢失会保留“物理结果未知”，不报告任务成功。

## ROS 2

- 接口包能由 `rosidl` 编译。
- 场景、任务、计划和运行时状态使用带版本的 `BookState`。
- 技能目录可通过 `QuerySkills` 查询。
- `ExecuteSkill` 包含目标、反馈、结果和取消语义。
- 正常闭环完成六个技能，并生成 `artifacts/ros2/result.json`。
- 过期场景版本与未注册技能会被拒绝。

## Isaac Sim / Unitree G1

- NVIDIA原始镜像可启动 `SimulationApp`。
- 教材镜像加载G1 29DoF、Dex1、桌面、蓝杯代理和相机。
- `g1-verify` 在固定步数后正常清理并退出。
- 实际仿真状态写入 `artifacts/isaac/g1-validation.json`。
- GUI入口检查Xorg与Xauthority，不在无桌面条件下假装启动。

## 安全与可复现性

- 默认脚本不连接实体机器人。
- 供应商密钥不写入仓库、实验报告或容器镜像。
- 本地、ROS 2与Isaac输出均声明后端和适用边界。
- 镜像、依赖与宇树仓库使用 `docs/version-matrix.md` 中的锁定版本。
