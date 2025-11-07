from PIL import Image
import numpy as np

# 读取图像
img = Image.open("/home/wyf/Projects/FoundationPose/demo_data/module1/depth/new1.png")
print("模式:", img.mode)

# 如果想看具体像素深度
arr = np.array(img)
print("数据类型:", arr.dtype)
print("最小值:", arr.min(), "最大值:", arr.max())