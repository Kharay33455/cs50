# Generated by Django 5.1.4 on 2025-01-07 06:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0031_notification_is_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='has_notification',
            field=models.BooleanField(default=False),
        ),
    ]
