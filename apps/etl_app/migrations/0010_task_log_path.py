# Generated by Django 5.0 on 2024-06-20 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl_app', '0009_alter_task_max_records'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='log_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
