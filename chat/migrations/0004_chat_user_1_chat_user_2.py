# Generated by Django 5.1.4 on 2024-12-29 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_remove_chatuser_is_read_chatuser_has_new_message_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chat',
            name='user_1',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='chat',
            name='user_2',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
