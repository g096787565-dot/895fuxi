import os


folders = ["images/简答", "images/问答"]
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"已创建或确认文件夹存在：{folder}")

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write("streamlit\n")
    f.write("extra-streamlit-components\n")
    f.write("PyMuPDF\n")

print("已生成 requirements.txt")
print("环境初始化完成。请将 PDF 放入 images/简答 和 images/问答。")
