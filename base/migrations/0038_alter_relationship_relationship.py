# Generated by Django 5.1.4 on 2025-01-19 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0037_rename_relationships_relationship'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relationship',
            name='relationship',
            field=models.CharField(choices=[('FO', 'Fan'), ('ST', 'Stalk'), ('NO', 'None')], default='NO', max_length=5),
        ),
    ]
