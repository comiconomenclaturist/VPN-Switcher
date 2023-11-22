from setuptools import setup

APP = ["VPN Switcher.py"]
DATA_FILES = ["icon_1024_x_1024_white.png", "country_codes.json"]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "LSUIElement": True,
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
