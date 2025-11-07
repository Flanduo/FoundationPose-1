import os
import shutil
import subprocess
import time

# 源文件目录
BASE_DIR = "/home/wyf/Projects/FoundationPose/newdata"
RGB_DIR = os.path.join(BASE_DIR, "rgb")
DEPTH_DIR = os.path.join(BASE_DIR, "depth")
MASK_DIR = os.path.join(BASE_DIR, "masks")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# demodebug.py 读取的固定路径（目标目录）
DEMO_DATA_DIR = "/home/wyf/Projects/FoundationPose/demo_data/module_needle_box_base"
FIXED_RGB = os.path.join(DEMO_DATA_DIR, "rgb", "new.png")
FIXED_MASK = os.path.join(DEMO_DATA_DIR, "masks", "new.png")
FIXED_DEPTH = os.path.join(DEMO_DATA_DIR, "depth", "new.png")

# 确保目标目录存在
os.makedirs(os.path.join(DEMO_DATA_DIR, "rgb"), exist_ok=True)
os.makedirs(os.path.join(DEMO_DATA_DIR, "mask"), exist_ok=True)
os.makedirs(os.path.join(DEMO_DATA_DIR, "depth"), exist_ok=True)

# 固定 RGB 顺序
RGB_NAMES = ["c1", "c2", "c3", "c4", "c5"]

print("="*70)
print("开始批处理图像...")
print(f"源目录: {BASE_DIR}")
print(f"目标目录: {DEMO_DATA_DIR}")
print("="*70)

for idx, rgb_name in enumerate(RGB_NAMES, 1):
    print(f"\n{'='*70}")
    print(f"处理进度: [{idx}/{len(RGB_NAMES)}] RGB组: {rgb_name}")
    print("="*70)
    
    rgb_file = os.path.join(RGB_DIR, f"{rgb_name}.png")
    mask_file = os.path.join(MASK_DIR, f"{rgb_name}_yellow_pipette_tip_box.png")

    # 三张对应 depth
    depth_files = [
        os.path.join(DEPTH_DIR, f"d{rgb_name[1:]}.png"),          # d1, d2 ...
        os.path.join(DEPTH_DIR, f"{rgb_name}_depth.png"),
        os.path.join(DEPTH_DIR, f"{rgb_name}_depth_scaled.png")
    ]

    # 检查 RGB 和 Mask 是否存在
    if not os.path.exists(rgb_file):
        print(f"[SKIP] RGB 文件不存在: {rgb_file}")
        continue
    if not os.path.exists(mask_file):
        print(f"[SKIP] Mask 文件不存在: {mask_file}")
        continue

    for depth_idx, depth_path in enumerate(depth_files, 1):
        if not os.path.exists(depth_path):
            print(f"[SKIP] Depth 文件不存在: {depth_path}")
            continue

        print(f"\n--- 处理 Depth 文件 [{depth_idx}/{len(depth_files)}] ---")
        
        # 显示源文件信息
        print(f"源文件:")
        print(f"  RGB:   {rgb_file}")
        print(f"  Mask:  {mask_file}")
        print(f"  Depth: {depth_path}")

        # 复制文件到固定路径
        print(f"\n复制文件到目标路径...")
        try:
            # 先删除旧文件（确保没有残留）
            for fixed_file in [FIXED_RGB, FIXED_MASK, FIXED_DEPTH]:
                if os.path.exists(fixed_file):
                    os.remove(fixed_file)
                    print(f"  删除旧文件: {fixed_file}")
            
            # 复制新文件
            shutil.copy2(rgb_file, FIXED_RGB)
            shutil.copy2(mask_file, FIXED_MASK)
            shutil.copy2(depth_path, FIXED_DEPTH)
            
            # 验证文件已复制
            assert os.path.exists(FIXED_RGB), f"RGB 复制失败: {FIXED_RGB}"
            assert os.path.exists(FIXED_MASK), f"Mask 复制失败: {FIXED_MASK}"
            assert os.path.exists(FIXED_DEPTH), f"Depth 复制失败: {FIXED_DEPTH}"
            
            print(f"  ✓ RGB  -> {FIXED_RGB}")
            print(f"  ✓ Mask -> {FIXED_MASK}")
            print(f"  ✓ Depth-> {FIXED_DEPTH}")
            
            # 给文件系统一点时间同步
            time.sleep(0.2)
            
        except Exception as e:
            print(f"[ERROR] 文件复制失败: {e}")
            continue

        # 准备输出目录
        depth_label = os.path.splitext(os.path.basename(depth_path))[0]
        out_dir = os.path.join(OUTPUT_DIR, rgb_name, depth_label)
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
                "--config", 
                "/home/wyf/Projects/FoundationPose/configs/mydemo.json"
            ], 
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print(f"  ✓ 处理成功")
            else:
                print(f"  ✗ 处理失败 (返回码: {result.returncode})")
                if result.stderr:
                    print(f"  错误信息: {result.stderr[:500]}")
                if result.stdout:
                    print(f"  标准输出: {result.stdout[:500]}")
                    
        except subprocess.TimeoutExpired:
            print(f"  ✗ 处理超时（超过5分钟）")
        except Exception as e:
            print(f"  ✗ 运行出错: {e}")

        print(f"\n[完成] RGB={rgb_name}, Depth={depth_label} -> {out_dir}")

print("\n" + "="*70)
print("所有处理完成！")
print(f"结果保存在: {OUTPUT_DIR}")
print("="*70)