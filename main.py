import os
import platform
import re
import shutil
import threading
from pathlib import Path

import flet as ft
import yt_dlp

APP_NAME = "COPA X"
DEFAULT_DIR = "/storage/emulated/0/Download/COPA X/"

QUALITY = {
    "أعلى جودة": "bv*+ba/b",
    "720p": "bv*[height<=720]+ba/b[height<=720]/b",
    "480p": "bv*[height<=480]+ba/b[height<=480]/b",
    "360p": "bv*[height<=360]+ba/b[height<=360]/b",
}

def get_abi():
    m = platform.machine().lower()
    if "aarch64" in m or "arm64" in m:
        return "arm64-v8a"
    if "armv7" in m or m == "arm":
        return "armeabi-v7a"
    if "x86_64" in m or "amd64" in m:
        return "x86_64"
    if m in ("i686", "x86"):
        return "x86"
    return m

def bundled_binary(name):
    """Copy an Android binary from the read-only Flet bundle to writable app storage."""
    abi = get_abi()
    storage = Path(os.environ.get("FLET_APP_STORAGE_DATA", Path.cwd()))
    dst = storage / "copa_x_bin" / abi / name
    if dst.exists():
        return str(dst)

    src = Path(__file__).resolve().parent / "assets" / "bin" / abi / name
    if not src.exists():
        return None

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    try:
        dst.chmod(dst.stat().st_mode | 0o111)
    except OSError:
        pass
    return str(dst)

def safe_component(value, limit=80):
    value = value or "video"
    value = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip().rstrip(".")
    return value[:limit] or "video"

class YDLLogger:
    def __init__(self, fn):
        self.fn = fn
    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.fn(msg + "\n")
    def info(self, msg):
        self.fn(msg + "\n")
    def warning(self, msg):
        self.fn("[WARN] " + msg + "\n")
    def error(self, msg):
        self.fn("[ERROR] " + msg + "\n")

def main(page: ft.Page):
    page.title = APP_NAME
    page.rtl = True
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed="#673AB7")

    url = ft.TextField(
        label="رابط الفيديو / Playlist",
        hint_text="YouTube، TikTok، Instagram...",
        filled=True, border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )
    quality = ft.Dropdown(
        label="الجودة",
        options=[ft.dropdown.Option(x) for x in QUALITY],
        value="أعلى جودة", filled=True, border_radius=12,
    )
    langs = ft.TextField(
        label="لغات الترجمة (مثال: ar,en)",
        value="ar,en", filled=True, border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )
    auto_sub = ft.Switch(label="تحميل الترجمة الآلية", value=True)
    embed_sub = ft.Switch(label="دمج الترجمة داخل الفيديو", value=False)
    playlist_dirs = ft.Switch(
        label="مجلد منفصل لكل فيديو في Playlist", value=True
    )
    path = ft.TextField(
        label="مجلد الحفظ",
        value=DEFAULT_DIR,
        filled=True, border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )

    log = ft.Text("", selectable=True, size=11, font_family="monospace")
    log_box = ft.Container(
        content=ft.Column([log], scroll=ft.ScrollMode.AUTO),
        height=260, bgcolor="#111111", padding=10, border_radius=12,
    )
    status = ft.Text("", weight=ft.FontWeight.BOLD, size=12)
    progress = ft.ProgressRing(visible=False, width=22, height=22)

    def write(text):
        log.value += text
        try:
            page.update()
        except Exception:
            pass

    def hook(d):
        if d.get("status") == "downloading":
            status.value = (
                f"جاري التحميل: {d.get('_percent_str','')} | "
                f"{d.get('_speed_str','')} | ETA {d.get('_eta_str','')}"
            )
        elif d.get("status") == "finished":
            status.value = "تم التنزيل، جارٍ المعالجة..."
        try:
            page.update()
        except Exception:
            pass

    def worker(target_url, fmt, language_text, auto_value,
               save_dir, playlist_value, embed_value):
        try:
            os.makedirs(save_dir, exist_ok=True)

            ffmpeg = bundled_binary("ffmpeg")
            qjs = bundled_binary("qjs")

            write(f"[INFO] ABI: {get_abi()}\n")
            write(f"[INFO] yt-dlp: {yt_dlp.version.__version__}\n")
            write(f"[INFO] FFmpeg: {ffmpeg or 'غير موجود'}\n")
            write(f"[INFO] QuickJS: {qjs or 'غير موجود'}\n")

            if playlist_value:
                template = os.path.join(
                    save_dir,
                    "video %(playlist_index)03d",
                    "%(title).80s [%(id)s].%(ext)s",
                )
            else:
                template = os.path.join(
                    save_dir,
                    "%(title).80s [%(id)s].%(ext)s",
                )

            opts = {
                "format": fmt,
                "outtmpl": template,
                "merge_output_format": "mp4",
                "retries": 10,
                "fragment_retries": 10,
                "file_access_retries": 5,
                "extractor_retries": 3,
                "continuedl": True,
                "overwrites": False,
                "writesubtitles": True,
                "writeautomaticsub": auto_value,
                "subtitleslangs": [
                    x.strip() for x in language_text.split(",") if x.strip()
                ],
                "subtitlesformat": "srt",
                "progress_hooks": [hook],
                "logger": YDLLogger(write),
                "quiet": False,
                "no_warnings": False,
            }

            if ffmpeg:
                opts["ffmpeg_location"] = ffmpeg

            if qjs:
                opts["js_runtimes"] = {"quickjs": qjs}
                opts["remote_components"] = {"ejs": ["github"]}

            if embed_value and ffmpeg:
                opts["embedsubs"] = True

            with yt_dlp.YoutubeDL(opts) as ydl:
                rc = ydl.download([target_url])

            if rc not in (0, None):
                raise RuntimeError(f"yt-dlp returned {rc}")

            write("\n[DONE] تم الانتهاء بنجاح ✅\n")
            status.value = "تم الانتهاء بنجاح ✅"

        except Exception as exc:
            msg = str(exc)
            write("\n[ERROR] " + msg + "\n")
            low = msg.lower()
            if "403" in low:
                write(
                    "[HELP] 403: المنصة رفضت الطلب. "
                    "التحديث وJavaScript يساعدان، لكن بعض المواقع تتطلب جلسة دخول/كوكيز.\n"
                )
            if "javascript" in low or "js runtime" in low or "challenge" in low:
                write(
                    "[HELP] JavaScript: تأكد أن QuickJS موجود داخل APK "
                    "وأن EJS متاح.\n"
                )
            status.value = "حدث خطأ ❌"
        finally:
            progress.visible = False
            download_button.disabled = False
            try:
                page.update()
            except Exception:
                pass

    def start_download(_):
        target = (url.value or "").strip()
        if not target:
            url.error_text = "أدخل الرابط"
            page.update()
            return

        url.error_text = None
        log.value = ""
        status.value = "بدء التحميل..."
        progress.visible = True
        download_button.disabled = True
        page.update()

        threading.Thread(
            target=worker,
            args=(
                target,
                QUALITY.get(quality.value, QUALITY["أعلى جودة"]),
                langs.value or "ar,en",
                bool(auto_sub.value),
                (path.value or DEFAULT_DIR).strip(),
                bool(playlist_dirs.value),
                bool(embed_sub.value),
            ),
            daemon=True,
        ).start()

    download_button = ft.ElevatedButton(
        "⬇ ابدأ التحميل", width=400, height=48, on_click=start_download
    )

    download_view = ft.Container(
        padding=12,
        content=ft.Column(
            [
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            [
                                url, quality, langs, auto_sub,
                                embed_sub, playlist_dirs, path
                            ],
                            spacing=12,
                        ),
                    )
                ),
                ft.Row(
                    [download_button, progress],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                status,
                ft.Text("السجل", weight=ft.FontWeight.BOLD),
                log_box,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    dark = ft.Switch(
        label="الوضع الليلي",
        value=True,
        on_change=lambda e: (
            setattr(
                page,
                "theme_mode",
                ft.ThemeMode.DARK if e.control.value
                else ft.ThemeMode.LIGHT,
            ),
            page.update(),
        ),
    )

    settings_view = ft.Container(
        padding=16,
        content=ft.Column(
            [
                ft.Text("COPA X", size=24, weight=ft.FontWeight.BOLD),
                dark,
                ft.Text(
                    "Universal: arm64-v8a + armeabi-v7a + x86_64 + x86",
                    size=12,
                ),
                ft.Text(
                    "FFmpeg وQuickJS يتم تجهيزهما داخل GitHub Actions "
                    "ثم تضمينهما في APK.",
                    size=12,
                ),
                ft.Text(
                    "أسماء الملفات تُقص لتقليل مشاكل طول المسار.",
                    size=12,
                ),
                ft.Text(
                    "403 لا يمكن ضمان منعه؛ قد يكون من حماية المنصة "
                    "أو الحاجة إلى جلسة دخول.",
                    size=12,
                ),
            ],
            spacing=12,
        ),
    )

    page.add(
        ft.Tabs(
            selected_index=0,
            length=2,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="⬇ تحميل"),
                            ft.Tab(label="⚙ إعدادات"),
                        ]
                    ),
                    ft.TabBarView(
                        expand=True,
                        controls=[download_view, settings_view],
                    ),
                ],
            ),
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
