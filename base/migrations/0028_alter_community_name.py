# Generated by Django 5.1.4 on 2025-01-04 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0027_community_description_alter_community_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='community',
            name='name',
            field=models.CharField(max_length=30),
        ),
    ]
