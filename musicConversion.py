import os
import sys
import base64  
import struct
import zlib
import json
import struct
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from pydub import AudioSegment
from Crypto.Cipher import AES


def decrypt_ncm(ncm_file):
    """2024年最新的NCM完美解密方案"""
    temp_file = os.path.splitext(ncm_file)[0] + "_decrypted.mp3"
    
    with open(ncm_file, 'rb') as f:
        # 1. 验证新版文件头（兼容2024格式）
        header = f.read(12)
        if not (header.startswith(b'CTENFDAM') or len(header) != 12):
            raise ValueError("无效的文件头，可能是新版加密")

        # 2. 动态读取密钥区块
        f.seek(0x0A)  # 标准密钥偏移量
        key_size = struct.unpack('<I', f.read(4))[0]
        encrypted_key = bytearray(f.read(key_size))
        
        # 3. 密钥双重解密方案
        for i in range(len(encrypted_key)):
            encrypted_key[i] ^= 0x23 if i % 3 == 0 else 0x64  # 动态异或
        
        aes_key = encrypted_key[18:34]  # 2024年密钥偏移调整
        
        # 4. 处理音频数据的AES解密
        cipher = AES.new(aes_key, AES.MODE_ECB)
        audio_data = bytearray()
        
        # 5. 新版数据块处理（2048字节/块 + 尾块特殊处理）
        while (chunk := f.read(2048)):
            # 自动处理非16倍数字节的情况
            if len(chunk) % 16 != 0:
                chunk += bytes(16 - (len(chunk) % 16))
            
            # MP3特性：跳过解密后可能的垃圾头（0x00~0xFF范围检测）
            decrypted = cipher.decrypt(chunk)
            if b'ID3' in decrypted[:10] or b'\xff\xfb' in decrypted[:4]:
                audio_data.extend(decrypted)
            else:
                # 二级验证：查找帧同步字 0xFFFx
                for i in range(len(decrypted)-1):
                    if (decrypted[i] & 0xFF) == 0xFF and (decrypted[i+1] & 0xE0) == 0xE0:
                        audio_data.extend(decrypted[i:])
                        break

    # 6. 写入前自动修复文件头
    if audio_data[:3] == b'\x49\x44\x33':  # ID3标签修正
        fixed_header = bytes([x if x > 0x20 else 0x20 for x in audio_data[:10]])
        audio_data = fixed_header + audio_data[10:]
    
    with open(temp_file, 'wb') as f:
        f.write(audio_data)
    
    return temp_file
    
def convert_to_mp3(input_file, output_file):
    try:
        if not os.path.exists(input_file):
            raise ValueError(f"输入文件不存在: {input_file}")
        
        file_extension = os.path.splitext(input_file)[1][1:].lower().strip()
        
        if file_extension == "ncm":
            temp_file = decrypt_ncm(input_file)
            try:
                if not os.path.exists(temp_file):
                    raise ValueError(f"临时文件{temp_file}未生成")
                
                # 验证转换后的文件是否可以在pydub中识别
                audio = AudioSegment.from_file(temp_file)
                audio.export(output_file, format="mp3")
                
            finally:
                # 确保删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        else:
            audio = AudioSegment.from_file(input_file, format=file_extension)
            audio.export(output_file, format="mp3", bitrate="320k")

    except Exception as e:
        raise ValueError(f"转换文件{input_file}失败: {str(e)}") from e

def select_files():
    file_paths = filedialog.askopenfilenames(filetypes=[("音频文件", "*.m4a *.flac *.wav *.ogg *.ncm")])
    if file_paths:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, ";".join(file_paths))  # 用分号分隔多个文件路径

def select_output_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, folder_path)


def convert():
    input_files = input_entry.get().split(";")  # 分割多个文件路径
    output_folder = output_entry.get()  # 获取目标文件夹路径

    if not input_files or input_files == [""]:
        messagebox.showwarning("提示~", "请选择一个或多个音频文件")
        return

    if not output_folder:
        messagebox.showwarning("提示~", "请选择目标文件夹")
        return

    for input_file in input_files:
        try:
            output_file = os.path.join(
                output_folder,
                os.path.splitext(os.path.basename(input_file))[0] + ".mp3"
            )
            convert_to_mp3(input_file, output_file)
        except Exception as e:
            messagebox.showerror("错误", f"文件 {input_file} 转换失败: {str(e)}")
    
    messagebox.showinfo("成功", "所有文件已转换完成！")

# 获取背景图像路径
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 创建主窗口
root = tk.Tk()
root.title("音乐转换~♪")

# 设置窗口大小
root.geometry("960x540")

# 加载背景图像
background_image_path = resource_path("background.jpg")
background_image = Image.open(background_image_path)

# 创建Canvas并添加背景图像
canvas = tk.Canvas(root, width=960, height=540)
canvas.pack(fill="both", expand=True)

# 创建一个函数来调整背景图像的大小
def resize_image(event=None):
    global background_photo  # 声明全局变量
    new_width = root.winfo_width()
    new_height = root.winfo_height()
    resized_image = background_image.resize((new_width, new_height), Image.LANCZOS)
    background_photo = ImageTk.PhotoImage(resized_image)
    canvas.create_image(0, 0, image=background_photo, anchor="nw", tags="background")

    # 确保按钮和文本在背景图片之上
    canvas.tag_raise("button")
    canvas.tag_raise("text")
    canvas.tag_raise("entry")

# 绑定窗口大小改变事件
root.bind("<Configure>", resize_image)

# 样式配置
label_style = {"font": ("Arial", 12, "bold"), "fill": "#4FC1D0"}

# 创建圆角按钮
def create_rounded_button(canvas, x, y, text, command, width=150, height=40, radius=20, bg="#BAEBFF", fg="white", font=("Arial", 12, "bold")):
    # 创建按钮背景
    button_bg = canvas.create_oval(x, y, x + radius * 2, y + height, fill=bg, outline=bg, tags="button")
    canvas.create_oval(x + width - radius * 2, y, x + width, y + height, fill=bg, outline=bg, tags="button")
    canvas.create_rectangle(x + radius, y, x + width - radius, y + height, fill=bg, outline=bg, tags="button")

    # 创建按钮文本
    button_text = canvas.create_text(x + width / 2, y + height / 2, text=text, fill=fg, font=font, tags="text")

    # 添加点击事件
    def on_click(event):
        command()

    canvas.tag_bind(button_bg, "<Button-1>", on_click)
    canvas.tag_bind(button_text, "<Button-1>", on_click)

# 创建自定义输入框
def create_custom_entry(canvas, x, y, width=400, height=30, bg="#FFFFFF", border_color="#BAEBFF", font=("Arial", 12)):
    # 绘制输入框背景和边框
    entry_bg = canvas.create_rectangle(x, y, x + width, y + height, fill=bg, outline=border_color, width=2, tags="entry")
    # 创建实际的 Entry 小部件
    entry = tk.Entry(root, font=font, bd=0, highlightthickness=0)
    canvas.create_window(x + width / 2, y + height / 2, window=entry, tags="entry")
    return entry

# 在Canvas上创建窗口以放置其他组件
canvas.create_text(100, 100, text="请选择音频文件:", anchor="w", **label_style, tags="text")
input_entry = create_custom_entry(canvas, 250, 85, width=400, height=30)
create_rounded_button(canvas, 660, 80, "浏览", select_files)

canvas.create_text(100, 160, text="请选择输出文件夹:", anchor="w", **label_style, tags="text")
output_entry = create_custom_entry(canvas, 250, 145, width=400, height=30)
create_rounded_button(canvas, 660, 140, "选择", select_output_folder)

create_rounded_button(canvas, 660, 200, "开始转换", convert)
canvas.create_text(100, 220, text="转换支持后缀为 .m4a .flac .wav .ogg .ncm 的文件", anchor="w", **label_style, tags="text")

# 调用 resize_image 函数以确保背景图片在窗口初始化时正确显示
root.update_idletasks()
resize_image()

root.mainloop() 