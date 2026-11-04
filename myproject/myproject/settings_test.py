from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

AUTH_PASSWORD_VALIDATORS = []
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# 測試不跑 collectstatic，改用一般靜態檔儲存；否則開 admin 頁會因缺少 manifest 而失敗。
STORAGES = {**STORAGES, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
