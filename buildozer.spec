# (For Android builds with Buildozer)
[app]
title = iLoveOPUS
package.name = iloveopus
package.domain = org.tapscodes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,mutagen,pillow
orientation = portrait
fullscreen = 0
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
# (You may add more permissions as needed)
# (You may need to adjust requirements for ffmpeg support or use python-for-android recipes)

[buildozer]
log_level = 2
warn_on_root = 1
