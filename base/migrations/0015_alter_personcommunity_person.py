# Generated by Django 5.1.4 on 2024-12-27 02:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0014_post_community'),
    ]

    operations = [
        migrations.AlterField(
            model_name='personcommunity',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.person'),
        ),
    ]
