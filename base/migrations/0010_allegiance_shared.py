# Generated by Django 5.1.4 on 2024-12-25 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0009_alter_allegiance_allegiance'),
    ]

    operations = [
        migrations.AddField(
            model_name='allegiance',
            name='shared',
            field=models.BooleanField(default=False),
        ),
    ]
