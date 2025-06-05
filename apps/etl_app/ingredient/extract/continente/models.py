import pickle

from marshmallow import fields, pre_dump, EXCLUDE
from peewee import *



""" Models """

database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy
    

class Ingredient(BaseModel):
    # Geral
    title = CharField(default="")
    brand = CharField(default="")
    description = CharField(default="")
    link = CharField(default="")
    category = CharField(default="")

    # Size and money
    size = CharField(default="")
    price_per_unit = CharField(default="")
    price_bulk = CharField(default="")
    bulk_unit = CharField(default="")


    # About the Product
    about_the_product = CharField(default="")
    
    # Caracteristics
    caracteristics = CharField(default="")

    # Other Information
    other_information = CharField(default="")

    # Nutritional Information
    nutrition_information = CharField(default = "")
    
    # Legal Info
    legal_info = CharField(default="")


class Image(BaseModel):
    path = CharField(default="")
    ingredient = ForeignKeyField(Ingredient, backref='images', null=True, on_delete='CASCADE')

class Tag(BaseModel):
    title = CharField(null=False, unique=True)
    parent_tab = ForeignKeyField('self', backref='parent_tag', null=True, on_delete='CASCADE')
    recipe = ManyToManyField(Ingredient, backref='tags')


class IngredientLink(BaseModel):
    link = CharField()
    category = CharField()
    page = CharField()
    base_search_link = CharField()

    class Meta:
        db_table = 'ingredient_link'


IngredientTagThrough = Ingredient.tags.get_through_model()