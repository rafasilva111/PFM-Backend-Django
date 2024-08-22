# Generated by Django 5.0 on 2024-08-16 18:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar_app', '0002_calendarentry_created_at_calendarentry_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendarentry',
            name='tag',
            field=models.CharField(choices=[('Breakfast', 'Pequeno Almoço'), ('Morning Snack', 'Lanche da manhã'), ('Lunch', 'Almoço'), ('Afternoon Snack', 'Lanche da tarde'), ('Dinner', 'Jantar'), ('Supper', 'Ceia'), ('Other', 'Other')], default='Other', max_length=15),
        ),
    ]
