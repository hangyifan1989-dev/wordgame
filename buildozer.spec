[app]

title = \u6797\u4e00\u5355\u8bcd
package.name = wordgame
package.domain = org.linyi

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,wav,mp3,txt,xlsx,xlsm,csv
source.exclude_exts = spec
source.exclude_dirs = tests, venv, .env, __pycache__, .git
source.exclude_patterns = buildozer.spec

version = 0.13
# version.regex =
# version.filename =

requirements = python3,kivy,plyer

presplash.filename =
icon.filename =

orientation = landscape
osx.package_name = WordGame

android.permissions = INTERNET
android.api = 34
android.minapi = 21
android.ndk = 28c
p4a.bootstrap = sdl2
# android.gradle_dependencies =

android.archs = arm64-v8a
android.entitlements =
android.keyalias =
android.keystore =
android.private_storage = True
android.wakelock = False
android.windowsoftinputmode = adjustResize

ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_cmake_url = https://github.com/kivy/ios-cmake/archive/refs/heads/master.tar.gz
ios.ios_cmake_branch = master
ios.simulator = False

[buildozer]

log_level = 2
warn_on_root = 1
