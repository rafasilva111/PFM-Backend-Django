# Generated by Django 5.0 on 2024-07-11 16:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('etl_app', '0018_remove_job_task_job_last_run_task_job'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='name',
        ),
    ]
