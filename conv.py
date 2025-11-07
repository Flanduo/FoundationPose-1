import os

def ply_to_obj_with_mtl(ply_path, obj_path):
    """
    将 PLY 文件转换为 OBJ+MTL 文件。
    支持顶点、面、颜色（如果 PLY 含有颜色）。
    """
    vertices = []
    colors = []
    faces = []
    
    with open(ply_path, 'r') as f:
        lines = f.readlines()

    # === 解析 PLY 头部 ===
    header_ended = False
    vertex_count = 0
    face_count = 0
    i = 0
    properties = []
    while not header_ended:
        line = lines[i].strip()
        if line.startswith('element vertex'):
            vertex_count = int(line.split()[-1])
        elif line.startswith('element face'):
            face_count = int(line.split()[-1])
        elif line.startswith('property'):
            properties.append(line.split()[-1])
        elif line == 'end_header':
            header_ended = True
        i += 1

    # === 判断是否包含颜色 ===
    has_color = all(c in properties for c in ['red', 'green', 'blue'])

    # === 读取顶点 ===
    for j in range(vertex_count):
        parts = lines[i + j].strip().split()
        x, y, z = map(float, parts[:3])
        vertices.append([x, y, z])

        if has_color:
            r, g, b = map(int, parts[3:6])
            colors.append([r / 255.0, g / 255.0, b / 255.0])
    i += vertex_count

    # === 读取面 ===
    for j in range(face_count):
        parts = lines[i + j].strip().split()
        if int(parts[0]) >= 3:
            face = [str(int(idx) + 1) for idx in parts[1:]]
            faces.append(face)

    # === 生成 MTL 文件 ===
    obj_dir = os.path.dirname(obj_path)
    obj_name = os.path.splitext(os.path.basename(obj_path))[0]
    mtl_path = os.path.join(obj_dir, f"{obj_name}.mtl")

    with open(mtl_path, 'w') as f:
        f.write(f"newmtl material_0\n")
        if has_color:
            f.write(f"Kd 1.0 1.0 1.0\n")  # 漫反射为白色，用顶点颜色显示
        else:
            f.write(f"Kd 0.8 0.8 0.8\n")  # 默认灰色
        f.write(f"Ka 0.2 0.2 0.2\n")
        f.write(f"Ks 0.0 0.0 0.0\n")
        f.write(f"d 1.0\n")
        f.write(f"illum 2\n")

    # === 生成 OBJ 文件 ===
    with open(obj_path, 'w') as f:
        f.write(f"mtllib {obj_name}.mtl\n")
        f.write(f"usemtl material_0\n")
        for idx, v in enumerate(vertices):
            if has_color:
                r, g, b = colors[idx]
                f.write(f"v {v[0]} {v[1]} {v[2]} {r} {g} {b}\n")
            else:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in faces:
            f.write(f"f {' '.join(face)}\n")

    print(f"✅ 转换完成:\n{ply_path}\n → {obj_path}\n → {mtl_path}")
    if has_color:
        print("🎨 检测到顶点颜色信息，已写入 OBJ 顶点。")
    else:
        print("⚪ 未检测到颜色属性，使用默认灰色材质。")

# 示例调用
if __name__ == "__main__":
    ply_file = "/home/wyf/mymnt/data_disk/Foundationpose/cad_mm/ply/needle_box_base.ply"    # 输入文件路径
    obj_file = "/home/wyf/mymnt/data_disk/Foundationpose/cad_mm/obj/needle_box_base.obj"   # 输出文件路径
    ply_to_obj_with_mtl(ply_file, obj_file)
