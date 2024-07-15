# Generated by Django 4.2.9 on 2024-05-31 18:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipe_app', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recipe',
            name='preparation',
        ),
        migrations.AddField(
            model_name='recipe',
            name='likes',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='recipe',
            name='rating',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipes_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Preparation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step', models.IntegerField()),
                ('description', models.CharField(max_length=255)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preparation', to='recipe_app.recipe')),
            ],
        ),
    ]
