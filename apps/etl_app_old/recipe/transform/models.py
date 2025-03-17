from datetime import datetime

from peewee import  Model, CharField, BooleanField, IntegerField, BlobField, ForeignKeyField, FloatField, \
    DateTimeField, ManyToManyField,DatabaseProxy

from apps.etl_app.constants import main_db


database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy


class NutritionInformation(BaseModel):
    energia = CharField(null = True)
    energia_perc = CharField(null = True)
    gordura = CharField(null = True)
    gordura_perc = CharField(null = True)
    gordura_saturada = CharField(null = True)
    gordura_saturada_perc = CharField(null = True)
    hidratos_carbonos = CharField(null = True)
    hidratos_carbonos_perc = CharField(null = True)
    hidratos_carbonos_acucares = CharField(null = True)
    hidratos_carbonos_acucares_perc = CharField(null = True)
    fibra = CharField(null = True)
    fibra_perc = CharField(null = True)
    proteina = CharField(null = True)
    proteina_perc = CharField(null = True)

    class Meta:
        db_table = 'nutrition_information'


class Ingredient(BaseModel):
    name = CharField(null=False, unique=True)





class Recipe(BaseModel):
    title = CharField(null=False)
    description = CharField(null=False)
    img_source = CharField(null=True)
    verified = BooleanField(default=True)

    difficulty = CharField(null=True)
    portion = CharField(null=True)
    time = CharField(null=True)

    

    nutrition_information = ForeignKeyField(NutritionInformation, backref='recipe', null=True, on_delete='CASCADE')

    source_rating = FloatField(null=True)
    source_link = CharField(null=True)

    is_valid = BooleanField(default=True)

    company = CharField(null=False)
    created_date = DateTimeField(default=datetime.now(), null=False)
    updated_date = DateTimeField(default=datetime.now(), null=False)


class Preparation(BaseModel):
    
    step = CharField()
    description = CharField()
    recipe = ForeignKeyField(Recipe, backref='preparation', null=True, on_delete='CASCADE')


    class Meta:
        db_table = 'preparation'

class Tag(BaseModel):
    title = CharField(null=False, unique=True)
    recipes = ManyToManyField(Recipe, backref='tags')


class IngredientQuantity(BaseModel):
    
    quantity_original = CharField(null=False)

    quantity_normalized = FloatField(null=True)
    units_normalized = CharField(null=True)
    extra_quantity = FloatField(null=True)
    extra_units = CharField(null=True)

    ingredient = ForeignKeyField(Ingredient, backref='ingredient_base')
    recipe = ForeignKeyField(Recipe, backref='ingredients', on_delete='CASCADE', null=False)

    class Meta:
        db_table = 'ingredient_quantity'


from marshmallow import Schema, fields, EXCLUDE, pre_dump
from datetime import datetime
import pickle

# Assuming NutritionInformationSchema is defined somewhere
# from yourmodule import NutritionInformationSchema

class NutritionInformationSchema(Schema):
    energia = fields.Float(required=True,null = True)
    energia_perc = fields.Float(null = True)
    gordura = fields.Float(required=True,null = True)
    gordura_perc = fields.Float(null = True)
    gordura_saturada = fields.Float(required=True,null = True)
    gordura_saturada_perc = fields.Float(null = True)
    hidratos_carbonos = fields.Float(required=True)
    hidratos_carbonos_perc = fields.Float(null = True)
    hidratos_carbonos_acucares = fields.Float(required=True,null = True)
    hidratos_carbonos_acucares_perc = fields.Float(null = True)
    fibra = fields.Float(required=True,null = True)
    fibra_perc = fields.Float(null = True)
    proteina = fields.Float(required=True,null = True)
    proteina_perc = fields.Float(null = False)

    class Meta:
        unknown = EXCLUDE

class PreparationSchema(Schema):
    step = fields.Integer(required=True)
    description = fields.String(required=True)

    class Meta:
        unknown = EXCLUDE

class TagSchema(Schema):
    title = fields.String(required=True)

class IngredientServerSchema(Schema):
    name = fields.String(required=True)


class IngredientQuantityServerSchema(Schema):
    ingredient = fields.Nested(IngredientServerSchema, required=True)
    quantity_original = fields.String(required=True)
    quantity_normalized = fields.Float(required=False, default=None)
    units_normalized = fields.String(required=True)

class RecipeSchema(Schema):
    title = fields.String(required=True)
    description = fields.String(required=True)
    img_source = fields.String(allow_none=True)
    verified = fields.Boolean(missing=True)

    difficulty = fields.String(allow_none=True)
    portion = fields.String(allow_none=True)
    time = fields.String(allow_none=True)

    ingredients = fields.Nested(IngredientQuantityServerSchema, required=True, many=True)
    preparation = fields.Nested(PreparationSchema, required=True, many=True)
    nutrition_information = fields.Nested(NutritionInformationSchema, null=True)
    tags = fields.Nested(TagSchema, many=True)

    rating = fields.Float(missing=0.0)
    source_rating = fields.Float(allow_none=True)
    source_link = fields.String(allow_none=True)

    is_valid = fields.Boolean(missing=True)

    company = fields.String(required=True)
    created_date = fields.DateTime(default=datetime.now, required=True)
    updated_date = fields.DateTime(default=datetime.now, required=True)

    class Meta:
        ordered = True
        unknown = EXCLUDE

