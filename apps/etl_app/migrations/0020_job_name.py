# Generated by Django 5.0 on 2024-07-11 17:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl_app', '0019_remove_job_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='name',
            field=models.CharField(default='teste', max_length=255),
            preserve_default=False,
        ),
    ]
