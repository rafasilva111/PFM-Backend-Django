# Generated by Django 5.0 on 2024-07-17 18:21

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_app', '0003_company_user_account'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='age',
        ),
        migrations.AlterField(
            model_name='user',
            name='birth_date',
            field=models.DateTimeField(default=datetime.datetime(2024, 7, 17, 18, 21, 22, 687841, tzinfo=datetime.timezone.utc)),
            preserve_default=False,
        ),
    ]
