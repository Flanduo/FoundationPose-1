import os
import shutil
import subprocess
import time
import json
from datetime import datetime


# 源文件目录（所有文件放在同一个文件夹）
BASE_DIR = "/home/wyf/Projects/FoundationPose/connect/12_images"
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# 已处理文件归档目录
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

# demodebug.py 读取的固定路径（目标目录基路径）
DEMO_DATA_BASE = "/home/wyf/Projects/FoundationPose/demo_data"

# 相机参数文件目录
CAM_K_DIR = "/home/wyf/Projects/FoundationPose/demo_data/cam_K"

# 配置文件路径
CONFIG_FILE = "/home/wyf/Projects/FoundationPose/configs/mydemo.json"

# 监听配置
CHECK_INTERVAL = 5  # 每5秒检查一次
running = True  # 控制循环


def parse_filename(filename):
    """解析文件名，提取相机型号和对象名
    例如：color_d435i_needle_box_base.png
    返回：(file_type, camera_model, object_name)
    """
    if not filename.endswith('.png'):
        return None, None, None
    
    name_without_ext = filename[:-4]
    parts = name_without_ext.split('_', 2)  # 最多分3部分
    
    if len(parts) < 3:
        return None, None, None
    
    file_type = parts[0]  # color, mask, depth
    camera_model = parts[1]  # d435, d435i
    object_name = parts[2]  # needle_box_base
    
    return file_type, camera_model, object_name


def get_files_info():
    """获取BASE_DIR中的文件信息
    返回：(camera_model, object_name, rgb_file, mask_file, depth_file) 或 None
    """
    if not os.path.exists(BASE_DIR):
        return None
    
    files = [f for f in os.listdir(BASE_DIR) if f.endswith('.png')]
    
    if len(files) < 3:
        return None
    
    rgb_file = None
    mask_file = None
    depth_file = None
    camera_model = None
    object_name = None
    
    for filename in files:
        file_type, cam_model, obj_name = parse_filename(filename)
        
        if file_type == 'color':
            rgb_file = os.path.join(BASE_DIR, filename)
            camera_model = cam_model
            object_name = obj_name
        elif file_type == 'mask':
            mask_file = os.path.join(BASE_DIR, filename)
        elif file_type == 'depth':
            depth_file = os.path.join(BASE_DIR, filename)
    
    # 检查是否三个文件都找到了
    if all([rgb_file, mask_file, depth_file, camera_model, object_name]):
        return camera_model, object_name, rgb_file, mask_file, depth_file
    
    return None


def is_base_dir_ready():
    """检查BASE_DIR是否有待处理的文件（三张图都齐全）"""
    files_info = get_files_info()
    return files_info is not None


def copy_camera_params(camera_model, target_dir):
    """根据相机型号复制对应的相机参数文件
    
    Args:
        camera_model: 相机型号 (d435 或 d435i)
        target_dir: 目标目录路径
    """
    # 源相机参数文件
    src_cam_k = os.path.join(CAM_K_DIR, f"{camera_model}.txt")
    
    # 目标相机参数文件
    dst_cam_k = os.path.join(target_dir, "cam_K.txt")
    
    if not os.path.exists(src_cam_k):
        print(f"[WARNING] 相机参数文件不存在: {src_cam_k}")
        return False
    
    try:
        shutil.copy2(src_cam_k, dst_cam_k)
        print(f"  ✓ 相机参数: {camera_model}.txt -> cam_K.txt")
        return True
    except Exception as e:
        print(f"[ERROR] 复制相机参数失败: {e}")
        return False


def update_config_file(object_name):
    """更新配置文件中的object_name
    
    Args:
        object_name: 对象名称（如：needle_box_base）
    
    Returns:
        bool: 更新是否成功
    """
    try:
        # 读取现有配置
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 更新所有包含对象名的路径
        config['mesh_file'] = f"/home/wyf/Projects/FoundationPose/demo_data/module_{object_name}/mesh/{object_name}.obj"
        config['test_scene_dir'] = f"/home/wyf/Projects/FoundationPose/demo_data/module_{object_name}"
        config['debug_dir'] = f"debug/{object_name}"
        
        # 写回配置文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print(f"  ✓ 配置文件已更新:")
        print(f"    - mesh_file: module_{object_name}/mesh/{object_name}.obj")
        print(f"    - test_scene_dir: module_{object_name}")
        print(f"    - debug_dir: debug/{object_name}")
        
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] 配置文件不存在: {CONFIG_FILE}")
        return False
    except json.JSONDecodeError as e:
        print(f"[ERROR] 配置文件JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 更新配置文件失败: {e}")
        return False


def process_batch():
    """处理一批文件"""
    
    # 获取文件信息
    files_info = get_files_info()
    
    if files_info is None:
        print("[ERROR] 文件不完整或无法识别")
        return
    
    camera_model, object_name, rgb_file, mask_file, depth_file = files_info
    
    print("="*70)
    print(f"开始处理图像...")
    print(f"  相机型号: {camera_model}")
    print(f"  对象名称: {object_name}")
    print(f"  源目录: {BASE_DIR}")
    print("="*70)
    
    # 显示源文件信息
    print(f"\n源文件:")
    print(f"  RGB:   {os.path.basename(rgb_file)}")
    print(f"  Mask:  {os.path.basename(mask_file)}")
    print(f"  Depth: {os.path.basename(depth_file)}")
    
    # 构建目标目录 (只用对象名，不含相机型号)
    DEMO_DATA_DIR = os.path.join(DEMO_DATA_BASE, f"module_{object_name}")
    FIXED_RGB = os.path.join(DEMO_DATA_DIR, "rgb", "new.png")
    FIXED_MASK = os.path.join(DEMO_DATA_DIR, "masks", "new.png")
    FIXED_DEPTH = os.path.join(DEMO_DATA_DIR, "depth", "new.png")
    
    print(f"\n目标目录: {DEMO_DATA_DIR}")
    
    # 确保目标目录存在
    os.makedirs(os.path.join(DEMO_DATA_DIR, "rgb"), exist_ok=True)
    os.makedirs(os.path.join(DEMO_DATA_DIR, "masks"), exist_ok=True)
    os.makedirs(os.path.join(DEMO_DATA_DIR, "depth"), exist_ok=True)

    # 更新配置文件
    print(f"\n更新配置文件...")
    if not update_config_file(object_name):
        print("[WARNING] 配置文件更新失败，继续处理...")

    # 复制文件到固定路径
    print(f"\n复制文件到目标路径...")
    try:
        # 先删除旧文件（确保没有残留）
        for fixed_file in [FIXED_RGB, FIXED_MASK, FIXED_DEPTH]:
            if os.path.exists(fixed_file):
                os.remove(fixed_file)
        
        # 复制新文件
        shutil.copy2(rgb_file, FIXED_RGB)
        shutil.copy2(mask_file, FIXED_MASK)
        shutil.copy2(depth_file, FIXED_DEPTH)
        
        # 验证文件已复制
        assert os.path.exists(FIXED_RGB), f"RGB 复制失败: {FIXED_RGB}"
        assert os.path.exists(FIXED_MASK), f"Mask 复制失败: {FIXED_MASK}"
        assert os.path.exists(FIXED_DEPTH), f"Depth 复制失败: {FIXED_DEPTH}"
        
        print(f"  ✓ RGB  -> rgb/new.png")
        print(f"  ✓ Mask -> masks/new.png")
        print(f"  ✓ Depth-> depth/new.png")
        
    except Exception as e:
        print(f"[ERROR] 文件复制失败: {e}")
        return
    
    # 复制相机参数文件
    print(f"\n复制相机参数文件...")
    if not copy_camera_params(camera_model, DEMO_DATA_DIR):
        print("[WARNING] 相机参数复制失败，继续处理...")
    
    # 给文件系统一点时间同步
    time.sleep(0.2)

    # 准备输出目录
    out_dir = os.path.join(OUTPUT_DIR, f"{camera_model}_{object_name}")
    os.makedirs(out_dir, exist_ok=True)

    # 设置环境变量
    env = {**os.environ, "DEBUG_DIR_OVERRIDE": out_dir}

    print(f"\n运行 demodebug.py...")
    print(f"  输出目录: {out_dir}")
    
    # 调用 demodebug.py
    try:
        result = subprocess.run([
        "python3",
        "/home/wyf/Projects/FoundationPose/demodebug.py",
        "--config", CONFIG_FILE
        ],
        capture_output=True,  # 捕获 stdout 和 stderr
        text=True,            # 以文本形式返回
        timeout=300
        )

        if result.returncode == 0:
            print("✓ 处理成功")
        else:
            print("✗ 运行出错")
            print("----- STDOUT -----")
            print(result.stdout)
            print("----- STDERR -----")
            print(result.stderr)

                
    except subprocess.TimeoutExpired:
        print(f"  ✗ 处理超时（超过5分钟）")
    except Exception as e:
        print(f"  ✗ 运行出错: {e}")

    print(f"\n[完成] 结果保存至: {out_dir}")
    print("="*70)


def archive_processed_files():
    """将处理完的文件移动到processed目录"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_dir = os.path.join(PROCESSED_DIR, timestamp)
    
    print(f"\n归档处理完的文件到: {archived_dir}")
    
    try:
        # 获取BASE_DIR下所有png文件
        png_files = [f for f in os.listdir(BASE_DIR) 
                     if f.endswith('.png') and os.path.isfile(os.path.join(BASE_DIR, f))]
        
        if not png_files:
            print("  (无文件需要归档)")
            return
        
        os.makedirs(archived_dir, exist_ok=True)
        
        # 移动所有png文件
        moved_count = 0
        for filename in png_files:
            src = os.path.join(BASE_DIR, filename)
            dst = os.path.join(archived_dir, filename)
            shutil.move(src, dst)
            moved_count += 1
        
        print(f"  ✓ 已移动 {moved_count} 个文件")
        print(f"✓ 归档完成: {archived_dir}")
        
    except Exception as e:
        print(f"✗ 归档失败: {e}")


def monitor_and_process():
    """主监听循环"""
    global running
    
    print("\n" + "="*70)
    print("文件监听服务已启动")
    print(f"监听目录: {BASE_DIR}")
    print(f"配置文件: {CONFIG_FILE}")
    print(f"检查间隔: {CHECK_INTERVAL}秒")
    print("\n文件格式要求 (所有文件放在同一目录):")
    print("  - color_<相机型号>_<对象名>.png")
    print("  - mask_<相机型号>_<对象名>.png")
    print("  - depth_<相机型号>_<对象名>.png")
    print("\n示例:")
    print("  - color_d435i_needle_box_base.png")
    print("  - mask_d435i_needle_box_base.png")
    print("  - depth_d435i_needle_box_base.png")
    print("\n支持的相机型号: d435, d435i")
    print("\n按 Ctrl+C 停止监听")
    print("="*70 + "\n")
    
    try:
        while running:
            # 检查是否有文件需要处理
            if is_base_dir_ready():
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检测到新文件，开始处理...")
                
                # 处理文件
                process_batch()
                
                # 归档已处理的文件
                archive_processed_files()
                
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 等待下一批文件...")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("收到停止信号，正在退出...")
        print("="*70)
        running = False


if __name__ == "__main__":
    # 确保必要的目录存在
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_FILE):
        print(f"[WARNING] 配置文件不存在: {CONFIG_FILE}")
    
    # 检查相机参数目录是否存在
    if not os.path.exists(CAM_K_DIR):
        print(f"[WARNING] 相机参数目录不存在: {CAM_K_DIR}")
        print("请确保以下文件存在:")
        print(f"  - {CAM_K_DIR}/d435.txt")
        print(f"  - {CAM_K_DIR}/d435i.txt")
    
    # 启动监听
    monitor_and_process()