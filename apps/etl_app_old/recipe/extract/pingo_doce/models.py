import pickle
from datetime import datetime

from flask_marshmallow import Marshmallow
from marshmallow import fields, pre_dump, EXCLUDE
from peewee import  Model, CharField, BlobField, ForeignKeyField, FloatField, DateTimeField, ManyToManyField,DatabaseProxy


ma = Marshmallow()


class IngredientSchema(ma.Schema):
    name = fields.String(required=True)
    quantity = fields.String(required=True)


class PreparationSchema(ma.Schema):
    step = fields.Integer(required=True)
    description = fields.String(required=True)


""" Goodbites server """


class IngredientServerSchema(ma.Schema):
    name = fields.String(required=True)


class IngredientQuantityServerSchema(ma.Schema):
    ingredient = fields.Nested(IngredientServerSchema, required=True)
    quantity_original = fields.String(required=True)
    quantity_normalized = fields.Float(required=False, default=None)


class PreparationServerSchema(ma.Schema):
    step = fields.Integer(required=True)
    description = fields.String(required=True)


class NutritionInformationServerSchema(ma.Schema):
    energia = fields.String(required=True)
    energia_perc = fields.String()
    gordura = fields.String(required=True)
    gordura_perc = fields.String()
    gordura_saturada = fields.String(required=True)
    gordura_saturada_perc = fields.String()
    hidratos_carbonos = fields.String(required=True)
    hidratos_carbonos_perc = fields.String(null=True)
    hidratos_carbonos_acucares = fields.String(required=True)
    hidratos_carbonos_acucares_perc = fields.String()
    fibra = fields.String(required=True)
    fibra_perc = fields.String()
    proteina = fields.String(required=True)
    proteina_perc = fields.String(null=True)

    class Meta:
        unknown = EXCLUDE


class TagSchema(ma.Schema):
    title = fields.String(required=True)


class RecipeSchema(ma.Schema):
    title = fields.String(required=True)
    description = fields.String(required=True)
    img_source = fields.String(required=False, default="")
    verified = fields.Boolean(required=True,default=True)

    difficulty = fields.String(required=False)
    portion = fields.String(required=False)
    time = fields.String(required=False)

    ingredients = fields.Nested(IngredientQuantityServerSchema, required=True, many=True)
    preparation = fields.Nested(PreparationSchema, required=True, many=True)
    nutrition_information = fields.Nested(NutritionInformationServerSchema, null=True)
    tags = fields.Nested(TagSchema, many=True)

    source_rating = fields.String(required=False)
    source_link = fields.String(required=False)
    company = fields.String(required=False)


    class Meta:
        ordered = True
        unknown = EXCLUDE

    @pre_dump
    def unlist(self, data, **kwargs):
        # decode blob
        if data.preparation:
            data.preparation = pickle.loads(data.preparation)

        data.comments = 0
        return data
    



""" Models """

database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy


class NutritionInformation(BaseModel):
    energia = CharField(default="")
    energia_perc = CharField(default="")
    gordura = CharField(default="")
    gordura_perc = CharField(default="")
    gordura_saturada = CharField(default="")
    gordura_saturada_perc = CharField(default="")
    hidratos_carbonos = CharField(default="")
    hidratos_carbonos_perc = CharField(default="")
    hidratos_carbonos_acucares = CharField(default="")
    hidratos_carbonos_acucares_perc = CharField(default="")
    fibra = CharField(default="")
    fibra_perc = CharField(default="")
    proteina = CharField(default="")
    proteina_perc = CharField(default="")

    class Meta:
        db_table = 'nutrition_information'


class Recipe(BaseModel):
    company = CharField()
    title = CharField(null=False)
    description = CharField(null=False)
    img_source = CharField(null=True)

    difficulty = CharField(null=True)
    portion = CharField(null=True)
    time = CharField(null=True)

    preparation = BlobField(null=False)
    nutrition_information = ForeignKeyField(NutritionInformation, backref='recipe', null=True, on_delete='CASCADE')

    source_rating = FloatField(null=True)
    source_link = CharField(null=True)

    created_date = DateTimeField(default=datetime.now(), null=False)
    updated_date = DateTimeField(default=datetime.now(), null=False)


class Ingredient(BaseModel):
    name = CharField(null=False, unique=True)


class IngredientQuantity(BaseModel):
    ingredient = ForeignKeyField(Ingredient, backref="ingredient_base")
    recipe = ForeignKeyField(Recipe, backref="ingredients")
    quantity_original = CharField(null=False)

    class Meta:
        db_table = 'recipe_ingredient_quantity'



class Tag(BaseModel):
    title = CharField(null=False, unique=True)
    recipes = ManyToManyField(Recipe, backref='tags')


class Recipe_links(BaseModel):
    link = CharField()
    page = CharField()
    base_search_link = CharField()
    image_link = CharField()

    class Meta:
        db_table = 'recipe_links'

