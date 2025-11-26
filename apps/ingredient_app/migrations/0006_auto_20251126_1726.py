











# Ingredient_app/migrations/0006_data_cleanup.py

from django.db import migrations

def set_empty_string_to_null(apps, schema_editor):
    """
    Sets any empty string values in the 'category' field to None (NULL)
    to prepare for conversion to JSONField.
    """
    Ingredient = apps.get_model('ingredient_app', 'Ingredient')
    # Use update() for performance and to avoid loading and saving every instance
    Ingredient.objects.filter(category='').update(category=None)

class Migration(migrations.Migration):

    dependencies = [
        # This dependency must point to the failed migration's number
        ('ingredient_app', '0005_tag_remove_ingredient_characteristics_and_more'),
    ]

    operations = [
        # The RunPython operation executes the function defined above
        migrations.RunPython(set_empty_string_to_null, 
                             reverse_code=migrations.RunPython.noop),
    ]
