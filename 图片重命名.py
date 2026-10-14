import os
import sys
from datetime import datetime
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

import threading
import tkinter as tk
from tkinter import filedialog, messagebox


class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        self.widget.after(0, self._append, text)

    def _append(self, text):
        self.widget.insert("end", text)
        self.widget.see("end")

    def flush(self):
        pass

def get_photo_date(filepath):
    """优先读取照片EXIF拍摄时间，读取失败则使用文件修改时间"""
    try:
        with Image.open(filepath) as img:
            exif = img.getexif()
            if exif:
                ifd = exif.get_ifd(0x8769)
                value = (ifd.get(36867) or ifd.get(36868)
                         or exif.get(36867) or exif.get(306))
                if value:
                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(filepath))

def rename_photos(directory, prefix="IMG", start_num=1):
    # 支持的图片格式
    image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.bmp', '.tiff'}

    # 获取文件夹内所有图片
    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and os.path.splitext(f)[1].lower() in image_exts
    ]

    if not files:
        print("当前文件夹内未找到图片文件。")
        return

    # 按拍摄时间排序
    files.sort(key=lambda f: get_photo_date(os.path.join(directory, f)))

    # 固定5位编号（00001-99999），超出则自动扩展位数
    total = len(files)
    if total > 99999:
        print("警告：图片数量超过99999张，编号将自动扩展位数！")
    width = max(5, len(str(start_num + total - 1)))

    print(f"共找到 {total} 张图片，开始按时间顺序重命名...")

    # 第一阶段：全部改成唯一临时名，彻底避免新旧名冲突
    temp_files = []
    for i, filename in enumerate(files):
        old_path = os.path.join(directory, filename)
        ext = os.path.splitext(filename)[1].lower()
        temp_path = os.path.join(directory, f".__tmp_rename_{i}__.tmp")
        while os.path.exists(temp_path):
            temp_path = os.path.join(directory, f".__tmp_rename_{i}_{os.getpid()}__.tmp")
        os.rename(old_path, temp_path)
        temp_files.append((temp_path, ext, filename))

    # 第二阶段：临时名 -> 最终编号名
    for index, (temp_path, ext, filename) in enumerate(temp_files, start=start_num):
        new_name = f"{prefix}_{str(index).zfill(width)}{ext}"
        new_path = os.path.join(directory, new_name)
        os.rename(temp_path, new_path)
        
        print(f"[{index:0>{width}}] {filename} -> {new_name}")

    print("重命名完成！")

def run_gui(initial_dir=""):
    root = tk.Tk()
    root.title("图片批量重命名")
    root.geometry("620x460")

    folder_var = tk.StringVar(value=initial_dir if os.path.isdir(initial_dir) else "")
    prefix_var = tk.StringVar(value="IMG")

    top = tk.Frame(root)
    top.pack(fill="x", padx=10, pady=(10, 4))
    tk.Label(top, text="文件夹：").pack(side="left")
    tk.Entry(top, textvariable=folder_var).pack(side="left", fill="x", expand=True, padx=6)
    tk.Button(top, text="选择文件夹", command=lambda: folder_var.set(filedialog.askdirectory() or folder_var.get())).pack(side="left")

    mid = tk.Frame(root)
    mid.pack(fill="x", padx=10, pady=4)
    tk.Label(mid, text="前缀：").pack(side="left")
    tk.Entry(mid, textvariable=prefix_var, width=12).pack(side="left", padx=(0, 10))
    start_btn = tk.Button(mid, text="开始重命名")
    start_btn.pack(side="left")

    box = tk.Frame(root)
    box.pack(fill="both", expand=True, padx=10, pady=(4, 10))
    sb = tk.Scrollbar(box)
    sb.pack(side="right", fill="y")
    log = tk.Text(box, wrap="word", yscrollcommand=sb.set)
    log.pack(side="left", fill="both", expand=True)
    sb.config(command=log.yview)

    def start_rename():
        folder = folder_var.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning("提示", "请先选择一个有效的文件夹")
            return
        prefix = prefix_var.get().strip() or "IMG"
        log.delete("1.0", "end")
        start_btn.config(state="disabled")

        def worker():
            sys.stdout = TextRedirector(log)
            try:
                rename_photos(folder, prefix=prefix)
            except Exception as e:
                print(f"发生错误：{e}")
            finally:
                sys.stdout = sys.__stdout__
                start_btn.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    start_btn.config(command=start_rename)
    root.mainloop()


if __name__ == "__main__":
    run_gui(sys.argv[1] if len(sys.argv) > 1 else "")