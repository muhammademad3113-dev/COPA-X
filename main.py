import os
import platform
import shutil
import stat
import threading
from pathlib import Path

import flet as ft
import yt_dlp


APP_NAME = "COPA X"

DEFAULT_DIR = "/storage/emulated/0/COPA X/"

QUALITY = {
    "أعلى جودة": "bv*+ba/b",
    "720p": "bv*[height<=720]+ba/b[height<=720]/b",
    "480p": "bv*[height<=480]+ba/b[height<=480]/b",
    "360p": "bv*[height<=360]+ba/b[height<=360]/b",
}


def get_abi():
    machine = platform.machine().lower()

    if "aarch64" in machine or "arm64" in machine:
        return "arm64-v8a"

    if "armv7" in machine or machine == "arm":
        return "armeabi-v7a"

    if "x86_64" in machine or "amd64" in machine:
        return "x86_64"

    return machine


def get_assets_dir():
    """
    Flet 0.86+:
    ملفات assets المضمنة داخل التطبيق تكون للقراءة فقط.
    نقرأ منها ثم ننسخ executable إلى مجلد التطبيق القابل للكتابة.
    """

    env_dir = os.environ.get("FLET_ASSETS_DIR")

    if env_dir:
        return Path(env_dir)

    # للتشغيل أثناء التطوير
    return Path(__file__).resolve().parent / "assets"


def runtime_file(name):
    """
    العثور على FFmpeg / QuickJS المناسب لمعمارية الجهاز.

    البحث:
    1) assets المضمنة داخل APK.
    2) assets المحلية أثناء التطوير.

    ثم نسخ الملف إلى مجلد writable وإعطاؤه صلاحية التنفيذ.
    """

    abi = get_abi()

    assets_dir = get_assets_dir()

    source = assets_dir / "bin" / abi / name

    if not source.exists():
        # fallback للتطوير
        fallback = (
            Path(__file__).resolve().parent
            / "assets"
            / "bin"
            / abi
            / name
        )

        if fallback.exists():
            source = fallback
        else:
            return None

    storage = Path(
        os.environ.get(
            "FLET_APP_STORAGE_DATA",
            Path.cwd(),
        )
    )

    destination = (
        storage
        / "copa_x_bin"
        / abi
        / name
    )

    try:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # إذا الملف غير موجود أو تغير الحجم، انسخه من جديد.
        if (
            not destination.exists()
            or destination.stat().st_size != source.stat().st_size
        ):
            shutil.copy2(
                source,
                destination,
            )

        destination.chmod(
            destination.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

        return str(destination)

    except Exception:
        return None


class Log:
    def __init__(self, callback):
        self.callback = callback

    def debug(self, message):
        if not str(message).startswith("[debug]"):
            self.callback(str(message) + "\n")

    def info(self, message):
        self.callback(str(message) + "\n")

    def warning(self, message):
        self.callback("[WARN] " + str(message) + "\n")

    def error(self, message):
        self.callback("[ERROR] " + str(message) + "\n")


def main(page: ft.Page):
    page.title = APP_NAME
    page.rtl = True
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    # ---------------------------------------------------------
    # عناصر التحميل
    # ---------------------------------------------------------

    url = ft.TextField(
        label="رابط الفيديو / Playlist",
        hint_text="YouTube، TikTok، Instagram وغيرها...",
        filled=True,
        border_radius=12,
        text_align=ft.TextAlign.RIGHT,
        autofocus=False,
    )

    quality = ft.Dropdown(
        label="الجودة",
        options=[
            ft.dropdown.Option(name)
            for name in QUALITY.keys()
        ],
        value="أعلى جودة",
        filled=True,
        border_radius=12,
    )

    subtitle_languages = ft.TextField(
        label="لغات الترجمة",
        value="ar,en",
        hint_text="مثال: ar,en,fr",
        filled=True,
        border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )

    automatic_subtitles = ft.Switch(
        label="تحميل الترجمة الآلية",
        value=True,
    )

    embed_subtitles = ft.Switch(
        label="دمج الترجمة داخل الفيديو",
        value=False,
    )

    playlist_folders = ft.Switch(
        label="مجلد منفصل لكل فيديو في Playlist",
        value=True,
    )

    save_path = ft.TextField(
        label="مجلد الحفظ",
        value=DEFAULT_DIR,
        filled=True,
        border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )

    log_text = ft.Text(
        "",
        selectable=True,
        size=11,
        font_family="monospace",
    )

    log_box = ft.Container(
        content=ft.Column(
            [log_text],
            scroll=ft.ScrollMode.AUTO,
        ),
        height=280,
        bgcolor="#111111",
        padding=10,
        border_radius=12,
    )

    status = ft.Text(
        "",
        weight=ft.FontWeight.BOLD,
        size=13,
    )

    progress = ft.ProgressRing(
        visible=False,
        width=24,
        height=24,
    )

    # ---------------------------------------------------------
    # وظائف الواجهة
    # ---------------------------------------------------------

    def update_page():
        try:
            page.update()
        except Exception:
            pass

    def write_log(message):
        log_text.value += str(message)

        # لا نترك السجل يكبر بلا حدود.
        if len(log_text.value) > 30000:
            log_text.value = log_text.value[-30000:]

        update_page()

    def progress_hook(data):
        state = data.get("status")

        if state == "downloading":

            percent = data.get(
                "_percent_str",
                "",
            )

            speed = data.get(
                "_speed_str",
                "",
            )

            eta = data.get(
                "_eta_str",
                "",
            )

            filename = data.get(
                "filename",
                "",
            )

            if filename:
                filename = os.path.basename(
                    str(filename)
                )

            status.value = (
                f"جاري التحميل: {percent} | "
                f"{speed} | ETA {eta}\n"
                f"{filename}"
            )

            update_page()

        elif state == "finished":

            status.value = (
                "تم تنزيل الملف، جارٍ المعالجة..."
            )

            update_page()

    # ---------------------------------------------------------
    # العامل الرئيسي للتحميل
    # ---------------------------------------------------------

    def worker():
        try:
            target_url = (
                url.value or ""
            ).strip()

            if not target_url:
                raise ValueError(
                    "لم يتم إدخال رابط."
                )

            save_dir = (
                save_path.value or DEFAULT_DIR
            ).strip()

            if not save_dir:
                save_dir = DEFAULT_DIR

            # -------------------------------------------------
            # تجهيز مجلد الحفظ
            # -------------------------------------------------

            try:
                os.makedirs(
                    save_dir,
                    exist_ok=True,
                )
            except Exception as exc:
                write_log(
                    "[WARN] تعذر إنشاء مجلد الحفظ المحدد.\n"
                    f"[WARN] {exc}\n"
                    "[WARN] سيتم استخدام مجلد التطبيق مؤقتًا.\n"
                )

                fallback_dir = Path(
                    os.environ.get(
                        "FLET_APP_STORAGE_DATA",
                        Path.cwd(),
                    )
                ) / "downloads"

                fallback_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                save_dir = str(
                    fallback_dir
                )

                write_log(
                    f"[INFO] مجلد الحفظ البديل: {save_dir}\n"
                )

            # -------------------------------------------------
            # الحصول على FFmpeg وQuickJS
            # -------------------------------------------------

            ffmpeg = runtime_file(
                "ffmpeg"
            )

            qjs = runtime_file(
                "qjs"
            )

            write_log(
                f"[INFO] ABI: {get_abi()}\n"
            )

            write_log(
                f"[INFO] yt-dlp: "
                f"{yt_dlp.version.__version__}\n"
            )

            write_log(
                "[INFO] FFmpeg: "
                f"{ffmpeg or 'غير موجود'}\n"
            )

            write_log(
                "[INFO] QuickJS: "
                f"{qjs or 'غير موجود'}\n"
            )

            if not ffmpeg:
                raise RuntimeError(
                    "FFmpeg غير موجود داخل APK."
                )

            if not qjs:
                raise RuntimeError(
                    "QuickJS غير موجود داخل APK."
                )

            # -------------------------------------------------
            # قالب أسماء الملفات
            # -------------------------------------------------

            if playlist_folders.value:
                output_template = os.path.join(
                    save_dir,
                    "video %(playlist_index)03d",
                    "%(title).100s [%(id)s].%(ext)s",
                )
            else:
                output_template = os.path.join(
                    save_dir,
                    "%(title).100s [%(id)s].%(ext)s",
                )

            # -------------------------------------------------
            # إعدادات yt-dlp
            # -------------------------------------------------

            languages = [
                item.strip()
                for item in (
                    subtitle_languages.value or ""
                ).split(",")
                if item.strip()
            ]

            options = {
                "format": QUALITY.get(
                    quality.value,
                    QUALITY["أعلى جودة"],
                ),

                "outtmpl": output_template,

                "merge_output_format": "mp4",

                # محاولات إضافية
                "retries": 10,
                "fragment_retries": 10,
                "file_access_retries": 5,
                "extractor_retries": 5,

                # استكمال التحميل
                "continuedl": True,
                "overwrites": False,

                # أسماء آمنة
                "restrictfilenames": True,
                "windowsfilenames": True,

                # Playlist
                "ignoreerrors": False,

                # الترجمة
                "writesubtitles": bool(
                    languages
                ),

                "writeautomaticsub": bool(
                    automatic_subtitles.value
                    and languages
                ),

                "subtitleslangs": languages,

                "subtitlesformat": "srt/best",

                # Logging
                "progress_hooks": [
                    progress_hook
                ],

                "logger": Log(
                    write_log
                ),

                # EJS / QuickJS
                "js_runtimes": (
                    {
                        "quickjs": qjs
                    }
                    if qjs
                    else {}
                ),

                # السماح لـ yt-dlp باستخدام EJS
                "remote_components": (
                    "ejs:github"
                ),
            }

            # -------------------------------------------------
            # FFmpeg
            # -------------------------------------------------

            options[
                "ffmpeg_location"
            ] = ffmpeg

            # -------------------------------------------------
            # دمج الترجمة داخل الفيديو
            # -------------------------------------------------

            if (
                embed_subtitles.value
                and ffmpeg
                and languages
            ):
                options[
                    "embedsubs"
                ] = True

            # -------------------------------------------------
            # تشغيل yt-dlp
            # -------------------------------------------------

            write_log(
                "\n[INFO] بدء yt-dlp...\n"
            )

            with yt_dlp.YoutubeDL(
                options
            ) as downloader:

                result = downloader.download(
                    [target_url]
                )

            if result not in (
                0,
                None,
            ):
                raise RuntimeError(
                    f"yt-dlp returned {result}"
                )

            write_log(
                "\n[DONE] تم الانتهاء بنجاح ✅\n"
            )

            status.value = (
                "تم الانتهاء بنجاح ✅"
            )

        except Exception as exc:

            message = str(exc)

            write_log(
                "\n[ERROR] "
                + message
                + "\n"
            )

            lower = message.lower()

            if "403" in lower:
                write_log(
                    "[HELP] المنصة رفضت الطلب (403). "
                    "هذا ليس خطأ FFmpeg.\n"
                    "[HELP] تأكد من تحديث yt-dlp وEJS.\n"
                )

            if (
                "javascript" in lower
                or "js runtime" in lower
                or "ejs" in lower
            ):
                write_log(
                    "[HELP] مشكلة JavaScript/EJS. "
                    "تأكد من وجود QuickJS داخل APK.\n"
                )

            if "ffmpeg" in lower:
                write_log(
                    "[HELP] مشكلة FFmpeg. "
                    "تأكد من أن الـWorkflow نجح في تضمينه.\n"
                )

            status.value = (
                "حدث خطأ ❌"
            )

        finally:

            progress.visible = False
            download_button.disabled = False

            update_page()

    # ---------------------------------------------------------
    # بدء التحميل
    # ---------------------------------------------------------

    def start_download(_):
        target = (
            url.value or ""
        ).strip()

        if not target:
            url.error_text = (
                "أدخل رابط الفيديو أو Playlist"
            )

            update_page()
            return

        url.error_text = None

        log_text.value = ""

        status.value = (
            "بدء التحميل..."
        )

        progress.visible = True
        download_button.disabled = True

        update_page()

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    download_button = ft.ElevatedButton(
        "⬇ ابدأ التحميل",
        width=400,
        height=50,
        on_click=start_download,
    )

    # ---------------------------------------------------------
    # صفحة التحميل
    # ---------------------------------------------------------

    download_view = ft.Container(
        padding=12,
        content=ft.Column(
            [
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            [
                                url,
                                quality,
                                subtitle_languages,
                                automatic_subtitles,
                                embed_subtitles,
                                playlist_folders,
                                save_path,
                            ],
                            spacing=12,
                        ),
                    )
                ),

                ft.Row(
                    [
                        download_button,
                        progress,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),

                status,

                ft.Text(
                    "السجل",
                    weight=ft.FontWeight.BOLD,
                ),

                log_box,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
    )

    # ---------------------------------------------------------
    # الإعدادات
    # ---------------------------------------------------------

    dark_mode = ft.Switch(
        label="الوضع الليلي",
        value=True,
    )

    def change_theme(e):
        page.theme_mode = (
            ft.ThemeMode.DARK
            if e.control.value
            else ft.ThemeMode.LIGHT
        )

        update_page()

    dark_mode.on_change = change_theme

    settings_view = ft.Container(
        padding=16,
        content=ft.Column(
            [
                ft.Text(
                    "COPA X",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "Universal Android Downloader",
                    size=14,
                ),

                dark_mode,

                ft.Divider(),

                ft.Text(
                    "المعماريات المدعومة:",
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "arm64-v8a\n"
                    "armeabi-v7a\n"
                    "x86_64",
                    size=13,
                ),

                ft.Divider(),

                ft.Text(
                    "FFmpeg: مضمّن تلقائيًا داخل APK",
                    size=13,
                ),

                ft.Text(
                    "QuickJS: مضمّن تلقائيًا داخل APK",
                    size=13,
                ),

                ft.Text(
                    "yt-dlp + EJS: يتم تحديثهما مع البناء",
                    size=13,
                ),

                ft.Divider(),

                ft.Text(
                    "ملاحظة:",
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "إذا رفض Android الكتابة في المسار "
                    "المحدد، سيستخدم التطبيق مجلدًا "
                    "داخليًا احتياطيًا بدل توقف التحميل.",
                    size=12,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
    )

    # ---------------------------------------------------------
    # التنقل
    # ---------------------------------------------------------

    current_view = ft.Column(
        [download_view],
        expand=True,
    )

    def show_download(_):
        current_view.controls = [
            download_view
        ]
        current_view.update()

    def show_settings(_):
        current_view.controls = [
            settings_view
        ]
        current_view.update()

    navigation = ft.Row(
        [
            ft.ElevatedButton(
                "⬇ التحميل",
                on_click=show_download,
            ),
            ft.ElevatedButton(
                "⚙ الإعدادات",
                on_click=show_settings,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    page.add(
        ft.Column(
            [
                ft.Container(
                    padding=10,
                    content=ft.Text(
                        "COPA X",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),

                navigation,

                current_view,
            ],
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.run(main)
