# Generated by Django 5.0 on 2024-07-20 16:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopping_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shoppingingredient',
            name='shopping_list',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shopping_ingredients', to='shopping_app.shoppinglist'),
        ),
    ]
