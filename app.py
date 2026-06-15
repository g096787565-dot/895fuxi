import base64
import json
import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import streamlit as st


APP_TITLE = "895 水力学复习打卡"
DATA_FILE = Path("review_progress.json")
IMAGE_DIR = Path("images")
QUESTION_TYPES = ("简答", "问答")


@dataclass(frozen=True)
class Question:
    q_type: str
    number: int
    file_path: Path

    @property
    def qid(self) -> str:
        return f"{self.q_type}_{self.number}"

    @property
    def title(self) -> str:
        return f"{self.q_type}题 第 {self.number} 题"

    @property
    def prompt(self) -> str:
        return f"请先独立回忆 {self.title} 的答案要点，再查看笔记核对。"


def load_data() -> dict:
    if not DATA_FILE.exists():
        return {"mastered_ids": [], "check_ins": {}}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"mastered_ids": [], "check_ins": {}}

    return {
        "mastered_ids": list(dict.fromkeys(data.get("mastered_ids", []))),
        "check_ins": data.get("check_ins", {}),
    }


def save_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_pdf_numbers(filename: str) -> list[int]:
    match = re.fullmatch(r"(\d+)(?:-(\d+))?\.pdf", filename, flags=re.IGNORECASE)
    if not match:
        return []

    start = int(match.group(1))
    end = int(match.group(2) or start)
    if end < start:
        return []
    return list(range(start, end + 1))


@st.cache_data(show_spinner=False)
def discover_questions() -> tuple[list[dict], dict[str, int]]:
    questions: list[dict] = []
    counts = {"简答": 0, "问答": 0, "pdf_files": 0}

    for q_type in QUESTION_TYPES:
        folder = IMAGE_DIR / q_type
        if not folder.exists():
            continue

        for file_path in sorted(folder.glob("*.pdf"), key=lambda p: p.name):
            numbers = parse_pdf_numbers(file_path.name)
            if not numbers:
                continue

            counts[q_type] += len(numbers)
            counts["pdf_files"] += 1
            for number in numbers:
                questions.append(
                    {
                        "q_type": q_type,
                        "number": number,
                        "file_path": str(file_path),
                    }
                )

    questions.sort(key=lambda q: (q["q_type"], q["number"]))
    return questions, counts


def to_question(raw: dict) -> Question:
    return Question(
        q_type=raw["q_type"],
        number=int(raw["number"]),
        file_path=Path(raw["file_path"]),
    )


def init_session() -> None:
    defaults = {
        "app_data": load_data(),
        "current_batch": [],
        "batch_index": 0,
        "show_answer": False,
        "last_draw_types": list(QUESTION_TYPES),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_batch() -> None:
    st.session_state.current_batch = []
    st.session_state.batch_index = 0
    st.session_state.show_answer = False


def draw_batch(questions: list[dict], selected_types: list[str], draw_count: int) -> None:
    mastered = set(st.session_state.app_data["mastered_ids"])
    remaining = [
        q
        for q in questions
        if q["q_type"] in selected_types and f"{q['q_type']}_{q['number']}" not in mastered
    ]

    if not remaining:
        reset_batch()
        st.toast("当前筛选范围内没有待复习题目。")
        return

    draw_size = min(draw_count, len(remaining))
    st.session_state.current_batch = random.sample(remaining, draw_size)
    st.session_state.batch_index = 0
    st.session_state.show_answer = False


def mark_mastered(question: Question) -> None:
    data = st.session_state.app_data
    if question.qid not in data["mastered_ids"]:
        data["mastered_ids"].append(question.qid)

    today = str(date.today())
    data["check_ins"][today] = data["check_ins"].get(today, 0) + 1
    save_data(data)


def unmark_mastered(question: Question) -> None:
    data = st.session_state.app_data
    data["mastered_ids"] = [qid for qid in data["mastered_ids"] if qid != question.qid]
    save_data(data)


def render_pdf(file_path: Path) -> None:
    if not file_path.exists():
        st.warning(f"没有找到答案文件：{file_path}")
        return

    with file_path.open("rb") as f:
        encoded_pdf = base64.b64encode(f.read()).decode("utf-8")

    st.markdown(
        f"""
        <iframe
            src="data:application/pdf;base64,{encoded_pdf}"
            width="100%"
            height="760"
            style="border: 1px solid #d8dee9; border-radius: 8px; background: white;"
            type="application/pdf">
        </iframe>
        """,
        unsafe_allow_html=True,
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.4rem;
            max-width: 1180px;
        }
        section[data-testid="stSidebar"] {
            background: #f7f9fc;
            border-right: 1px solid #e6ebf2;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e6ebf2;
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
        }
        .study-header {
            padding: 0.2rem 0 1rem 0;
            border-bottom: 1px solid #e6ebf2;
            margin-bottom: 1.2rem;
        }
        .study-header h1 {
            font-size: 2rem;
            margin: 0;
            letter-spacing: 0;
        }
        .study-subtitle {
            color: #526070;
            margin-top: 0.35rem;
        }
        .question-card {
            border: 1px solid #dfe6ee;
            border-radius: 8px;
            padding: 1.15rem 1.25rem;
            background: #ffffff;
            margin: 0.75rem 0 1rem 0;
        }
        .question-kicker {
            color: #4d6277;
            font-size: 0.95rem;
            margin-bottom: 0.35rem;
        }
        .question-title {
            font-size: 1.65rem;
            font-weight: 720;
            color: #17212b;
            margin-bottom: 0.45rem;
        }
        .question-prompt {
            color: #384858;
            font-size: 1.02rem;
            line-height: 1.65;
        }
        .answer-note {
            background: #f4f8fb;
            border: 1px solid #dce7f0;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            color: #34495e;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(questions: list[dict], counts: dict[str, int]) -> None:
    data = st.session_state.app_data
    mastered_ids = set(data["mastered_ids"])
    total_questions = len(questions)
    mastered_count = len([q for q in questions if f"{q['q_type']}_{q['number']}" in mastered_ids])
    today_done = data["check_ins"].get(str(date.today()), 0)

    with st.sidebar:
        st.header("学习控制台")
        st.progress(mastered_count / total_questions if total_questions else 0)

        c1, c2 = st.columns(2)
        c1.metric("已掌握", mastered_count)
        c2.metric("总题数", total_questions)
        st.metric("今日完成", today_done)

        st.caption(f"已识别 PDF：{counts.get('pdf_files', 0)} 个")
        st.caption(f"简答题：{counts.get('简答', 0)} 题 · 问答题：{counts.get('问答', 0)} 题")
        st.divider()

        selected_types = st.multiselect(
            "题型",
            options=list(QUESTION_TYPES),
            default=st.session_state.last_draw_types,
            help="可以只抽简答或只抽问答。",
        )
        if not selected_types:
            selected_types = list(QUESTION_TYPES)

        max_draw = max(1, min(30, total_questions or 1))
        draw_count = st.slider("本轮抽题数量", min_value=1, max_value=max_draw, value=min(10, max_draw))

        if st.button("开始随机抽题", type="primary", use_container_width=True):
            st.session_state.last_draw_types = selected_types
            draw_batch(questions, selected_types, draw_count)
            st.rerun()

        if st.button("清空本轮", use_container_width=True):
            reset_batch()
            st.rerun()

        st.divider()
        st.subheader("最近打卡")
        recent = sorted(data["check_ins"].items(), reverse=True)[:7]
        if recent:
            for day, count in recent:
                st.write(f"{day}：完成 {count} 题")
        else:
            st.caption("还没有打卡记录。")

        st.divider()
        if st.button("重置已掌握进度", use_container_width=True):
            st.session_state.app_data = {"mastered_ids": [], "check_ins": data["check_ins"]}
            save_data(st.session_state.app_data)
            reset_batch()
            st.rerun()


def render_empty_state(questions: list[dict]) -> None:
    if not questions:
        st.error("没有识别到题库 PDF。请确认 `images/简答` 和 `images/问答` 中有 PDF 文件。")
        return

    st.info("在左侧选择题型和数量，然后点击“开始随机抽题”。")

    col1, col2, col3 = st.columns(3)
    col1.metric("复习方式", "随机抽题")
    col2.metric("答案来源", "PDF 笔记")
    col3.metric("掌握规则", "掌握后不再抽")


def render_question_workspace() -> None:
    batch = st.session_state.current_batch
    if not batch:
        return

    index = min(st.session_state.batch_index, len(batch) - 1)
    st.session_state.batch_index = index
    question = to_question(batch[index])
    mastered = question.qid in set(st.session_state.app_data["mastered_ids"])

    st.caption(f"本轮进度：第 {index + 1} / {len(batch)} 题")
    st.progress((index + 1) / len(batch))

    st.markdown(
        f"""
        <div class="question-card">
            <div class="question-kicker">{question.q_type} · PDF：{question.file_path.name}</div>
            <div class="question-title">{question.title}</div>
            <div class="question-prompt">{question.prompt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav1, nav2, nav3, nav4 = st.columns([1, 1, 1.2, 1.4])
    if nav1.button("上一题", use_container_width=True, disabled=index == 0):
        st.session_state.batch_index -= 1
        st.session_state.show_answer = False
        st.rerun()
    if nav2.button("下一题", use_container_width=True, disabled=index >= len(batch) - 1):
        st.session_state.batch_index += 1
        st.session_state.show_answer = False
        st.rerun()
    if nav3.button("显示/隐藏答案", use_container_width=True):
        st.session_state.show_answer = not st.session_state.show_answer
        st.rerun()
    if nav4.button("标记已掌握", type="primary", use_container_width=True, disabled=mastered):
        mark_mastered(question)
        if index < len(batch) - 1:
            st.session_state.batch_index += 1
        st.session_state.show_answer = False
        st.rerun()

    aux1, aux2 = st.columns([1, 1])
    if aux1.button("暂时跳过", use_container_width=True):
        if index < len(batch) - 1:
            st.session_state.batch_index += 1
        st.session_state.show_answer = False
        st.rerun()
    if aux2.button("撤销本题已掌握", use_container_width=True, disabled=not mastered):
        unmark_mastered(question)
        st.rerun()

    if mastered:
        st.success("这道题已在你的掌握列表中。")

    if st.session_state.show_answer:
        st.markdown(
            f"""
            <div class="answer-note">
                已打开答案笔记：<strong>{question.file_path.as_posix()}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_pdf(question.file_path)

    if index == len(batch) - 1:
        st.caption("已经到本轮最后一题。可以继续标记掌握，或从左侧重新抽一轮。")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")
    inject_css()
    init_session()

    questions, counts = discover_questions()
    render_sidebar(questions, counts)

    st.markdown(
        """
        <div class="study-header">
            <h1>895 水力学复习打卡</h1>
            <div class="study-subtitle">随机抽题、按需查看 PDF 笔记、记录已掌握题目。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.current_batch:
        render_question_workspace()
    else:
        render_empty_state(questions)


if __name__ == "__main__":
    main()
