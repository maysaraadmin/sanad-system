from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hadith_app', '0014_populate_system_hadith_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='hadith',
            name='anomaly_score',
            field=models.FloatField(default=0.0, verbose_name='درجة الشذوذ'),
        ),
        migrations.AddField(
            model_name='hadith',
            name='is_mutawatir',
            field=models.BooleanField(default=False, verbose_name='متواتر'),
        ),
        migrations.AddField(
            model_name='hadith',
            name='is_shadh',
            field=models.BooleanField(default=False, verbose_name='شاذ'),
        ),
        migrations.AddField(
            model_name='narrator',
            name='reliability_history',
            field=models.JSONField(default=list, verbose_name='سجل التوثيق'),
        ),
        migrations.AddField(
            model_name='sanadnarrator',
            name='is_mursal',
            field=models.BooleanField(default=False, verbose_name='مرسل'),
        ),
        migrations.AddField(
            model_name='sanadnarrator',
            name='is_tadlis',
            field=models.BooleanField(default=False, verbose_name='تدليس'),
        ),
    ]
