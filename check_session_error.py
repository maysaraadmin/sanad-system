
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanad_system.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'sanad_system'))
django.setup()

from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

try:
    # Just try to filter, it should fail if 'user' field doesn't exist
    # usage of dummy user object isn't needed for the filter call check on field existence, 
    # but let's try to be consistent with the code
    try:
        user = User.objects.first()
    except:
        user = None
        
    print(f"User: {user}")
    if user:
        sessions = Session.objects.filter(user=user)
        print("Query successful (surprisingly)")
    else:
        # If no user, mock it or just check field
        sessions = Session.objects.filter(user__isnull=False)
except Exception as e:
    print(f"Error caught: {e}")
