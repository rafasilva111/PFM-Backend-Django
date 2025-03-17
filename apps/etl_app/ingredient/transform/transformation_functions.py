
import re
from apps.etl_app.constants import Measures

def remove_special_characters(quantity_original: str):
    
    # Remove (±) , ± , +-

    if "(±)" in quantity_original:
        
        quantity_original = quantity_original.replace("(±)", "").strip()
        
    if "±" in quantity_original:
        
        quantity_original = quantity_original.replace("±", "").strip()

    if "+-" in quantity_original:
        quantity_original = quantity_original.replace("+-", "").strip()
        
    return quantity_original
        
def remove_fraction_characters(quantity_original: str):
    
    # Remove fractions ½ , 1⁄2 , ¼, ⅓
    
    if "½" in quantity_original:
        quantity_original = quantity_original.replace("½", "0.5")
    
    elif "1⁄2" in quantity_original:
        quantity_original = quantity_original.replace("1⁄2", "0.5")
    
    elif "¼" in quantity_original:
        quantity_original = quantity_original.replace("¼", "0.25")

    elif "⅓" in quantity_original:
        quantity_original = quantity_original.replace("⅓", "0.25")

    else:
        return quantity_original

    helper = quantity_original.split(" ")
    
    try:
        value = float(helper[0]) + float(helper[1])
        quantity_original = f'{value} {" ".join(helper[2:])}'
    except ValueError:
        pass
    except IndexError:
        pass
    
    
    return quantity_original

unids_pattern_units = r'(\d+(\.\d+)?)\s*unid\.'
unids_pattern_units_grams = r'(\d+(\.\d+)?)\s*unid\.?\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*(?:[a-zA-Z]*)?\s*\)|(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+))'
unids_pattern_units_reverse = r'(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\(\s*(\d+(\.\d+)?)\s*unid\.?\s*\)'

def transform_unids(logger, quantity_original: str):
    
    if "unid." == quantity_original:
        quantity_original = "1 unid."
    
    if " unid " in quantity_original:
        quantity_original = quantity_original.replace("unid", "unid.")
    
    if "uni.)" in quantity_original:
        quantity_original = quantity_original.replace("uni.", "unid.")
    
    if "uni)" in quantity_original:
        quantity_original = quantity_original.replace("uni", " unid.)")

    match_reverse = re.search(unids_pattern_units_reverse, quantity_original)
    match_units = re.search(unids_pattern_units, quantity_original)
    match_grams = re.search(unids_pattern_units_grams, quantity_original)
    extra_value =  None
    extra_units = None
    units = None
    value = None

    if match_reverse  :
        extra_value = float(match_reverse.group(4))  # Extract the number of units (fourth group)
        extra_units = "unid."
        value = match_reverse.group(1)
        units = match_reverse.group(3)

    elif match_units:
        extra_value = float(match_units.group(1))  # Extract the number of units (first group)
        extra_units = "unid."
        units = None
        value = None

        if match_grams:
            if match_grams.group(3):  # If group 3 exists, the value is inside parentheses
                value = match_grams.group(3)
                units = match_grams.group(5)
            else:  # Otherwise, use group 6 and group 8
                value = match_grams.group(6)
                units = match_grams.group(8)
    else:
        logger.warning(f"Function {__name__} failed. Quantity {quantity_original} not transformed.")

    if not units and not value:
        value = extra_value
        units = extra_units
        extra_value = None
        extra_units = None
        

    return quantity_original, units, value, extra_value, extra_units


embs_pattern_embs = r'(\d+(\.\d+)?)\s*emb\.'
embs_pattern_embs_grams = r'(\d+(\.\d+)?)\s*emb\.?\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*(?:[a-zA-Z]*)?\s*\)|(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+))'
embs_pattern_embs_reverse = r'(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\(\s*(\d+(\.\d+)?)\s*emb\.?\s*\)'

def transform_embs(logger, quantity_original: str):
    match_reverse = re.search(embs_pattern_embs_reverse, quantity_original)
    match_units = re.search(embs_pattern_embs, quantity_original)
    match_grams = re.search(embs_pattern_embs_grams, quantity_original)
    extra_value =  None
    extra_units = None
    units = None
    value = None

    if quantity_original.startswith("emb."):
        quantity_original.replace("emb.","1 emb.")

    if match_reverse:
        value = match_reverse.group(1)
        units = match_reverse.group(3)
        extra_value = float(match_reverse.group(4))  # Extract the number of units (fourth group)
        extra_units = "emb."

    elif match_units:
        extra_value = float(match_units.group(1))  # Extract the number of units (first group)
        extra_units = "emb."
        units = None
        value = None

        if match_grams:
            if match_grams.group(3):  # If group 3 exists, the value is inside parentheses
                value = match_grams.group(3)
                units = match_grams.group(5)
            else:  # Otherwise, use group 6 and group 8
                value = match_grams.group(6)
                units = match_grams.group(8)

    else:
        logger.warning(f"Function {__name__} failed. Quantity {quantity_original} not transformed.")


    return quantity_original, units, value, extra_value, extra_units

pattern_soup_spoon_units = r'(\d+(\.\d+)?)\s*c\.?\s*de\s*sopa\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\))?'

pattern_soup_spoon_plus = r'(\d+)\s*c\. de sopa'


C_DE_SOPA = 20
def transform_soup_spoon(logger, quantity_original: str):
    # Define pattern for "c. de sopa" 
    value = None
    units = None
    extra_value = None
    extra_units = None

    extra_plus = None

    # Check if the string contains "+"
    if "+" in quantity_original:
        # Apply pattern for "c. de sopa" with "+"
        match_plus = re.findall(pattern_soup_spoon_plus, quantity_original)
        
        try:
            nr_soup_spoons = int(match_plus[0])
            extra_plus = quantity_original.replace(f"{int(match_plus[0])} c. de sopa", f"{nr_soup_spoons*Measures.SOUP_SPOON} g")  
        except:
            pass

        
    else:
        # Apply pattern for standalone "c. de sopa"
        match_units = re.match(pattern_soup_spoon_units, quantity_original)

        if match_units:
            extra_value = match_units.group(1)
            extra_units = "c. de sopa"
            value = float(match_units.group(1)) * C_DE_SOPA if match_units.group(1) == extra_value else None
            units = "g" if match_units.group(1) == extra_value else None




    return quantity_original, units, value, extra_units, extra_value, extra_plus

pattern_tea_spoon_units = r'(\d+(\.\d+)?)\s*c\.?\s*de\s*chá\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\))?'
pattern_tea_spoon_plus = r'(\d+(\.\d+)?)\s*c\.\s*de\s*chá'

def transform_tea_spoon(logger,quantity_original):

    value = None
    units = None
    extra_value = None
    extra_units = None
    extra_plus = None

    # Check if the string contains "+"
    if "+" in quantity_original:
        # Apply pattern for "c. de chá" with "+"
        match_plus = re.findall(pattern_tea_spoon_plus, quantity_original)
        try:
            nr_cha_spoons = float(match_plus[0][0])
            extra_plus = quantity_original.replace(f"{match_plus[0][0]} c. de chá", f"{nr_cha_spoons * Measures.TEA_SPOON} g")
        except:
            pass
    else:
        # Apply pattern for standalone "c. de chá"
        match_units = re.match(pattern_tea_spoon_units, quantity_original)

        if match_units:
            extra_value = match_units.group(1)
            extra_units = "c. de chá"
            value = float(match_units.group(1)) * Measures.TEA_SPOON
            units = "g"


    return quantity_original, units, value, extra_units, extra_value, extra_plus


pattern_desert_spoon_units = r'(\d+(\.\d+)?)\s*c\.?\s*de\s*sobremesa\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\))?'
pattern_desert_spoon_plus = r'(\d+(\.\d+)?)\s*c\.\s*de\s*sobremesa'

def transform_desert_spoon(logger,quantity_original):

    value = None
    units = None
    extra_value = None
    extra_units = None
    extra_plus = None

    # Check if the string contains "+"
    if "+" in quantity_original:
        # Apply pattern for "c. de sobremesa" with "+"
        match_plus = re.findall(pattern_desert_spoon_plus, quantity_original)
        try:
            nr_cha_spoons = float(match_plus[0][0])
            extra_plus = quantity_original.replace(f"{match_plus[0][0]} c. de sobremesa", f"{nr_cha_spoons * Measures.DESERT_SPOON} g")
        except:
            pass
    else:
        # Apply pattern for standalone "c. de sobremesa"
        match_units = re.match(pattern_desert_spoon_units, quantity_original)

        if match_units:
            extra_value = match_units.group(1)
            extra_units = "c. de sobremesa"
            value = float(match_units.group(1)) * Measures.DESERT_SPOON
            units = "g"


    return quantity_original, units, value, extra_units, extra_value, extra_plus


pattern_coffe_spoon_units = r'(\d+(\.\d+)?)\s*c\.?\s*de\s*café\s*(?:\(\s*(\d+(\.\d+)?|[\d\.\,]+)\s*([a-zA-Z]+)\s*\))?'
pattern_coffe_spoon_plus = r'(\d+(\.\d+)?)\s*c\.\s*de\s*café'

def transform_coffe_spoon(logger,quantity_original):

    value = None
    units = None
    extra_value = None
    extra_units = None
    extra_plus = None

    # Check if the string contains "+"
    if "+" in quantity_original:
        # Apply pattern for "c. de café" with "+"
        match_plus = re.findall(pattern_coffe_spoon_plus, quantity_original)
        try:
            nr_cha_spoons = float(match_plus[0][0])
            extra_plus = quantity_original.replace(f"{match_plus[0][0]} c. de café", f"{nr_cha_spoons * 5.69} g")
        except:
            pass
    else:
        # Apply pattern for standalone "c. de café"
        match_units = re.match(pattern_coffe_spoon_units, quantity_original)

        if match_units:
            extra_value = match_units.group(1)
            extra_units = "c. de café"
            value = float(match_units.group(1)) * 5.69
            units = "g"


    return quantity_original, units, value, extra_units, extra_value, extra_plus

pattern_general_number_units = r'(\d*\.?\d+)\s+(\w+)'

def transform_number(logger,quantity_original):

    units = None
    value = None
    

    match = re.match(pattern_general_number_units, quantity_original)
    if match:
        value, units = match.groups()

    return quantity_original, units, value