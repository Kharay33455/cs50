# Generated by Django 5.1.4 on 2024-12-29 05:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_chat_user_1_chat_user_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='media',
            field=models.ImageField(blank=True, null=True, upload_to='chat/'),
        ),
    ]
