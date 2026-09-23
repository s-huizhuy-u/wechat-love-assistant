"""
微信恋爱军师 - 文字分析版
直接复制聊天记录文字，自动分析
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time


class ChatAnalyzerApp:
    """聊天记录分析器"""

    def __init__(self, root):
        self.root = root
        self.root.title("💕 恋爱军师 - 文字分析")
        self.root.geometry("600x650")
        self.root.resizable(True, True)
        
        self.last_clipboard = ""
        self.auto_detect = False
        
        self.setup_ui()
        self.center_window()
        
        # 启动剪贴板监控
        self.start_clipboard_monitor()

    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def setup_ui(self):
        """设置界面"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 设置样式
        style = ttk.Style()
        style.configure("LargeButton.TButton", 
                       font=("Microsoft YaHei", 12, "bold"),
                       padding=15)
        style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"))
        style.configure("Info.TLabel", font=("Microsoft YaHei", 10), foreground="gray")

        # 标题
        title_label = ttk.Label(main_frame, text="💕 恋爱军师 - 文字分析", style="Title.TLabel")
        title_label.pack(pady=(0, 5))

        # 说明
        info_label = ttk.Label(
            main_frame, 
            text="1. 在微信复制聊天记录 → 2. 粘贴到下方 → 3. 点击分析",
            style="Info.TLabel"
        )
        info_label.pack(pady=(0, 10))

        # 自动检测开关
        auto_frame = ttk.Frame(main_frame)
        auto_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            auto_frame, 
            text="🔄 自动检测剪贴板（复制后自动分析）",
            variable=self.auto_var,
            command=self.toggle_auto_detect
        ).pack(side=tk.LEFT)
        
        ttk.Label(auto_frame, text="间隔：3 秒", font=("Microsoft YaHei", 9), foreground="gray").pack(side=tk.LEFT, padx=5)

        # 聊天记录输入
        chat_frame = ttk.LabelFrame(main_frame, text="聊天记录", padding="10")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.chat_text = scrolledtext.ScrolledText(chat_frame, height=12, font=("Microsoft YaHei", 10))
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.insert(tk.END, "在此粘贴微信聊天记录...\n\n示例格式：\n她：今天好累啊\n我：辛苦了，早点休息\n她：嗯嗯")

        # 补充背景
        context_frame = ttk.LabelFrame(main_frame, text="补充背景 (可选)", padding="10")
        context_frame.pack(fill=tk.X, pady=(0, 10))

        self.context_text = scrolledtext.ScrolledText(context_frame, height=3)
        self.context_text.pack(fill=tk.X)
        self.context_text.insert(tk.END, "例如：我们认识两个月了，她是 INTJ 类型，最近她回复消息变慢了...")

        # 分析按钮
        self.analyze_btn = ttk.Button(
            main_frame, 
            text="🔍 开始分析",
            style="LargeButton.TButton",
            command=self.start_analysis
        )
        self.analyze_btn.pack(pady=(0, 10))

        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="分析结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, 
                                                     state=tk.DISABLED,
                                                     font=("Microsoft YaHei", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="📋 复制提示", 
                  command=self.copy_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="🗑️ 清空", 
                  command=self.clear_result).pack(side=tk.RIGHT, padx=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 粘贴聊天记录后点击分析")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

    def toggle_auto_detect(self):
        """切换自动检测"""
        self.auto_detect = self.auto_var.get()
        if self.auto_detect:
            self.status_var.set("自动检测已开启 - 复制聊天记录后将自动分析")
        else:
            self.status_var.set("自动检测已关闭")

    def start_clipboard_monitor(self):
        """启动剪贴板监控线程"""
        def monitor():
            while True:
                if self.auto_detect:
                    try:
                        clipboard = self.root.clipboard_get()
                        if clipboard and clipboard != self.last_clipboard and len(clipboard) > 10:
                            # 检查是否已经是聊天记录格式
                            if '：' in clipboard or ':' in clipboard:
                                self.last_clipboard = clipboard
                                self.root.after(0, self.auto_analyze, clipboard)
                    except:
                        pass
                time.sleep(3)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def auto_analyze(self, clipboard_text):
        """自动分析剪贴板内容"""
        # 清空并粘贴
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.insert(tk.END, clipboard_text)
        
        # 显示提示
        self.status_var.set("检测到聊天记录，正在分析...")
        
        # 延迟 1 秒后自动分析
        self.root.after(1000, self.start_analysis)

    def start_analysis(self):
        """开始分析"""
        chat_text = self.chat_text.get("1.0", tk.END).strip()
        context = self.context_text.get("1.0", tk.END).strip()
        
        if not chat_text or chat_text == "在此粘贴微信聊天记录...\n\n示例格式：\n她：今天好累啊\n我：辛苦了，早点休息\n她：嗯嗯":
            messagebox.showwarning("提示", "请先粘贴聊天记录！")
            return
        
        # 生成提示
        prompt = self.generate_prompt(chat_text, context)
        
        # 显示结果
        result = f"""✅ 分析提示已生成

📋 下一步操作：

1️⃣ 点击"复制提示"按钮
2️⃣ 切换到 DSH 对话窗口
3️⃣ 粘贴 (Ctrl+V)
4️⃣ 发送

💡 DSH 会调用"狗头军师"分析聊天记录

📝 聊天记录长度：{len(chat_text)} 字符
"""
        
        self.display_result(result)
        self.status_var.set(f"完成！已生成分析提示")
        
        # 保存提示
        self.current_prompt = prompt

    def generate_prompt(self, chat_text, context):
        """生成分析提示"""
        prompt = f"""请分析以下微信聊天记录，使用"狗头军师"的分析框架给出建议。

【聊天记录】
{chat_text}

【用户补充背景】
{context or "无"}

【分析框架】
1. 情绪分析：理解双方感受
2. 事实梳理：已知、推测、未知
3. 建议回复：可直接复制的回复
4. 发送策略：时机和应对
5. 行动建议：下一步怎么做

请给出详细分析。"""
        
        return prompt

    def display_result(self, result):
        """显示结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.config(state=tk.DISABLED)

    def copy_prompt(self):
        """复制提示到剪贴板"""
        if hasattr(self, 'current_prompt'):
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_prompt)
            self.status_var.set("已复制到剪贴板!")
            messagebox.showinfo("提示", "提示已复制!\n\n请切换到 DSH 对话窗口粘贴")
        else:
            messagebox.showinfo("提示", "请先分析！")

    def clear_result(self):
        """清空结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.chat_text.delete("1.0", tk.END)
        self.context_text.delete("1.0", tk.END)
        self.status_var.set("已清空")


def main():
    """主函数"""
    root = tk.Tk()
    app = ChatAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
