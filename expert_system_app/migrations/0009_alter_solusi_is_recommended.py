# Generated by Django 5.1.6 on 2025-03-29 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expert_system_app', '0008_alter_solusi_is_recommended'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solusi',
            name='is_recommended',
            field=models.BooleanField(default=True),
        ),
    ]
