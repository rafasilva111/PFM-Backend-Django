# Generated by Django 5.0 on 2024-07-28 18:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('group_app', '0002_group_admin_group_owner'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='admin',
            new_name='admins',
        ),
    ]
