# Generated by Django 5.1.4 on 2025-01-19 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0038_alter_relationship_relationship'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relationship',
            name='relationship',
            field=models.CharField(choices=[('FO', 'Fan'), ('ST', 'Stalk')], default='ST', max_length=5),
        ),
    ]
