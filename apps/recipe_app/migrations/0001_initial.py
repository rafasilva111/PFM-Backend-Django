# Generated by Django 3.2.6 on 2024-05-13 14:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='NutritionInformation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('energia', models.FloatField()),
                ('energia_perc', models.FloatField()),
                ('gordura', models.FloatField()),
                ('gordura_perc', models.FloatField()),
                ('gordura_saturada', models.FloatField()),
                ('gordura_saturada_perc', models.FloatField()),
                ('hidratos_carbonos', models.FloatField()),
                ('hidratos_carbonos_perc', models.FloatField(null=True)),
                ('hidratos_carbonos_acucares', models.FloatField()),
                ('hidratos_carbonos_acucares_perc', models.FloatField(null=True)),
                ('fibra', models.FloatField()),
                ('fibra_perc', models.FloatField()),
                ('proteina', models.FloatField()),
                ('proteina_perc', models.FloatField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
                ('img_source', models.CharField(max_length=255, null=True)),
                ('verified', models.BooleanField(default=False)),
                ('difficulty', models.CharField(max_length=255, null=True)),
                ('portion', models.CharField(max_length=255, null=True)),
                ('time', models.CharField(max_length=255, null=True)),
                ('views', models.IntegerField(default=0)),
                ('preparation', models.BinaryField()),
                ('source_rating', models.FloatField(null=True)),
                ('source_link', models.CharField(max_length=255, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_recipes', to=settings.AUTH_USER_MODEL)),
                ('nutrition_information', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recipe', to='recipe_app.nutritioninformation')),
            ],
            options={
                'ordering': ['-views'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('recipes', models.ManyToManyField(related_name='tags', to='recipe_app.Recipe')),
            ],
        ),
        migrations.CreateModel(
            name='RecipeReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.CharField(max_length=255)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='recipe_app.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_reports', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RecipeRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(null=True)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='recipe_app.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rated_recipes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RecipeIngredientQuantity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_original', models.CharField(max_length=255)),
                ('quantity_normalized', models.FloatField(null=True)),
                ('units_normalized', models.CharField(default='G', max_length=255)),
                ('extra_quantity', models.FloatField(null=True)),
                ('extra_units', models.CharField(max_length=255, null=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredient_base', to='recipe_app.ingredient')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients', to='recipe_app.recipe')),
            ],
        ),
        migrations.CreateModel(
            name='RecipeBackground',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=255)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backgrounds', to='recipe_app.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('parent_comment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='recipe_app.comment')),
                ('recipe', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='recipe_app.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL)),
                ('users_likes', models.ManyToManyField(related_name='comment_likes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
