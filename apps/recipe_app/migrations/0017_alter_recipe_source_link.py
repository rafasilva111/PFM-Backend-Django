# Generated by Django 5.0 on 2024-07-15 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipe_app', '0016_alter_recipe_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='source_link',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
    ]
