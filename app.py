import streamlit as st
import random
import json
import os
import re
import base64
from datetime import date

# ==========================================
# 1. 内置题库 (按你的习惯，简答和问答分开编号)
# ==========================================
RAW_QUESTIONS = [
    # ---- 简答题部分 ----
    {"type": "简答", "num": 1, "question": "连续性介质假设"},
    {"type": "简答", "num": 2, "question": "水力坡度、水头损失"},
    {"type": "简答", "num": 3, "question": "弗劳德数Fr的物理意义"},
    {"type": "简答", "num": 4, "question": "温度对流体和气体的动力粘度分别有什么影响？"},
    {"type": "简答", "num": 5, "question": "水击现象是什么？"},
    {"type": "简答", "num": 6, "question": "如何判别恒定/非恒定流，均匀/非均匀流？"},
    {"type": "简答", "num": 7, "question": "减少水击的方法有哪些？"},
    {"type": "简答", "num": 8, "question": "判断缓流急流的方式都有哪些？列举两种。"},
    {"type": "简答", "num": 9, "question": "粘滞性的性质及雷诺数(Re)的性质。"},
    {"type": "简答", "num": 10, "question": "明渠均匀流的产生条件与特点。"},
    # 你可以继续添加简答题，num 顺延 11, 12...

    # ---- 问答题部分 ----
    {"type": "问答", "num": 1, "question": "水流进入阻力平方区，沿程摩擦系数怎么变？"},
    {"type": "问答", "num": 2, "question": "矩形断面宽浅明渠水流为均匀流，若n变大，Q不变，Fr怎么变，为何？"},
    {"type": "问答", "num": 3, "question": "尼古拉兹实验中沿程阻力系数怎么变化？"},
    {"type": "问答", "num": 4, "question": "同样水头下，为何实用堰比宽顶堰的过水能力更强？"},
    {"type": "问答", "num": 5, "question": "泄水建筑物下游常用何种水面衔接和消能措施？怎么确定水跃位置？"}
    # 你可以继续添加问答题，num 顺延 6, 7...
]

# ==========================================
# 2. 数据与文件匹配逻辑
# ==========================================
DATA_FILE = "review_progress.json"
IMAGE_DIR = "images"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mastered_ids": [], "check_ins": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# 核心升级：根据题型去对应的文件夹里找 PDF
def find_file_for_question(q_type, q_num):
    # 拼接出对应的子文件夹路径，例如 images/简答
    type_dir = os.path.join(IMAGE_DIR, q_type)

    if not os.path.exists(type_dir):
        return None

    for filename in os.listdir(type_dir):
        # 匹配 "1-3.pdf" 这种格式
        range_match = re.match(r"(\d+)-(\d+)\.\w+", filename)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start <= q_num <= end:
                return os.path.join(type_dir, filename)

        # 也兼容单独的 "1.pdf" 格式
        single_match = re.match(r"(\d+)\.\w+", filename)
        if single_match:
            if int(single_match.group(1)) == q_num:
                return os.path.join(type_dir, filename)

    return None


# ==========================================
# 3. 初始化网页与会话状态
# ==========================================
st.set_page_config(page_title="895 水力学复习神器", page_icon="🌊", layout="centered")

if "app_data" not in st.session_state:
    st.session_state.app_data = load_data()
if "current_batch" not in st.session_state:
    st.session_state.current_batch = []
if "batch_index" not in st.session_state:
    st.session_state.batch_index = 0
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

data = st.session_state.app_data
mastered_ids = data["mastered_ids"]
today_str = str(date.today())

# ==========================================
# 4. 侧边栏：控制台
# ==========================================
with st.sidebar:
    st.header("⚙️ 学习控制台")

    total_q = len(RAW_QUESTIONS)
    mastered_q = len(mastered_ids)
    st.progress(mastered_q / total_q if total_q > 0 else 0)
    st.write(f"**总进度:** {mastered_q} / {total_q} 题")

    st.markdown("---")
    num_to_draw = st.slider("今天想复习多少题？", min_value=1, max_value=20, value=5)

    if st.button("🎲 开始今日抽取", use_container_width=True):
        # 使用 "类型_题号" 作为唯一标识，例如 "简答_1"
        remaining = [q for q in RAW_QUESTIONS if f"{q['type']}_{q['num']}" not in mastered_ids]
        if not remaining:
            st.success("🎉 题库已全部掌握！")
        else:
            draw_size = min(num_to_draw, len(remaining))
            st.session_state.current_batch = random.sample(remaining, draw_size)
            st.session_state.batch_index = 0
            st.session_state.show_answer = False
            st.rerun()

    st.markdown("---")
    st.header("📅 打卡记录")
    if data["check_ins"]:
        for date_key, count in sorted(data["check_ins"].items(), reverse=True)[:5]:
            st.write(f"✅ {date_key}: 完成 {count} 题")
    else:
        st.write("暂无记录，今天开始加油！")

    st.markdown("---")
    if st.button("⚠️ 重置所有进度"):
        st.session_state.app_data = {"mastered_ids": [], "check_ins": data["check_ins"]}
        save_data(st.session_state.app_data)
        st.session_state.current_batch = []
        st.rerun()

# ==========================================
# 5. 主区域：刷题与 PDF 预览
# ==========================================
st.title("🌊 895 专属复习打卡系统")

if not st.session_state.current_batch:
    st.info("👈 请在左侧设定题量并点击【开始今日抽取】")
else:
    batch = st.session_state.current_batch
    idx = st.session_state.batch_index

    if idx < len(batch):
        current_q = batch[idx]
        # 生成唯一标识，如 "简答_1"
        unique_id = f"{current_q['type']}_{current_q['num']}"

        st.caption(f"当前进度：第 {idx + 1} 题 / 共 {len(batch)} 题")

        st.markdown(f"### 【{current_q['type']}】第 {current_q['num']} 题")
        st.markdown(f"## {current_q['question']}")

        # 核心：同时传入题型和题号去找文件
        file_path = find_file_for_question(current_q['type'], current_q['num'])

        if st.button("👁️ 查看我的笔记答案", use_container_width=True):
            st.session_state.show_answer = not st.session_state.show_answer

        if st.session_state.show_answer:
            if file_path:
                ext = file_path.split('.')[-1].lower()
                st.caption(f"已自动匹配到文件: {current_q['type']} / {os.path.basename(file_path)}")

                if ext == 'pdf':
                    with open(file_path, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    st.image(file_path, use_container_width=True)
            else:
                st.warning(f"⚠️ 找不到对应的笔记。请检查是否将文件放入了 images/{current_q['type']} 文件夹中。")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏭️ 暂时跳过 (下次再背)", use_container_width=True):
                st.session_state.batch_index += 1
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            if st.button("✅ 我已掌握，不再出现", type="primary", use_container_width=True):
                mastered_ids.append(unique_id)
                if today_str not in data["check_ins"]:
                    data["check_ins"][today_str] = 0
                data["check_ins"][today_str] += 1
                save_data(st.session_state.app_data)

                st.session_state.batch_index += 1
                st.session_state.show_answer = False
                st.rerun()
    else:
        st.success("🎯 恭喜！今天抽取的题目已经全部过完啦！")
        st.balloons()
        if st.button("完成并返回"):
            st.session_state.current_batch = []
            st.session_state.batch_index = 0
            st.rerun()
