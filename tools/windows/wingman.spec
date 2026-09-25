# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包定義，CI（.github/workflows/release.yml、windows.yml）和 tools/windows/build.bat 共用這一份。
在 repo 根目錄執行：pyinstaller --noconfirm --clean tools/windows/wingman.spec
onedir 不是 onefile：PySide6 + onnxruntime 打出來 ~150MB，onefile 每次啟動都要解壓一遍，慢且佔臨時盤。
只在 Windows 上跑，下面的 collect_all 也只認 Windows 上裝好的那幾個包。"""
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))  # noqa: F821 -- SPECPATH 由 PyInstaller 注入

NAME = "chat-wingman"

hiddenimports = [
    # spawn 出來的採集子程序按名字 import wingman.app.worker，再順著它拉 capture/ocr；
    # 父程序這邊 engine 也是執行時才走到，一併釘死，別指望靜態分析都能掃出來
    "wingman.app.worker", "wingman.app.capture", "wingman.app.ocr", "wingman.app.fill",
    "wingman.app.overlay", "wingman.app.settings", "wingman.app.version", "wingman.app.update",
    "wingman.app.debugwin",  # debugwin 是開了除錯檢視才 import 的
    "wingman.core.engine", "wingman.core.draft", "wingman.core.jev_client", "wingman.core.questions",
    "wingman.core.providers", "wingman.core.llm",
]
datas, binaries = [], []
for pkg in (
    "rapidocr_onnxruntime",  # .onnx 模型 + config.yaml 是包資料，不收就是啟動即炸
    "onnxruntime",           # capi 下面那堆 DLL
    "qfluentwidgets",        # qss / 圖示資源
    "windows_capture",       # Rust 編譯的 .pyd
    # 四個模型 SDK：core/llm.py 和 jev_client 裡是**函式內 import**，靜態分析掃不到，必須顯式收
    "openai",
    "socksio",                # httpx 選用的 SOCKS 代理支援（上游 PR #15）
    "typesafe_sdk",
    "anthropic",
    "google.genai",
    "certifi",               # httpx 的 CA 證書包；certifi 的官方 hook 通常收得到，這裡寫明白省得漏
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

excludes = [
    # 確認沒人用：rapidocr 只 import 了 cv2 / PIL / yaml / pyclipper / shapely（PIL 千萬別排，讀圖要它）
    "tkinter", "matplotlib", "scipy", "pandas",
] + ["PySide6." + m for m in (
    # 留著 QtCore / QtGui / QtWidgets / QtSvg / QtSvgWidgets / QtXml —— import qfluentwidgets 實測就這六個
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebEngineQuick", "QtWebChannel",
    "QtMultimedia", "QtMultimediaWidgets", "QtCharts", "QtDataVisualization",
    "QtQuick", "QtQuick3D", "QtQuickControls2", "QtQuickWidgets", "QtQuickTest", "QtQml",
    "QtPdf", "QtPdfWidgets", "QtBluetooth", "QtNfc", "QtSensors", "QtSerialPort",
    "QtTest", "QtDesigner", "QtHelp", "QtRemoteObjects", "QtScxml", "QtStateMachine",
    "QtTextToSpeech", "QtPositioning", "QtLocation", "QtSql",
    "Qt3DCore", "Qt3DRender", "Qt3DInput", "Qt3DLogic", "Qt3DAnimation", "Qt3DExtras",
)]

a = Analysis(
    [os.path.join(ROOT, "wingman", "__main__.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # runner 上本來就沒 upx，而且壓 Qt / onnxruntime 的 DLL 是出了名的能壓壞
    console=False,  # 不要黑框；print 也就跟著沒了，狀態介面上都有，聊天內容本來就不許落日誌
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "docs", "images", "wingman.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NAME,
)
