import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"  # 指定使用 GPU1
import argparse
import json
import yaml as pyyaml
import trimesh
import logging
import cv2
import imageio
import numpy as np
import open3d as o3d

from estimater import *
from datareader import *
import paramiko
from scp import SCPClient
from datetime import datetime


def send_txt_scp(local_dir, remote_path):
    """
    将指定目录下的 .txt 文件传输到远程服务器。
    
    Args:
        local_dir (str): 本地目录，包含要传输的 .txt 文件
        remote_path (str): 远程服务器上的目标路径
    """
    hostname = '10.12.58.80'
    port = 22
    username = 'elwg'
    password = 'elwg224'

    txt_ext = ('.txt',)

    print("准备传输目录:", local_dir)

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
        print(f"已连接到远程主机: {hostname}")

        txt_files = [f for f in os.listdir(local_dir)
                     if f.lower().endswith(txt_ext) and os.path.isfile(os.path.join(local_dir, f))]
        
        if not txt_files:
            print(f"  (在 {local_dir} 中未找到 .txt 文件)")
            return

        print(f"  找到 {len(txt_files)} 个 .txt 文件，开始传输...")

        with SCPClient(ssh.get_transport()) as scp:
            success_count = 0
            for file in txt_files:
                try:
                    local_file_path = os.path.join(local_dir, file)
                    scp.put(local_file_path, remote_path)
                    print(f"  ✓ {file} 传输成功")
                    success_count += 1
                except Exception as e:
                    print(f"  ✗ {file} 传输失败: {e}")

            print(f"\n  传输完成: {success_count}/{len(txt_files)} 个文件成功")

    except Exception as e:
        print(f"  ✗ 连接或传输失败: {e}")
    finally:
        ssh.close()
        print("  SSH连接已关闭")

def send_files_scp(local_path, remote_path):
    """
    将指定文件或目录下的文件传输到远程服务器。
    
    Args:
        local_path (str): 本地目录或文件
        remote_path (str): 远程服务器路径（包括文件名或目录）
    """
    hostname = '10.12.58.80'
    port = 22
    username = 'elwg'
    password = 'elwg224'

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
        print(f"已连接到远程主机: {hostname}")

        with SCPClient(ssh.get_transport()) as scp:
            if os.path.isfile(local_path):
                scp.put(local_path, remote_path)
                print(f"✓ 文件 {local_path} 传输成功 -> {remote_path}")
            elif os.path.isdir(local_path):
                # 传输目录下所有文件
                for f in os.listdir(local_path):
                    full_path = os.path.join(local_path, f)
                    if os.path.isfile(full_path):
                        scp.put(full_path, remote_path)
                        print(f"✓ 文件 {full_path} 传输成功 -> {remote_path}")
            else:
                print(f"✗ 本地路径不存在: {local_path}")

    except Exception as e:
        print(f"✗ 连接或传输失败: {e}")
    finally:
        ssh.close()
        print("SSH连接已关闭")



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='configs/mydemo.json', help="Path to config file")
    args = parser.parse_args()

    # 读取配置
    with open(args.config, 'r') as f:
        cfg = json.load(f)

    set_logging_format()
    set_seed(0)

    # 使用配置里的路径
    mesh_file = cfg['mesh_file']
    test_scene_dir = cfg['test_scene_dir']
    est_refine_iter = cfg['est_refine_iter']
    track_refine_iter = cfg['track_refine_iter']
    debug = cfg['debug']
    debug_dir = cfg['debug_dir']

    # 加载 mesh
    mesh = trimesh.load(mesh_file)

    # 清理 debug 文件夹
    #if debug_dir is not None:
    #    os.system(f'rm -rf {debug_dir}/* && mkdir -p {debug_dir}/track_vis {debug_dir}/ob_in_cam')

    # 计算 bounding box
    to_origin, extents = trimesh.bounds.oriented_bounds(mesh)
    bbox = np.stack([-extents / 2, extents / 2], axis=0).reshape(2, 3)

    # 初始化 estimator
    scorer = ScorePredictor()
    refiner = PoseRefinePredictor()
    glctx = dr.RasterizeCudaContext()
    if isinstance(mesh, trimesh.Scene):
        mesh = list(mesh.geometry.values())[0]  # 假设场景中只有一个 mesh

    est = FoundationPose(
        model_pts=mesh.vertices,
        model_normals=mesh.vertex_normals,
        mesh=mesh,
        scorer=scorer,
        refiner=refiner,
        debug_dir=debug_dir,
        debug=debug,
        glctx=glctx
    )
    logging.info("estimator initialization done")

    # 数据读取
    reader = YcbineoatReader(video_dir=test_scene_dir, shorter_side=None, zfar=np.inf)

    for i in range(len(reader.color_files)):
        logging.info(f'i:{i}')
        color = reader.get_color(i)
        depth = reader.get_depth(i)

        if i == 0:
            mask = reader.get_mask(0).astype(bool)
            pose = est.register(K=reader.K, rgb=color, depth=depth, ob_mask=mask, iteration=est_refine_iter)

            if debug >= 3:
                m = mesh.copy()
                m.apply_transform(pose)
                m.export(f'{debug_dir}/model_tf.obj')

                xyz_map = depth2xyzmap(depth, reader.K)
                valid = depth >= 0.001
                pcd = toOpen3dCloud(xyz_map[valid], color[valid])
                o3d.io.write_point_cloud(f'{debug_dir}/scene_complete.ply', pcd)
        else:
            pose = est.track_one(rgb=color, depth=depth, K=reader.K, iteration=track_refine_iter)

        os.makedirs(f'{debug_dir}/ob_in_cam', exist_ok=True)
        np.savetxt(f'{debug_dir}/ob_in_cam/object_in_camera.txt', pose.reshape(4, 4))

        if debug >= 1:
            center_pose = pose @ np.linalg.inv(to_origin)
            vis = draw_posed_3d_box(reader.K, img=color, ob_in_cam=center_pose, bbox=bbox)
            vis = draw_xyz_axis(color, ob_in_cam=center_pose, scale=0.1, K=reader.K,
                                thickness=3, transparency=0, is_input_rgb=True)

        if debug >= 2:
            os.makedirs(f'{debug_dir}/track_vis', exist_ok=True)
            imageio.imwrite(f'{debug_dir}/track_vis/{reader.id_strs[i]}.png', vis)

    # 传输 txt 文件
    llcal_path = os.path.join(debug_dir, 'ob_in_cam')
    send_files_scp(llcal_path, '/home/elwg/dowload/ConnectionWithRobot (copy)/connectWithSever/received_files/object_in_camera.txt')

    # 传输可视化图片（假设你最后的 vis 保存为 vis_pem.png）
    vis_file = os.path.join(debug_dir, 'track_vis')
    send_files_scp(vis_file, '/home/elwg/dowload/ConnectionWithRobot (copy)/connectWithSever/received_files/vis_pem.png')
