# Generated by Django 4.2.9 on 2024-06-01 22:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipe_app', '0009_alter_recipe_liked_clients_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recipe',
            old_name='liked_clients',
            new_name='users_liked',
        ),
        migrations.RenameField(
            model_name='recipe',
            old_name='saved_clients',
            new_name='users_saved',
        ),
    ]
