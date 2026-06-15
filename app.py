import base64
import json
import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

try:
    import extra_streamlit_components as stx
except ImportError:  # pragma: no cover - handled in the UI for missing installs.
    stx = None

try:
    import fitz
except ImportError:  # pragma: no cover - handled in the UI for missing installs.
    fitz = None


APP_TITLE = "895 水力学复习打卡"
COOKIE_NAME = "895_hydraulics_review_progress_v2"
QUESTIONS_FILE = Path("questions.json")
IMAGE_DIR = Path("images")
QUESTION_TYPES = ("简答", "问答")


@dataclass(frozen=True)
class Question:
    q_type: str
    number: int
    file_path: Path
    prompt_text: str = ""

    @property
    def qid(self) -> str:
        return f"{self.q_type}_{self.number}"

    @property
    def title(self) -> str:
        return f"{self.q_type}题 第 {self.number} 题"

    @property
    def prompt(self) -> str:
        if self.prompt_text.strip():
            return self.prompt_text.strip()
        return (
            f"这道题还没有录入文字题干。请在 questions.json 中补充 {self.qid}，"
            "当前可先按题号复习，并点击“显示/隐藏答案”查看下方 PDF 图片。"
        )


def empty_progress() -> dict:
    return {"mastered_ids": [], "check_ins": {}}


def normalize_progress(data: object) -> dict:
    if not isinstance(data, dict):
        return empty_progress()

    mastered_ids = data.get("mastered_ids", [])
    if not isinstance(mastered_ids, list):
        mastered_ids = []

    check_ins = data.get("check_ins", {})
    if not isinstance(check_ins, dict):
        check_ins = {}

    return {
        "mastered_ids": list(dict.fromkeys(str(item) for item in mastered_ids)),
        "check_ins": {str(day): int(count) for day, count in check_ins.items() if str(count).isdigit()},
    }


def encode_progress_cookie(data: dict) -> str:
    payload = json.dumps(normalize_progress(data), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_progress_cookie(raw_value: object) -> dict:
    if not isinstance(raw_value, str) or not raw_value:
        return empty_progress()

    try:
        padded = raw_value + "=" * (-len(raw_value) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        return normalize_progress(json.loads(payload))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return empty_progress()


def get_cookie_manager():
    if stx is None:
        return None
    return stx.CookieManager()


def load_data(cookie_manager=None) -> dict:
    if cookie_manager is None:
        return empty_progress()
    try:
        return decode_progress_cookie(cookie_manager.get(COOKIE_NAME))
    except Exception:
        return empty_progress()


def save_data(data: dict) -> None:
    normalized = normalize_progress(data)
    st.session_state.app_data = normalized

    cookie_manager = st.session_state.get("cookie_manager")
    if cookie_manager is None:
        return

    cookie_manager.set(
        COOKIE_NAME,
        encode_progress_cookie(normalized),
        expires_at=datetime.now() + timedelta(days=365),
        same_site="strict",
    )


def load_question_prompts(path: Path = QUESTIONS_FILE) -> dict[str, str]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {str(key): str(value).strip() for key, value in data.items() if str(value).strip()}


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


def apply_prompts(questions: list[dict], prompts: dict[str, str]) -> list[dict]:
    enriched = []
    for question in questions:
        qid = f"{question['q_type']}_{question['number']}"
        enriched.append({**question, "prompt_text": prompts.get(qid, "")})
    return enriched


def to_question(raw: dict) -> Question:
    return Question(
        q_type=raw["q_type"],
        number=int(raw["number"]),
        file_path=Path(raw["file_path"]),
        prompt_text=raw.get("prompt_text", ""),
    )


@st.cache_data(show_spinner=False)
def pdf_page_images(file_path: str, zoom: float = 1.75, max_pages: int = 8) -> tuple[list[bytes], int]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    images: list[bytes] = []
    with fitz.open(file_path) as doc:
        total_pages = len(doc)
        matrix = fitz.Matrix(zoom, zoom)
        for page_index in range(min(total_pages, max_pages)):
            pixmap = doc[page_index].get_pixmap(matrix=matrix, alpha=False)
            images.append(pixmap.tobytes("png"))
    return images, total_pages


def init_session(cookie_manager) -> None:
    st.session_state.setdefault("cookie_manager", cookie_manager)
    if "app_data" not in st.session_state:
        st.session_state.app_data = load_data(cookie_manager)
    st.session_state.setdefault("current_batch", [])
    st.session_state.setdefault("batch_index", 0)
    st.session_state.setdefault("show_answer", False)
    st.session_state.setdefault("last_draw_types", list(QUESTION_TYPES))


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
        pdf_bytes = f.read()

    st.download_button(
        "下载原始 PDF",
        data=pdf_bytes,
        file_name=file_path.name,
        mime="application/pdf",
        use_container_width=True,
    )

    if fitz is None:
        st.error("当前环境没有安装 PyMuPDF，无法把 PDF 渲染为图片。请确认 requirements.txt 中包含 PyMuPDF。")
        return

    try:
        images, total_pages = pdf_page_images(str(file_path))
    except Exception as exc:
        st.error(f"PDF 转图片失败：{exc}")
        return

    if not images:
        st.warning("这个 PDF 没有可显示的页面。")
        return

    if total_pages > len(images):
        st.info(f"该 PDF 共 {total_pages} 页，当前显示前 {len(images)} 页。")

    for index, image in enumerate(images, start=1):
        st.image(image, caption=f"{file_path.name} 第 {index} 页", use_container_width=True)


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
        section[data-testid="stSidebar"] * {
            color: #17212b;
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
            color: #d4d9e2;
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
            font-size: 1.08rem;
            line-height: 1.7;
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

        with st.expander("在线与个人数据说明", expanded=True):
            st.write("当前 `localhost` 是你电脑上的本地预览。部署到 Streamlit Cloud 后，别人才能通过网址访问。")
            st.write("每个人的掌握进度保存在自己浏览器的 Cookie 中，不会写入服务器公共 JSON。")

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
        if st.button("重置本浏览器进度", use_container_width=True):
            save_data(empty_progress())
            reset_batch()
            st.rerun()


def render_empty_state(questions: list[dict], prompt_count: int) -> None:
    if not questions:
        st.error("没有识别到题库 PDF。请确认 `images/简答` 和 `images/问答` 中有 PDF 文件。")
        return

    st.info("在左侧选择题型和数量，然后点击“开始随机抽题”。")

    col1, col2, col3 = st.columns(3)
    col1.metric("复习方式", "随机抽题")
    col2.metric("PDF 显示", "图片预览")
    col3.metric("已录题干", f"{prompt_count} 条")

    if st.button("开始一轮复习", type="primary", use_container_width=True):
        draw_batch(questions, list(QUESTION_TYPES), 10)
        st.rerun()


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

    cookie_manager = get_cookie_manager()
    init_session(cookie_manager)

    prompts = load_question_prompts()
    raw_questions, counts = discover_questions()
    questions = apply_prompts(raw_questions, prompts)

    render_sidebar(questions, counts)

    st.markdown(
        """
        <div class="study-header">
            <h1>895 水力学复习打卡</h1>
            <div class="study-subtitle">随机抽题、按需查看 PDF 图片笔记、每个浏览器单独保存掌握进度。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.current_batch:
        render_question_workspace()
    else:
        render_empty_state(questions, len(prompts))


if __name__ == "__main__":
    main()
