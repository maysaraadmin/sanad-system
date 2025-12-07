
import os
import django
import sys
import inspect

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanad_system.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'sanad_system'))
django.setup()

import hadith_app.views
print(f"File: {hadith_app.views.__file__}")
print(f"Dir: {dir(hadith_app.views)}")

try:
    from hadith_app.views import HadithUpdateView
    print("HadithUpdateView imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
