# Generated by Django 5.0 on 2024-07-03 18:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipe_app', '0013_remove_recipe_preparation_preparation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='preparation',
            old_name='recipes',
            new_name='recipe',
        ),
    ]
