# Generated by Django 5.0 on 2024-07-28 20:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group_app', '0003_rename_admin_group_admins'),
        ('shopping_app', '0005_delete_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='shoppinglist',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shopping_lists', to='group_app.group'),
        ),
    ]
