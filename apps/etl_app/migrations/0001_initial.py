# Generated by Django 5.0 on 2024-06-18 20:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(auto_now=True)),
                ('finished_at', models.DateTimeField(null=True)),
                ('type', models.CharField(choices=[('EXTRACT', 'Extract'), ('TRANSFORM', 'Transform'), ('LOAD', 'Load'), ('FULL_PROCESS', 'Full Process')], default=None, max_length=12, null=True)),
                ('status', models.CharField(choices=[('STARTING', 'Starting'), ('RUNNING', 'Running'), ('CANCELED', 'Canceled'), ('FAILED', 'Failed'), ('FINISHED', 'Finished')], default='STARTING', max_length=10)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
