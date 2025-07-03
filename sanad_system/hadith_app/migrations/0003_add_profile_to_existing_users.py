from django.db import migrations

def add_profiles_to_existing_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('hadith_app', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.create(user=user)

class Migration(migrations.Migration):
    dependencies = [
        ('hadith_app', '0002_userprofile'),
    ]

    operations = [
        migrations.RunPython(add_profiles_to_existing_users),
    ]
