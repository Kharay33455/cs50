# Generated by Django 5.1.4 on 2025-01-20 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0008_alter_communitymessage_message'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='message',
            field=models.TextField(blank=True, null=True),
        ),
    ]
