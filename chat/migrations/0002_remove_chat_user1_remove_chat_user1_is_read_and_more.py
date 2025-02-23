# Generated by Django 5.1.4 on 2024-12-28 21:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chat',
            name='user1',
        ),
        migrations.RemoveField(
            model_name='chat',
            name='user1_is_read',
        ),
        migrations.RemoveField(
            model_name='chat',
            name='user2',
        ),
        migrations.RemoveField(
            model_name='chat',
            name='user2_is_read',
        ),
        migrations.CreateModel(
            name='ChatUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_read', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('media', models.ImageField(upload_to='chat/')),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chat.chat')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chat.chatuser')),
            ],
        ),
    ]
