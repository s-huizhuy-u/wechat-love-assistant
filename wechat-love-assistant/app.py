"""
微信恋爱军师 - 文字分析版 v2（零依赖：仅标准库 + tkinter）

优化点：
1. 自动解析微信/QQ 导出格式（两种常见排版），提取说话人
2. 强制「说话人映射」由用户确认后才生成分析提示（对齐狗头军师证据边界）
3. 分析后自动复制提示，一键即可切到 DSH 粘贴
4. 长期保存补充背景与已确认映射（data/profile.json）
5. 历史记录可回看、重载、删除（data/history.json，自动限量）
6. 两种模式：完整分析 / 只要一句可发的话术
7. Ctrl+Enter 快速分析；剪贴板监控在主线程轮询，避免线程崩溃
"""
import json
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
from pathlib import Path

try:
    import ctypes
except ImportError:  # 非 Windows 平台
    ctypes = None

# ============================ 路径与常量 ============================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
try:
    DATA_DIR.mkdir(exist_ok=True)
except OSError:
    DATA_DIR = BASE_DIR

PROFILE_FILE = DATA_DIR / "profile.json"
HISTORY_FILE = DATA_DIR / "history.json"
MAX_HISTORY = 30

SAMPLE_TEXT = """她：今天加班好累啊
我：辛苦了，早点休息
她：嗯嗯
我：明天周末了，要不要出来走走？"""

SURVEY_TEXT = """【首次使用·档案】
我：MBTI / 主观综合评分0-100 / 主要优势和短板
对象A：代号 / MBTI / 主观综合评分0-100 / 当前关系
对象B（如有）：同上
经过：认识方式、发展多久、最近三件关键事件、联系和双方投入
目标：推进、确认、修复、比较选择，还是退出
情绪：最难受的点、强度0-10；眼下有没有必须马上回的话
（不知道可留空，也可以直接讲故事）"""


def enable_dpi_awareness():
    """避免高分屏下界面模糊"""
    if ctypes is None:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ============================ 聊天记录解析 ============================

# 格式一：昵称在前，时间在后（微信导出常见）
HEADER_NAME_FIRST = re.compile(
    r'^(?P<name>.{1,24}?)\s+'
    r'(?P<ts>\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s*$'
)
# 格式二：时间在前，昵称在后（QQ 导出常见，昵称可能带 (123456)）
HEADER_TS_FIRST = re.compile(
    r'^(?P<ts>\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+'
    r'(?P<name>.{1,24}?)\s*$'
)
# 格式三：单行 “昵称：内容”
INLINE = re.compile(r'^(?P<name>[^:：]{1,24}?)\s*[:：]\s*(?P<content>.*)$')
# 行首时间戳 / 中括号标记，如 “[2024-05-01 20:30] ” 或 “20:30 ”
LEADING_TS = re.compile(
    r'^\s*[\[\(]?\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+)?'
    r'\d{1,2}:\d{2}(?::\d{2})?\s*[\]\)]?\s*'
)
# 昵称尾部账号，如 “张三(123456)”“李四<lisi@qq.com>”“王五（wxid_abc）”
TAIL_ACCOUNT = re.compile(r'(?:[\(（][^\)）]*[\)）]|<[^>]*>)\s*$')


def _clean_name(name):
    """清洗昵称：去空白与尾部账号"""
    name = (name or "").strip()
    name = TAIL_ACCOUNT.sub("", name).strip()
    return name


def _scan_lines(raw):
    """逐行扫描，返回 [(kind, name, content)]，kind 为 'new' 或 'cont'"""
    items = []
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s:
            continue

        m = HEADER_NAME_FIRST.match(s) or HEADER_TS_FIRST.match(s)
        if m:
            items.append(("new", _clean_name(m.group("name")), ""))
            continue

        body = LEADING_TS.sub("", s)
        m = INLINE.match(body)
        if m and m.group("name").strip():
            items.append(("new", _clean_name(m.group("name")),
                          m.group("content").strip()))
            continue

        items.append(("cont", None, body))
    return items


def parse_chat(raw):
    """
    解析聊天记录。
    返回 (messages, speakers)
      messages: [{'speaker': str|None, 'text': str}]
      speakers: 按首次出现排序的真实说话人列表
    只有反复出现（>=2 次）的昵称才认定为说话人，降低“他说：…”这类误判。
    """
    items = _scan_lines(raw)

    counts = {}
    for kind, name, _ in items:
        if kind == "new" and name:
            counts[name] = counts.get(name, 0) + 1

    frequent = {n for n, c in counts.items() if c >= 2}
    accepted = frequent if len(frequent) >= 2 else set(counts)
    speakers = [n for n in counts if n in accepted]

    messages = []
    current = None
    for kind, name, content in items:
        if kind == "new" and name in accepted:
            current = {"speaker": name, "text": content}
            messages.append(current)
            continue

        # 未被认定为说话人的行，按原文回填，避免内容丢失
        text = (f"{name}：{content}" if content else name) if kind == "new" else content
        if not text:
            continue
        if current is None:
            current = {"speaker": None, "text": text}
            messages.append(current)
        else:
            current["text"] = (current["text"] + "\n" + text).strip()

    messages = [m for m in messages if m.get("text")]
    return messages, speakers


def render_transcript(messages, me=None, other=None):
    """按已确认映射改写称谓，输出统一格式的记录"""
    lines = []
    for m in messages:
        sp = m.get("speaker")
        if sp is None:
            label = "（未标注）"
        elif me and sp == me:
            label = "我"
        elif other and sp == other:
            label = "对方"
        else:
            label = sp
        body = m["text"].replace("\n", "\n    ")
        lines.append(f"{label}：{body}")
    return "\n".join(lines)


def count_by_speaker(messages, me=None, other=None):
    """统计双方消息条数（客观投入信号，供互惠判断参考）"""
    stat = {}
    for m in messages:
        sp = m.get("speaker")
        if sp is None:
            key = "未标注"
        elif me and sp == me:
            key = "我"
        elif other and sp == other:
            key = "对方"
        else:
            key = sp
        stat[key] = stat.get(key, 0) + 1
    return stat


# ============================ 提示词构造 ============================

def build_prompt(messages, context, me, other, mode,
                 mapping_confirmed, stats, total):
    """
    生成发给 DSH 的分析提示。
    注意：记录由本函数内部渲染，未确认映射时一律输出原始昵称，
    绝不预先替换成「我／对方」——避免把猜测当事实。
    """
    if mode == "quick":
        head = ("请用「狗头军师」的方式处理下面的微信聊天记录："
                "第一屏先给我一条可以直接复制发送的回复。")
    else:
        head = "请用「狗头军师」的分析框架分析下面的微信聊天记录。"

    if mapping_confirmed and me and other:
        transcript = render_transcript(messages, me, other)
    else:
        transcript = render_transcript(messages)

    lines = [head, ""]

    if mapping_confirmed and me and other:
        lines.append("【说话人映射（用户已确认，请沿用，不要按语气或左右翻转）】")
        lines.append(f"- 我 = {me}")
        lines.append(f"- 分析对象 = {other}")
        lines.append("")
    else:
        lines.append("【说话人映射（未确认）】")
        lines.append("下方记录保留原始昵称。请先用一个最小问题向我确认"
                     "哪个昵称是我本人；确认前不要解释关系。")
        lines.append("")

    lines.append("【聊天记录】")
    lines.append(transcript)
    lines.append("")

    if total:
        detail = "、".join(f"{k} {v} 条" for k, v in stats.items())
        lines.append("【客观计数（仅原始条数，非结论）】")
        lines.append(f"共 {total} 条；{detail}")
        lines.append("")

    lines.append("【补充背景】")
    lines.append(context.strip() or "无")
    lines.append("")

    if mode == "quick":
        lines.append("【输出要求】")
        lines.append("1. 先给一条可直接发送的成品，单独成段方便复制")
        lines.append("2. 再说发送时机与主要代价")
        lines.append("3. 给出对方积极 / 含糊 / 不回应三种后续，分别怎么接")
        lines.append("4. 每条消息只承载一个主动作，不要堆叠多个意图")
        lines.append("5. 不要读心，只依据记录里可见的文字、顺序和间隔")
    else:
        lines.append("【输出要求】")
        lines.append("1. 情绪落地：2-4 句指出感受、触发点与冲突")
        lines.append("2. 事实拆分：已知 / 合理推测 / 关键未知，三者分开列")
        lines.append("3. 利益判断：互惠、可靠、投入、边界与机会成本")
        lines.append("4. 明确建议：先给一句首选 + 2-4 条理由；"
                     "有真实权衡时再给不超过三个版本（稳健 / 会撩 / 强势）")
        lines.append("5. 行动收束：现在能做的一个小动作、观察窗口、停止条件")
        lines.append("6. 最后只追问 1-3 个真正影响决策的问题")
        lines.append("7. 不要读心，只依据记录里可见的文字、顺序和间隔；"
                     "缺失信息保持未知，不要为了完整而虚构")

    return "\n".join(lines)


# ============================ 主应用 ============================

class ChatAnalyzerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("💕 恋爱军师 - 文字分析")
        self.root.geometry("680x860")
        self.root.minsize(580, 640)

        self.current_prompt = ""
        self.last_clipboard = ""
        self.auto_detect = False
        self._parse_job = None
        self._speakers = []
        self._messages = []

        self.setup_ui()
        self.center_window()
        self.load_profile()

        self.root.bind("<Control-Return>", lambda e: self.start_analysis())
        self.root.after(1500, self._poll_clipboard)

    # ---------- 基础 ----------

    def center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2) - 20
        self.root.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Big.TButton", font=("Microsoft YaHei", 12, "bold"), padding=12)
        style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"))
        style.configure("Info.TLabel", font=("Microsoft YaHei", 9), foreground="#666")
        style.configure("Warn.TLabel", font=("Microsoft YaHei", 9), foreground="#C62828")
        style.configure("Ok.TLabel", font=("Microsoft YaHei", 9), foreground="#2E7D32")
        style.configure("TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"))

        main = ttk.Frame(self.root, padding="12")
        main.pack(fill=tk.BOTH, expand=True)

        # —— 标题 ——
        ttk.Label(main, text="💕 恋爱军师", style="Title.TLabel").pack()
        ttk.Label(
            main,
            text="复制微信聊天 → 粘贴 → Ctrl+Enter → 提示自动复制 → 到 DSH 粘贴发送",
            style="Info.TLabel",
        ).pack(pady=(2, 8))

        # —— 选项行 ——
        opt = ttk.Frame(main)
        opt.pack(fill=tk.X, pady=(0, 6))

        self.mode_var = tk.StringVar(value="full")
        ttk.Radiobutton(opt, text="完整分析", value="full",
                        variable=self.mode_var).pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text="只要一句回复", value="quick",
                        variable=self.mode_var).pack(side=tk.LEFT, padx=(6, 12))

        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="自动检测剪贴板", variable=self.auto_var,
                        command=self.toggle_auto).pack(side=tk.LEFT)
        self.min_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="复制后最小化", variable=self.min_var).pack(side=tk.LEFT, padx=6)

        # —— 聊天记录 ——
        chat_box = ttk.LabelFrame(main, text="聊天记录", padding=8)
        chat_box.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.input_text = scrolledtext.ScrolledText(
            chat_box, height=10, font=("Microsoft YaHei", 10), wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        self.input_text.bind("<<Modified>>", self.on_input_modified)

        tools = ttk.Frame(chat_box)
        tools.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(tools, text="示例", width=6,
                   command=lambda: self._fill(SAMPLE_TEXT)).pack(side=tk.LEFT)
        ttk.Button(tools, text="首用档案", width=9,
                   command=lambda: self._fill(SURVEY_TEXT)).pack(side=tk.LEFT, padx=4)
        ttk.Button(tools, text="清空记录", width=9,
                   command=self.clear_input).pack(side=tk.LEFT)
        self.parse_info = ttk.Label(tools, text="", style="Info.TLabel")
        self.parse_info.pack(side=tk.RIGHT)

        # —— 说话人映射 ——
        map_box = ttk.LabelFrame(main, text="说话人映射（必须确认，避免误判关系）", padding=8)
        map_box.pack(fill=tk.X, pady=(0, 6))

        row = ttk.Frame(map_box)
        row.pack(fill=tk.X)
        ttk.Label(row, text="我是：").pack(side=tk.LEFT)
        self.me_box = ttk.Combobox(row, width=14, values=[])
        self.me_box.pack(side=tk.LEFT, padx=(2, 10))
        ttk.Label(row, text="对象是：").pack(side=tk.LEFT)
        self.other_box = ttk.Combobox(row, width=14, values=[])
        self.other_box.pack(side=tk.LEFT, padx=(2, 10))

        self.confirm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="我已确认以上映射", variable=self.confirm_var,
                        command=self.refresh_map_state).pack(side=tk.LEFT)

        self.map_state = ttk.Label(map_box, text="", style="Warn.TLabel")
        self.map_state.pack(fill=tk.X, pady=(4, 0))

        self.me_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_map_state())
        self.other_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_map_state())

        # —— 补充背景 ——
        ctx_box = ttk.LabelFrame(main, text="补充背景（自动保存，不用每次重打）", padding=8)
        ctx_box.pack(fill=tk.X, pady=(0, 6))
        self.context_text = scrolledtext.ScrolledText(
            ctx_box, height=3, font=("Microsoft YaHei", 10), wrap=tk.WORD)
        self.context_text.pack(fill=tk.X)

        # —— 主按钮 ——
        act = ttk.Frame(main)
        act.pack(fill=tk.X, pady=(0, 6))
        self.analyze_btn = ttk.Button(act, text="🔍 生成提示并复制（Ctrl+Enter）",
                                      style="Big.TButton", command=self.start_analysis)
        self.analyze_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(act, text="💾 存为文件", width=11,
                   command=self.save_file).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(act, text="📚 历史", width=8,
                   command=self.open_history).pack(side=tk.LEFT, padx=(6, 0))

        # —— 预览 ——
        prev_box = ttk.LabelFrame(main, text="提示预览（内容已复制到剪贴板）", padding=8)
        prev_box.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.preview = scrolledtext.ScrolledText(
            prev_box, height=8, font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
        self.preview.pack(fill=tk.BOTH, expand=True)

        # —— 状态栏 ——
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=4).pack(fill=tk.X)

    # ---------- 输入与解析 ----------

    def _fill(self, text):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert(tk.END, text)

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)

    def on_input_modified(self, _event=None):
        try:
            if not self.input_text.edit_modified():
                return
            self.input_text.edit_modified(False)
        except tk.TclError:
            return
        if self._parse_job:
            self.root.after_cancel(self._parse_job)
        self._parse_job = self.root.after(400, self.do_parse)

    def do_parse(self):
        raw = self.input_text.get("1.0", tk.END).strip()
        self._messages, self._speakers = parse_chat(raw)

        self.me_box["values"] = self._speakers
        self.other_box["values"] = self._speakers

        if not self._speakers:
            self.parse_info.config(text="未识别到昵称（可直接手输）")
        else:
            self.parse_info.config(
                text=f"识别到 {len(self._speakers)} 位：{'、'.join(self._speakers[:4])}"
                     f"{'…' if len(self._speakers) > 4 else ''} / 共 {len(self._messages)} 条")

        # 昵称变化后，旧确认作废
        if self.confirm_var.get():
            me, other = self.me_box.get().strip(), self.other_box.get().strip()
            if me not in self._speakers and other not in self._speakers:
                self.confirm_var.set(False)
        self.refresh_map_state()

    def refresh_map_state(self):
        me = self.me_box.get().strip()
        other = self.other_box.get().strip()

        if me and other and me == other:
            self.map_state.config(text="⚠️ 「我」和「对象」不能是同一个人", style="Warn.TLabel")
        elif self.confirm_var.get() and me and other:
            self.map_state.config(text=f"✅ 已确认：我 = {me}；对象 = {other}", style="Ok.TLabel")
        elif me and other:
            self.map_state.config(text="⚠️ 请勾选「我已确认以上映射」后再分析", style="Warn.TLabel")
        else:
            self.map_state.config(text="ℹ️ 请选择（或手动输入）两个昵称，并勾选确认", style="Info.TLabel")

    def toggle_auto(self):
        self.auto_detect = self.auto_var.get()
        self.status_var.set("自动检测已开启：复制聊天记录后自动生成提示"
                            if self.auto_detect else "自动检测已关闭")

    def _poll_clipboard(self):
        """主线程轮询剪贴板，避免子线程操作 tkinter 导致崩溃"""
        try:
            if self.auto_detect:
                text = self.root.clipboard_get()
                if (text and text != self.last_clipboard
                        and len(text) > 12 and ("：" in text or ":" in text)):
                    self.last_clipboard = text
                    self._fill(text)
                    self.status_var.set("检测到剪贴板内容，正在生成提示…")
                    self.root.after(600, self.start_analysis)
        except tk.TclError:
            pass
        except Exception:
            pass
        finally:
            self.root.after(1500, self._poll_clipboard)

    # ---------- 分析 ----------

    def start_analysis(self):
        raw = self.input_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("还没有内容", "请先粘贴或复制一段聊天记录。")
            return

        self.do_parse()
        me = self.me_box.get().strip()
        other = self.other_box.get().strip()

        if me and other and me == other:
            messagebox.showwarning("映射有误", "「我」和「对象」不能是同一个人。")
            return

        confirmed = bool(self.confirm_var.get() and me and other)

        if self._speakers and not confirmed:
            ok = messagebox.askyesno(
                "建议先确认说话人映射",
                "还没确认哪个昵称是你本人。\n\n"
                "不确认的话，军师会先反问你，可能要多一轮对话。\n\n"
                "仍然直接生成提示吗？")
            if not ok:
                return

        # 解析失败时用原文兜底，保证内容不丢
        messages = self._messages or [{"speaker": None, "text": raw}]

        stats = count_by_speaker(messages, me if confirmed else None,
                                 other if confirmed else None)

        context = self.context_text.get("1.0", tk.END).strip()
        prompt = build_prompt(messages, context, me, other,
                              self.mode_var.get(), confirmed, stats,
                              len(messages))

        self.current_prompt = prompt
        self.set_preview(prompt)

        # 自动复制
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            self.root.update_idletasks()
        except tk.TclError:
            pass

        self.analyze_btn.config(text="✅ 已复制，去 DSH 粘贴")
        self.root.after(2200, lambda: self.analyze_btn.config(
            text="🔍 生成提示并复制（Ctrl+Enter）"))

        self.status_var.set(
            f"完成：{len(messages)} 条记录 → 提示已复制到剪贴板"
            + ("（映射已确认）" if confirmed else "（映射未确认）"))

        self.save_profile(context, me, other)
        self.append_history(raw, context, prompt, confirmed, len(messages))

        if self.min_var.get():
            self.root.iconify()

    def set_preview(self, text):
        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, text)
        self.preview.config(state=tk.DISABLED)

    def save_file(self):
        if not self.current_prompt:
            messagebox.showinfo("提示", "请先生成提示。")
            return
        path = filedialog.asksaveasfilename(
            title="保存分析提示",
            defaultextension=".txt",
            initialfile=f"prompt_{datetime.now():%Y%m%d_%H%M%S}.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            Path(path).write_text(self.current_prompt, encoding="utf-8")
            self.status_var.set(f"已保存：{path}")
        except OSError as e:
            messagebox.showerror("保存失败", str(e))

    # ---------- 档案与历史 ----------

    def save_profile(self, context, me, other):
        data = {"context": context, "me": me, "other": other,
                "saved_at": datetime.now().isoformat(timespec="seconds")}
        try:
            PROFILE_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def load_profile(self):
        if not PROFILE_FILE.exists():
            return
        try:
            data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return

        ctx = (data.get("context") or "").strip()
        if ctx:
            self.context_text.insert(tk.END, ctx)

        # 沿用上次确认过的映射（这是用户自己确认过的，不是猜测）
        me, other = (data.get("me") or "").strip(), (data.get("other") or "").strip()
        if me or other:
            self.me_box.set(me)
            self.other_box.set(other)
            if me and other:
                self.confirm_var.set(True)
                self.map_state.config(
                    text=f"✅ 沿用上次确认：我 = {me}；对象 = {other}", style="Ok.TLabel")

        if ctx or me:
            self.status_var.set("已载入上次的补充背景与说话人映射")

    def read_history(self):
        if not HISTORY_FILE.exists():
            return []
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def append_history(self, raw, context, prompt, confirmed, count):
        items = self.read_history()
        items.insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": self.mode_var.get(),
            "confirmed": bool(confirmed),
            "count": count,
            "raw": raw[:4000],
            "context": context,
            "prompt": prompt,
        })
        del items[MAX_HISTORY:]
        try:
            HISTORY_FILE.write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def open_history(self):
        items = self.read_history()
        if not items:
            messagebox.showinfo("历史记录", "还没有历史记录。")
            return

        win = tk.Toplevel(self.root)
        win.title("历史记录")
        win.geometry("620x420")
        win.transient(self.root)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        cols = ("time", "mode", "count", "map")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        for cid, text, width in (("time", "时间", 150), ("mode", "模式", 90),
                                 ("count", "条数", 60), ("map", "映射", 70)):
            tree.heading(cid, text=text)
            tree.column(cid, width=width, anchor=tk.CENTER)
        tree.pack(fill=tk.BOTH, expand=True)

        for idx, it in enumerate(items):
            tree.insert("", tk.END, iid=str(idx), values=(
                it.get("time", ""),
                "只要话术" if it.get("mode") == "quick" else "完整分析",
                it.get("count", 0),
                "已确认" if it.get("confirmed") else "未确认",
            ))

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, pady=(8, 0))

        def selected():
            sel = tree.selection()
            return items[int(sel[0])] if sel else None

        def reload_item():
            it = selected()
            if not it:
                return
            self._fill(it.get("raw", ""))
            self.context_text.delete("1.0", tk.END)
            self.context_text.insert(tk.END, it.get("context", ""))
            self.mode_var.set(it.get("mode", "full"))
            self.set_preview(it.get("prompt", ""))
            self.current_prompt = it.get("prompt", "")
            self.status_var.set(f"已载入 {it.get('time', '')} 的记录")
            win.destroy()

        def copy_item():
            it = selected()
            if not it:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(it.get("prompt", ""))
            self.status_var.set("历史提示已复制到剪贴板")

        ttk.Button(btns, text="载入这条", command=reload_item).pack(side=tk.LEFT)
        ttk.Button(btns, text="复制提示", command=copy_item).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="关闭", command=win.destroy).pack(side=tk.RIGHT)


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    ChatAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
