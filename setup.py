import os

# 1. 自动创建文件夹结构
folders = ["images/简答", "images/问答"]
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"📁 已创建或确认文件夹存在: {folder}")

# 2. 自动生成部署所需的 requirements.txt 配置文件
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write("streamlit\n")
    f.write("extra-streamlit-components\n")
print("📄 已生成配置文件: requirements.txt")

print("\n🎉 环境初始化完成！请将 PDF 放入对应的文件夹中。")