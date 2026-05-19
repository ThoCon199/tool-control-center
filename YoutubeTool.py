import os
import json
import glob
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from yt_dlp import YoutubeDL
import threading
import sys
import requests

CURRENT_VERSION = "2.0.1"
LICENSE_KEY = "LICENSE-XYZ-999"

UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ThoCon199/tool-control-center/main/tool_update.json"
SYSTEM_STATUS_URL = "https://raw.githubusercontent.com/ThoCon199/tool-control-center/main/system_status.json"
LICENSE_DB_URL = "https://raw.githubusercontent.com/ThoCon199/tool-control-center/main/license_db.json"

NODE_PATH = r"C:\Program Files\nodejs\node.exe"

DOWNLOAD_LOG = "downloaded_videos.json"
LAST_CHANNEL_FILE = "last_channel.txt"


def check_system_and_license():
    try:
        import time

        cache = f"?t={int(time.time())}"

        r = requests.get(SYSTEM_STATUS_URL + cache, timeout=5)
        system_data = r.json()

        if system_data.get("disable_all"):
            messagebox.showerror(
                "Thông báo",
                system_data.get("message", "Tool đã bị vô hiệu hóa.")
            )
            sys.exit()

        if system_data.get("force_update"):

            latest = system_data.get("latest_version")

            if latest != CURRENT_VERSION:
                messagebox.showerror(
                    "Cập nhật bắt buộc",
                    f"Phiên bản mới: {latest}\nVui lòng cập nhật tool."
                )
                sys.exit()

        r2 = requests.get(LICENSE_DB_URL + cache, timeout=5)
        license_db = r2.json()

        if LICENSE_KEY not in license_db:
            messagebox.showerror("License lỗi", "License không tồn tại.")
            sys.exit()

        if not license_db[LICENSE_KEY].get("active", False):
            messagebox.showerror(
                "License bị thu hồi",
                license_db[LICENSE_KEY].get("note", "Liên hệ admin.")
            )
            sys.exit()

    except Exception as e:
        messagebox.showerror(
            "Lỗi xác minh",
            f"Không thể xác minh license.\n{e}"
        )
        sys.exit()


def auto_update():

    try:
        import time

        cache = f"?t={int(time.time())}"

        r = requests.get(UPDATE_CHECK_URL + cache, timeout=5)
        data = r.json()

        latest = data.get("latest_version")

        if latest != CURRENT_VERSION:

            messagebox.showinfo(
                "Update",
                data.get("message", "Updating...")
            )

            new_code = requests.get(data["update_url"]).text

            current_file = sys.argv[0]

            with open(current_file, "w", encoding="utf-8") as f:
                f.write(new_code)

            messagebox.showinfo(
                "Update",
                "Đã cập nhật xong. Tool sẽ khởi động lại."
            )

            os.execv(sys.executable, ['python'] + sys.argv)

    except Exception as e:
        print("Update check failed:", e)


def send_channel_to_gsheet(channel_url):

    form_url = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSe7qd0SQ7euJwylcQw6_1nB60rM49OVNJxr0RJIh1VRzKEwjg/formResponse"

    data = {
        "entry.465162591": channel_url
    }

    try:
        requests.post(form_url, data=data)
    except:
        pass


def load_downloaded():

    if os.path.exists(DOWNLOAD_LOG):

        with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            return json.load(f)

    return []


def save_downloaded(video_ids):

    with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(video_ids, f, indent=2)


def ensure_output_folders():

    folders = [
        "output/video",
        "output/thumb",
        "output/tiêu đề",
        "output/mô tả",
        "output/video_tags",
        "output/channel_info",
        "output/json"
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)


def safe_filename(name):

    return "".join(
        c for c in name if c.isalnum() or c in " _-"
    ).strip()


def download_file(url, save_path):

    try:
        r = requests.get(url, timeout=15)

        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)

            return True

    except:
        pass

    return False


def download_channel_info(channel_url, log_callback):

    log_callback("📡 Đang lấy thông tin kênh...")

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
    }

    with YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(channel_url, download=False)

        ensure_output_folders()

        channel_name = (
            info.get("channel")
            or info.get("uploader")
            or info.get("title")
            or "unknown_channel"
        )

        safe_name = safe_filename(channel_name)

        description = info.get("description", "")

        tags = info.get("tags", [])

        # avatar
        avatar_url = None

        thumbnails = info.get("thumbnails", [])

        if thumbnails:
            avatar_url = thumbnails[-1].get("url")

        # banner
        banner_url = None

        banner_candidates = (
            info.get("banners")
            or info.get("channel_banners")
            or []
        )

        if banner_candidates:
            banner_url = banner_candidates[-1].get("url")

        # save description
        with open(
            f"output/channel_info/{safe_name}_description.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(description)

        # save tags
        if tags:

            with open(
                f"output/channel_info/{safe_name}_tags.txt",
                "w",
                encoding="utf-8"
            ) as f:
                f.write("\n".join(tags))

        # save raw json
        with open(
            f"output/channel_info/{safe_name}_full.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        # avatar
        if avatar_url:

            ok = download_file(
                avatar_url,
                f"output/channel_info/{safe_name}_avatar.jpg"
            )

            if ok:
                log_callback("✅ Đã tải avatar kênh")

        # banner
        if banner_url:

            ok = download_file(
                banner_url,
                f"output/channel_info/{safe_name}_banner.jpg"
            )

            if ok:
                log_callback("✅ Đã tải banner kênh")

        log_callback("✅ Đã lưu thông tin kênh")


def download_video(video_url, log_callback, download_format):

    temp_outtmpl = '%(id)s.%(ext)s'

    base_opts = {
        'outtmpl': temp_outtmpl,
        'quiet': True,
        'writethumbnail': True,
        'writeinfojson': True,

        'js_runtimes': {
            'node': {'path': NODE_PATH}
        },
    }

    if download_format == 'mp4':

        ydl_opts = {
            **base_opts,

            'format': '(bestvideo[height<=480][vcodec^=avc1]/best[height<=480])[ext=mp4]+bestaudio[ext=m4a]/bestaudio',
            'merge_output_format': 'mp4',
        }

    else:

        ydl_opts = {
            **base_opts,

            'format': 'bestaudio/best',

            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

    with YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(video_url, download=True)

        ensure_output_folders()

        video_id = info.get('id')

        title = info.get('title', '')
        description = info.get('description', '')

        video_tags = info.get('tags', [])

        upload_date_raw = info.get('upload_date')

        if upload_date_raw:
            upload_date = datetime.strptime(upload_date_raw, "%Y%m%d")
            date_prefix = upload_date.strftime("%Y%m%d")
        else:
            date_prefix = "unknown_date"

        # move files
        for file in glob.glob(f"{video_id}.*"):

            ext = file.split('.')[-1].lower()

            new_name = f"{date_prefix}_{video_id}.{ext}"

            if ext in ['mp4', 'webm', 'mkv', 'mp3']:

                target = os.path.join("output/video", new_name)

            elif ext in ['jpg', 'png', 'webp']:

                target = os.path.join("output/thumb", new_name)

            elif ext == "json":

                target = os.path.join("output/json", new_name)

            else:
                continue

            try:
                os.replace(file, target)
            except:
                pass

        # title
        title_file = f"{date_prefix}_{video_id}.txt"

        with open(
            os.path.join("output/tiêu đề", title_file),
            "w",
            encoding="utf-8"
        ) as f:
            f.write(title)

        # description
        with open(
            os.path.join("output/mô tả", title_file),
            "w",
            encoding="utf-8"
        ) as f:
            f.write(description)

        # tags

        # tags
        if video_tags:

            with open(
                os.path.join("output/video_tags", title_file),
                "w",
                encoding="utf-8"
            ) as f:

                f.write("\n".join(video_tags))
        
        log_callback(f"✅ Tải xong: {title}")

        return video_id


def fetch_video_list(channel_url, mode, log_callback):

    sort_map = {
        'newest': 'date',
        'oldest': 'date'
    }

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'force_generic_extractor': False,
    }

    with YoutubeDL(ydl_opts) as ydl:

        log_callback("📥 Đang lấy danh sách video...")

        info = ydl.extract_info(
            f"{channel_url}/videos?view=0&sort={sort_map[mode]}&flow=grid",
            download=False
        )

        entries = info.get("entries", [])

        if mode == "oldest":
            entries.reverse()

        return entries, len(entries)


def start_download():

    def log(msg):

        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
        log_box.update_idletasks()

    channel_url = url_entry.get().strip()

    send_channel_to_gsheet(channel_url)

    mode = mode_var.get()

    download_format = format_var.get()

    try:

        limit = int(limit_entry.get().strip())

        if limit <= 0:
            raise ValueError

    except ValueError:

        messagebox.showerror(
            "Lỗi",
            "Số lượng video phải là số nguyên dương."
        )

        return

    if not channel_url:

        messagebox.showerror(
            "Lỗi",
            "Vui lòng dán link kênh YouTube."
        )

        return

    try:

        with open(
            LAST_CHANNEL_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(channel_url)

    except:
        pass

    log(f"\n🔗 Kênh: {channel_url}")
    log(f"⚙️ Chế độ: {mode}")
    log(f"🎯 Số lượng: {limit}")
    log(f"📁 Định dạng: {download_format}\n")

    downloaded = load_downloaded()

    try:

        # download channel info
        download_channel_info(channel_url, log)

        entries, total = fetch_video_list(
            channel_url,
            mode,
            log
        )

        count = 0

        started = len(downloaded)

        for entry in entries:

            if count >= limit:
                break

            vid = entry["id"]

            video_url = f"https://www.youtube.com/watch?v={vid}"

            if vid in downloaded:
                continue

            index = started + count + 1

            status_label.config(
                text=f"🔢 Đã tải: {index} / {total} video"
            )

            log(f"⬇️ ({index}/{total}) {entry['title']}")

            try:

                vid_id = download_video(
                    video_url,
                    log,
                    download_format
                )

                downloaded.append(vid_id)

                save_downloaded(downloaded)

                count += 1

            except Exception as e:

                log(f"❌ Lỗi tải: {e}")

        log(f"\n✅ Đã tải {count} video.")

        root.after(3000, root.destroy)

    except Exception as e:

        messagebox.showerror(
            "Lỗi",
            f"Không thể lấy danh sách: {e}"
        )


check_system_and_license()

auto_update()

root = tk.Tk()

root.title("YouTube Channel Downloader PRO")
root.geometry("650x700")

root.resizable(False, False)

status_label = tk.Label(
    root,
    text="🔢 Đã tải: 0 / 0 video",
    fg="blue"
)

status_label.pack(pady=(5, 5))

tk.Label(
    root,
    text="🔗 Dán link kênh YouTube:"
).pack(pady=(5, 2))

url_entry = tk.Entry(root, width=75)

url_entry.pack(pady=(0, 10))

try:

    with open(
        LAST_CHANNEL_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        url_entry.insert(0, f.read().strip())

except:
    pass

tk.Label(
    root,
    text="📌 Chọn chế độ tải:"
).pack()

mode_var = tk.StringVar(value="newest")

frm = tk.Frame(root)

frm.pack()

tk.Radiobutton(
    frm,
    text="Mới nhất",
    variable=mode_var,
    value="newest"
).grid(row=0, column=0, padx=10)

tk.Radiobutton(
    frm,
    text="Cũ nhất",
    variable=mode_var,
    value="oldest"
).grid(row=0, column=1, padx=10)

tk.Label(
    root,
    text="🎵 Chọn định dạng tải:"
).pack(pady=(10, 2))

format_var = tk.StringVar(value="mp4")

frm_format = tk.Frame(root)

frm_format.pack()

tk.Radiobutton(
    frm_format,
    text="MP4 (video)",
    variable=format_var,
    value="mp4"
).grid(row=0, column=0, padx=10)

tk.Radiobutton(
    frm_format,
    text="MP3 (âm thanh)",
    variable=format_var,
    value="mp3"
).grid(row=0, column=1, padx=10)

tk.Label(
    root,
    text="🔢 Số lượng video muốn tải:"
).pack(pady=(10, 2))

limit_entry = tk.Entry(root, width=10)

limit_entry.insert(0, "1000")

limit_entry.pack(pady=(0, 10))

tk.Button(
    root,
    text="▶️ Bắt đầu tải",
    command=lambda: threading.Thread(
        target=start_download
    ).start(),
    bg="#4CAF50",
    fg="white",
    width=20
).pack(pady=15)

log_box = tk.Text(
    root,
    height=20,
    width=85
)

log_box.pack(padx=10, pady=10)

root.mainloop()
