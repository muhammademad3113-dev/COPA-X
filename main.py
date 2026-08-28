
import os, platform, shutil, stat, subprocess, threading
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
    m = platform.machine().lower()
    if "aarch64" in m or "arm64" in m: return "arm64-v8a"
    if "armv7" in m or m == "arm": return "armeabi-v7a"
    if "x86_64" in m or "amd64" in m: return "x86_64"
    return m

def runtime_file(name):
    abi = get_abi()
    # Flet 0.86+ stores app data under FLET_APP_STORAGE_DATA.
    data = Path(os.environ.get("FLET_APP_STORAGE_DATA", Path.cwd()))
    dst = data / "copa_x_bin" / abi / name
    if dst.exists():
        return str(dst)
    src = Path(__file__).resolve().parent / "assets" / "bin" / abi / name
    if not src.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(dst)

class Log:
    def __init__(self, fn): self.fn=fn
    def debug(self, m):
        if not m.startswith("[debug]"): self.fn(m+"\n")
    def info(self,m): self.fn(m+"\n")
    def warning(self,m): self.fn("[WARN] "+m+"\n")
    def error(self,m): self.fn("[ERROR] "+m+"\n")

def main(page: ft.Page):
    page.title=APP_NAME
    page.rtl=True
    page.padding=0
    page.theme_mode=ft.ThemeMode.DARK

    url=ft.TextField(label="رابط الفيديو / Playlist", hint_text="YouTube، TikTok، Instagram...", filled=True, border_radius=12, text_align=ft.TextAlign.RIGHT)
    q=ft.Dropdown(label="الجودة", options=[ft.dropdown.Option(x) for x in QUALITY], value="أعلى جودة", filled=True, border_radius=12)
    langs=ft.TextField(label="لغات الترجمة", value="ar,en", filled=True, border_radius=12, text_align=ft.TextAlign.RIGHT)
    auto=ft.Switch(label="الترجمة الآلية", value=True)
    embed=ft.Switch(label="دمج الترجمة داخل الفيديو", value=False)
    playlist_dirs=ft.Switch(label="مجلد منفصل لكل فيديو في Playlist", value=True)
    path=ft.TextField(label="مجلد الحفظ", value=DEFAULT_DIR, filled=True, border_radius=12, text_align=ft.TextAlign.RIGHT)

    log=ft.Text("", selectable=True, size=11, font_family="monospace")
    box=ft.Container(content=ft.Column([log],scroll=ft.ScrollMode.AUTO),height=260,bgcolor="#111111",padding=10,border_radius=12)
    status=ft.Text("",weight=ft.FontWeight.BOLD,size=12)
    spin=ft.ProgressRing(visible=False,width=22,height=22)

    def write(s):
        log.value += s
        try: page.update()
        except: pass

    def hook(d):
        if d.get("status")=="downloading":
            status.value=f"جاري التحميل: {d.get('_percent_str','')} | {d.get('_speed_str','')} | ETA {d.get('_eta_str','')}"
            try: page.update()
            except: pass
        elif d.get("status")=="finished":
            status.value="تم التنزيل، جارٍ المعالجة..."
            try: page.update()
            except: pass

    def worker():
        try:
            save=(path.value or DEFAULT_DIR).strip()
            os.makedirs(save,exist_ok=True)
            ffmpeg=runtime_file("ffmpeg")
            qjs=runtime_file("qjs")
            write(f"[INFO] ABI: {get_abi()}\n")
            write(f"[INFO] yt-dlp: {yt_dlp.version.__version__}\n")
            write(f"[INFO] FFmpeg: {ffmpeg or 'غير موجود'}\n")
            write(f"[INFO] QuickJS: {qjs or 'غير موجود'}\n")

            tmpl=(os.path.join(save,"video %(playlist_index)03d","%(title).100s [%(id)s].%(ext)s")
                   if playlist_dirs.value else
                   os.path.join(save,"%(title).100s [%(id)s].%(ext)s"))

            opts={
                "format":QUALITY.get(q.value,QUALITY["أعلى جودة"]),
                "outtmpl":tmpl,
                "merge_output_format":"mp4",
                "retries":10,
                "fragment_retries":10,
                "file_access_retries":5,
                "extractor_retries":3,
                "continuedl":True,
                "overwrites":False,
                "restrictfilenames":True,
                "windowsfilenames":True,
                "writesubtitles":True,
                "writeautomaticsub":bool(auto.value),
                "subtitleslangs":[x.strip() for x in (langs.value or "").split(",") if x.strip()],
                "subtitlesformat":"srt",
                "progress_hooks":[hook],
                "logger":Log(write),
                # Deno is recommended by current yt-dlp; QuickJS is bundled here
                # because Android packaging is much smaller.
                "js_runtimes": {"quickjs": qjs} if qjs else {},
            }
            if ffmpeg: opts["ffmpeg_location"]=ffmpeg
            if embed.value and ffmpeg: opts["embedsubs"]=True

            with yt_dlp.YoutubeDL(opts) as y:
                rc=y.download([url.value.strip()])
            if rc not in (0,None): raise RuntimeError(f"yt-dlp returned {rc}")
            write("\n[DONE] تم الانتهاء بنجاح ✅\n")
            status.value="تم الانتهاء بنجاح ✅"
        except Exception as e:
            msg=str(e)
            write("\n[ERROR] "+msg+"\n")
            if "403" in msg: write("[HELP] 403: المنصة رفضت الطلب؛ تأكد من تحديث yt-dlp وتوفر JavaScript/EJS.\n")
            if "javascript" in msg.lower() or "js runtime" in msg.lower(): write("[HELP] JavaScript: QuickJS غير متاح أو غير مناسب لمعمارية الهاتف.\n")
            status.value="حدث خطأ ❌"
        finally:
            spin.visible=False; button.disabled=False
            try: page.update()
            except: pass

    def start(_):
        if not (url.value or "").strip():
            url.error_text="أدخل الرابط"; page.update(); return
        url.error_text=None; log.value=""; status.value="بدء التحميل..."
        spin.visible=True; button.disabled=True; page.update()
        threading.Thread(target=worker,daemon=True).start()

    button=ft.ElevatedButton("⬇ ابدأ التحميل",width=400,height=48,on_click=start)

    download=ft.Container(padding=12,content=ft.Column([
        ft.Card(content=ft.Container(padding=16,content=ft.Column([url,q,langs,auto,embed,playlist_dirs,path],spacing=12))),
        ft.Row([button,spin],alignment=ft.MainAxisAlignment.CENTER),status,
        ft.Text("السجل",weight=ft.FontWeight.BOLD),box
    ],spacing=12,scroll=ft.ScrollMode.AUTO))

    dark=ft.Switch("الوضع الليلي",value=True,on_change=lambda e:(setattr(page,"theme_mode",ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT),page.update()))
    settings=ft.Container(padding=16,content=ft.Column([
        ft.Text("COPA X",size=22,weight=ft.FontWeight.BOLD),dark,
        ft.Text("Universal APK: arm64-v8a + armeabi-v7a + x86_64",size=12),
        ft.Text("أسماء الملفات تُقص إلى 100 حرف ويُضاف ID لتفادي مشاكل طول المسار.",size=12),
        ft.Text("403 لا يمكن ضمان منعه؛ فهو قد يكون رفضًا من المنصة أو يتطلب صلاحيات/جلسة.",size=12),
    ],spacing=12))

    page.add(ft.Tabs(selected_index=0,length=2,expand=True,content=ft.Column(expand=True,controls=[
        ft.TabBar(tabs=[ft.Tab(label="⬇ تحميل"),ft.Tab(label="⚙ إعدادات")]),
        ft.TabBarView(expand=True,controls=[download,settings])
    ])))

if __name__=="__main__":
    ft.app(target=main)
