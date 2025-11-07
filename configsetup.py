import yaml
import os

def update_yaml_config(yaml_path, module_name):
    # 读取 YAML
    with open(yaml_path, "r") as f:
        cfg = yaml.safe_load(f)

    # ✅ 自动设置路径
    cfg["mesh_file"] = f"demo_data/module_{module_name}/mesh/{module_name}.obj"
    cfg["test_scene_dir"] = f"demo_data/module_{module_name}"
    cfg["debug_dir"] = f"debug/{module_name}"

    # ✅ 保存修改后的配置
    with open(yaml_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print(f"✅ YAML 已更新! 使用模块: {module_name}")
    return cfg

# ✅ 示例调用
if __name__ == "__main__":
    update_yaml_config("/home/wyf/Projects/FoundationPose/configs/mydemo.yaml", "tube_rack")
