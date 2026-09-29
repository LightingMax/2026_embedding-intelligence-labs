# 锁定版本

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.9+ | Mock实验无第三方运行依赖 |
| ROS 2 | Jazzy | 与Ubuntu 24.04课堂容器配套 |
| Isaac Sim | 5.0.0 | 宇树官方要求RTX 50系列使用该版本 |
| Isaac Lab | v2.2.0 (`46dff135`) | 对应Isaac Sim 5.0.0 |
| CycloneDDS | releases/0.10.x (`5041f356`) | Unitree DDS通信依赖 |
| unitree_sdk2_python | `814556d1` | Unitree Python SDK |
| unitree_sim_isaaclab | `e30c25b1dffdf92ada1d6c8c1fe9a47bdde0fecc` | 官方G1场景与DDS接口 |
| teleimager | `b81de448` | Unitree仿真仓库锁定的子模块版本 |
| G1场景 | 29DoF + Dex1夹爪 | 首个递杯MVP，后续可扩展Dex3 |

NVIDIA和宇树资产在首次构建时下载，受各自许可证约束，不复制进本仓库。
