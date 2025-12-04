
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

def fraction_to_decimal(match):
        numerator, denominator = map(int, match.groups())
        return str(numerator / denominator)  # Convert fraction to decimal
    
def convert_fractions(text: str):
    return re.sub(r'(\d+)/(\d+)', fraction_to_decimal, text)

def remove_multiple_spaces(text: str):
    return re.sub(r'\s+', ' ', text)

def contains_numbers(input_string):
    return bool(re.search(r'\d', input_string))