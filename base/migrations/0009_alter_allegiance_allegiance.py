# Generated by Django 5.1.4 on 2024-12-25 06:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_alter_allegiance_allegiance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allegiance',
            name='allegiance',
            field=models.CharField(blank=True, default=None, max_length=10, null=True),
        ),
    ]
