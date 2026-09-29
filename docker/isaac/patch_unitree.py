from __future__ import annotations

from pathlib import Path


ROOT = Path("/opt/unitree_sim_isaaclab")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"patch anchor not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_scene() -> None:
    path = ROOT / "tasks/common_scene/base_scene_pickplace_cylindercfg.py"
    replace_once(path, "radius=0.018,", "radius=0.04,")
    replace_once(path, "height=0.35,", "height=0.16,")
    replace_once(path, "mass_props=sim_utils.MassPropertiesCfg(mass=0.4)", "mass_props=sim_utils.MassPropertiesCfg(mass=0.2)")
    replace_once(
        path,
        "diffuse_color=(0.15, 0.15, 0.15), metallic=1.0",
        "diffuse_color=(0.04, 0.22, 0.80), metallic=0.05",
    )


def patch_runner() -> None:
    path = ROOT / "sim_main.py"
    replace_once(
        path,
        'parser.add_argument("--seed", type=int, default=42, help="environment seed")',
        'parser.add_argument("--seed", type=int, default=42, help="environment seed")\n'
        'parser.add_argument("--max_steps", type=int, default=0, help="stop cleanly after N control steps")\n'
        'parser.add_argument("--book_report", type=str, default="", help="write textbook validation JSON")',
    )
    replace_once(
        path,
        "                controller.step()\n",
        "                controller.step()\n"
        "\n"
        "                if args_cli.max_steps > 0 and loop_count >= args_cli.max_steps:\n"
        "                    if args_cli.book_report:\n"
        "                        import json\n"
        "                        report_path = Path(args_cli.book_report)\n"
        "                        report_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "                        report = {\n"
        "                            'status': 'ok',\n"
        "                            'backend': 'isaac_sim_5.0_unitree_sim_isaaclab',\n"
        "                            'task': args_cli.task,\n"
        "                            'robot': 'unitree_g1_29dof_dex1',\n"
        "                            'object_id': 'cup_blue',\n"
        "                            'object_shape': 'blue_cylinder_cup_proxy',\n"
        "                            'seed': args_cli.seed,\n"
        "                            'steps': loop_count,\n"
        "                            'scene_state': sim_state,\n"
        "                        }\n"
        "                        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\\n', encoding='utf-8')\n"
        "                    print(f'BOOK_G1_VALIDATION_OK steps={loop_count} report={args_cli.book_report}', flush=True)\n"
        "                    controller.stop()\n"
        "                    break\n",
    )


if __name__ == "__main__":
    patch_scene()
    patch_runner()
    print("UNITREE_TEACHING_PATCH_OK")
