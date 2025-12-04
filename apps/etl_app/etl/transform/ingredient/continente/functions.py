from apps.etl_app.etl.transform.recipe.continente.utils import convert_fractions, remove_special_characters,\
    remove_fraction_characters, remove_multiple_spaces, contains_numbers
    
import re
import traceback
import math
from fractions import Fraction

general_units = (
    r"kg|g|ml|dl|cl|l|lt|L|c\. de sopa|c\. de chá|c\. de café|c\. de sobremesa|cháv\."
    r"|folhas|folha|dentes|dente|pacotes|pacote|embalagens|embalagem|garrafas|garrafa"
)

def repair_with_language_model(s: str):
    if "�" not in s:
        return s
    
    from symspellpy import SymSpell, Verbosity
    from django.conf import settings

    # Criar SymSpell
    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

    # Carregar dicionário português (word frequency list)
    sym_spell.load_dictionary(f"{settings.BASE_DIR}/pt_freq_dictionary.txt", term_index=0, count_index=1)

    # Corrigir palavra
    term = "M�nima"
    suggestions = sym_spell.lookup(term, Verbosity.CLOSEST, max_edit_distance=2)
    print(suggestions[0].term) 


     
def normalize_size(ingredient):
    size = ingredient.size

    portions = None
    portion_unit = None
    portion_size = None
    portion_price = ingredient.price_per_unit

    bulk_price = ingredient.price_bulk
    bulk_unit = ingredient.bulk_unit

    size_type = None
    minimum_size_for_bulk = None

    # Clean up size string
    if size:
        size = size.replace("  ", " ")
        if " x " in size and " un x " not in size:
            size = size.replace(" x ", " un x ")
        if " (aprox.)" in size:
            size = size.replace(" (aprox.)", "")
        if " (Leve 3 pague 2)" in size:
            size = size.replace(" (Leve 3 pague 2)", "")
        # Add space after 'emb.' if needed
        size = re.sub(r"(emb\.)(\d+(\.\d+)?\s+gr)", r"\1 \2", size)
        if "emb. " in size:
            size = size.replace("emb. ", "")

    # Clean up price
    if portion_price and "€" in portion_price:
        portion_price = portion_price.replace("€", "").strip()

    # Swap prices if unit is "un"
    if bulk_unit == "un":
        bulk_price, portion_price = portion_price, bulk_price
        bulk_unit = "kg"

    # BULK
    if size and "Quant. Mínima = " in size:
        minimum_size_for_bulk = size.replace("Quant. Mínima = ", "")
        size_type = Ingredient.SizeType.BULK
        size = None
        return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    # PACKAGE
    size_type = Ingredient.SizeType.PACKAGE

    if size and " un x " in size:
        bonus_size = 0
        bonus_unit = None

        if " (" in size and "gr (" not in size:
            size = size.replace(" (", "gr (")

        # Pattern: + <number> <unit> GRÁTIS
        pattern_bonus = re.compile(
            r'\+\s*(?P<bonus_size>\d+(?:[.,]\d+)?)\s*(?P<bonus_unit>[a-zA-Z]+)\s*GRÁTIS',
            re.IGNORECASE
        )
        match_bonus = pattern_bonus.search(size)
        if match_bonus:
            bonus_size = float(match_bonus.group('bonus_size').replace(',', '.'))
            bonus_unit = match_bonus.group('bonus_unit')

        # Pattern: <number> un x <number> <unit> (<number> <unit>)
        pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\s*x\s*'
            r'(?P<unit_size>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Z]+)\s*'
            r'\(\s*(?P<total_size>\d+(?:[.,]\d+)?)\s*(?P<total_unit>[a-zA-Z]+)\s*\)',
            re.IGNORECASE
        )
        matches = pattern.search(size)
        if matches:
            portions = float(matches.group('units').replace(',', '.'))
            portion_size = float(matches.group('unit_size').replace(',', '.'))
            portion_unit = matches.group('unit')
            size = f"{matches.group('total_size')} {matches.group('total_unit')}"

            if bonus_size > 0 and bonus_unit:
                if bonus_unit == "un":
                    total_portions = portions + bonus_size
                    size = f"{total_portions * portion_size} {portion_unit}"
                elif portion_unit == bonus_unit:
                    total_size = (portions * portion_size) + bonus_size
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "gr" and bonus_unit == "kg":
                    total_size = (portions * portion_size) + (bonus_size * 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "kg" and bonus_unit == "gr":
                    total_size = (portions * portion_size) + (bonus_size / 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "ml" and bonus_unit == "l":
                    total_size = (portions * portion_size) + (bonus_size * 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "l" and bonus_unit == "ml":
                    total_size = (portions * portion_size) + (bonus_size / 1000)
                    size = f"{total_size} {portion_unit}"
            else:
                size = f"{portions * portion_size} {portion_unit}"

            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

        # Pattern: <number> un x <number> <unit>
        pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\s*x\s*'
            r'(?P<unit_size>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Z]+)\s*',
            re.IGNORECASE
        )
        matches = pattern.search(size)
        if matches:
            portions = int(float(matches.group('units')))
            portion_size = float(matches.group('unit_size'))
            portion_unit = matches.group('unit')

            if bonus_size > 0 and bonus_unit:
                if bonus_unit == "un":
                    portions += bonus_size
                    size = f"{portions * portion_size} {portion_unit}"
                elif portion_unit == bonus_unit:
                    total_size = (portions * portion_size) + bonus_size
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "gr" and bonus_unit == "kg":
                    total_size = (portions * portion_size) + (bonus_size * 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "kg" and bonus_unit == "gr":
                    total_size = (portions * portion_size) + (bonus_size / 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "ml" and bonus_unit == "l":
                    total_size = (portions * portion_size) + (bonus_size * 1000)
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "l" and bonus_unit == "ml":
                    total_size = (portions * portion_size) + (bonus_size / 1000)
                    size = f"{total_size} {portion_unit}"
            else:
                size = f"{portions * portion_size} {portion_unit}"

            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    if size and " = " in size:
        pattern = re.compile(
            r'^\s*(\d+(?:/\d+)?)\b.*?=\s*([\d]+(?:[.,]\d+)?)\s*([a-zA-Z]+)',
            re.IGNORECASE
        )
        matches = pattern.search(size)
        if matches:
            portions = float(Fraction(matches.group(1))) if '/' in matches.group(1) else float(matches.group(1))
            size = f"{matches.group(2)} {matches.group(3)}"

    if size and " un)" in size:
        matches = re.search(r'\((\d+)\s*un\)', size)
        if matches:
            portions = matches.group(1)
            size = size.replace(f" ({portions} un)", "")

    # Pattern: <number> un (<number> <unit>)
    if size and " un (" in size:
        pattern = re.compile(
            r'(\d+)\s*un\s*\(\s*([\d.,]+)\s*([a-zA-Z]+)\s*\)',
            re.IGNORECASE
        )
        matches = pattern.search(size)
        if matches:
            portions = matches.group(1)
            size = f"{matches.group(2)} {matches.group(3)}"
            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    # Pattern: <number> un
    if size and " un" in size:
        pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\b',
            re.IGNORECASE
        )
        match = pattern.search(size)
        if match:
            portions = float(match.group('units').replace(',', '.'))
            size = None
            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    if size and " doses)" in size:
        matches = re.search(r'\((\d+)\s*doses\)', size)
        if matches:
            portions = matches.group(1)
            size = size.replace(f" ({portions} doses)", "")

    # Pattern: <number> <unit> + <number> <unit> GRÁTIS
    if size and " + " in size and "GRÁTIS" in size:
        pattern = re.compile(
            r'(?P<main_size>\d+(?:[.,]\d+)?)\s*(?P<main_unit>[a-zA-Z]+)\s*\+\s*'
            r'(?P<bonus_size>\d+(?:[.,]\d+)?)\s*(?P<bonus_unit>[a-zA-Z]+)\s*GRÁTIS',
            re.IGNORECASE
        )
        match = pattern.search(size)
        if match:
            main_size = float(match.group('main_size').replace(',', '.'))
            main_unit = match.group('main_unit')
            bonus_size = float(match.group('bonus_size').replace(',', '.'))
            bonus_unit = match.group('bonus_unit')
            if main_unit == bonus_unit:
                total_size = main_size + bonus_size
                size = f"{total_size} {main_unit}"
            else:
                if main_unit == "kg" and bonus_unit == "g":
                    total_size = main_size + (bonus_size / 1000)
                    size = f"{total_size} {main_unit}"
                elif main_unit == "g" and bonus_unit == "kg":
                    total_size = (main_size / 1000) + bonus_size
                    size = f"{total_size} {bonus_unit}"
            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    # Pattern: <number> <unit> + <number>% GRÁTIS
    if size and " + " in size and "% GRÁTIS" in size:
        pattern_percent = re.compile(
            r'(?P<main_size>\d+(?:[.,]\d+)?)\s*'
            r'(?P<main_unit>[a-zA-Z]+)\s*\+\s*'
            r'(?P<bonus_percent>\d+(?:[.,]\d+)?)%\s*GRÁTIS',
            re.IGNORECASE
        )
        match = pattern_percent.search(size)
        if match:
            main_size = float(match.group('main_size').replace(',', '.'))
            bonus_percent = float(match.group('bonus_percent').replace(',', '.'))
            total_size = math.floor(main_size * (1 + bonus_percent / 100))
            size = f"{total_size} {match.group('main_unit')}"
            return True, (size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk)

    # If nothing matched, return as invalid
    return False, (None, None, None, None, None, None, None, None, None)



def normalize_quantity(logger, task, quantity_original: str):
    """
    Normalize a quantity string by sanitizing it, extracting its components, 
    and converting it into a structured format.

    Args:
        logger: Logger object for logging errors and debugging information.
        quantity_original (str): The original quantity string to be normalized.

    Returns:
        tuple: A tuple containing:
            - quantity_tempered (str): The sanitized and normalized quantity string.
            - units (str or None): The unit of measurement (e.g., "g", "ml", etc.).
            - value (float or None): The numeric value of the quantity.
            - extra_units (str or None): Additional units if applicable.
            - extra_value (float or None): Additional values if applicable.
            - ingredient (str or None): The ingredient name or description.
    """
   
    units = None
    value = None
    extra_units = None
    extra_value = None
    ingredient = None
    

    ##
    #   1 - String Sanitation
    #
    ##

    # Remove leading and trailing spaces
    quantity_tempered = quantity_original.strip()
    
    # Replace multiple spaces with a single space
    quantity_tempered = remove_multiple_spaces(quantity_tempered)
    
    # Remove special characters like (±), ±, +-
    quantity_tempered = remove_special_characters(quantity_tempered)

    # Remove fraction characters like ½, 1⁄2, ¼
    quantity_tempered = remove_fraction_characters(quantity_tempered)

    # Convert fractions to decimal format
    quantity_tempered = convert_fractions(quantity_tempered)

    # Convert the string to lowercase for uniformity
    quantity_tempered = quantity_tempered.lower()
    
    
    # Replace specific patterns with normalized equivalents
    if "1 /2" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("1 /2", "0.5")
    if "1/2" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("1/2", "0.5")
    if "1/4" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("1/4", "0.25")
    if "1/3" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("1/3", "0.33")
    if "1/8" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("1/8", "0.125")

    # Normalize common abbreviations and terms
    if "cha " in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("cha", "chá")
    if "cafe " in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("cafe", "café")
    if "qb" in quantity_tempered:                                 # Q.b.
        quantity_tempered = quantity_tempered.replace("qb", "q.b.")
    if "q. b." in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("q. b.", "q.b.")
    if "q.b" in quantity_tempered and 'q.b.' not in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("q.b", "q.b.")
    if "qb." in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("qb.", "q.b.")
    if "a gosto" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("a gosto", "q.b.")
    if "c.es" in quantity_tempered:                                 # C.
        quantity_tempered = quantity_tempered.replace("c.es", "c.")
    if "colher" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("colher", "c.")
    if "c.sopa" in quantity_tempered:                                 # C. de Sopa
        quantity_tempered = quantity_tempered.replace("c.sopa", "c. de sopa")
    if "c.de sopa" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("c.de sopa", "c. de sopa")
    if "c. (de sopa)" in quantity_tempered:                                               
        quantity_tempered = quantity_tempered.replace("c. (de sopa)", "c. de sopa")
    if "c.café" in quantity_tempered:                                               # C. de café
        quantity_tempered = quantity_tempered.replace("c.café", "c. de café")
    if "c.de café" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("c.de café", "c. de café")
    if "chávena" in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("chávena", "cháv.")
    if "  " in quantity_tempered:
        quantity_tempered = quantity_tempered.replace("  ", " ")
    
    
    

    # Add spaces between numbers and units (e.g., "100g" -> "100 g")
    try:
        pattern = r'(\d+)(kg|g)'
        replacement = r'\1 \2'
        quantity_tempered = re.sub(pattern, replacement, quantity_tempered)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )

        return quantity_tempered, None, None, None, None, None

    # Add spaces between numbers and "c." (e.g., "2c." -> "2 c.")
    try:
        pattern = r'(\d+)c\.'
        replacement = r'\1 c.'
        quantity_tempered = re.sub(pattern, replacement, quantity_tempered)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    # Add spaces between numbers and volume units (e.g., "500ml" -> "500 ml")
    try:
        pattern = r'(\d+)(ml|l|lt|L|dl|cl)'
        replacement = r'\1 \2'
        quantity_tempered = re.sub(pattern, replacement, quantity_tempered)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    # Normalize "c. sopa", "c. chá", "c. café" patterns
    try:
        pattern = r'\bc\. (sopa|chá|café)\b'
        replacement = r'c. de \1'
        quantity_tempered = re.sub(pattern, replacement, quantity_tempered)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    ##
    #   2 - Patterns
    #
    ##

    # Handle ranges like "1 a 2"
    try:
        pattern = r'(\d+)\s+a\s+(\d+)'
        match = re.search(pattern, quantity_tempered, re.IGNORECASE)
        if match:
            lower = match.group(1)
            value = match.group(2)
            quantity_tempered.replace(f"{lower} a ", "")
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    # Extract numeric value, unit, and ingredient
    try:
        pattern = fr'(\d+(?:[.,]\d+)?)\s?({general_units})\s+(.*)'
        match = re.match(pattern, quantity_tempered)
        if match:
            value = str(match.group(1))
            units = match.group(2)
            ingredient = match.group(3)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None
    
    # Pattern for matching multiple quantities like "30 g + 140 g de açúcar"
    try:
        
        pattern = fr'(\d+(?:[.,]\d+)?)\s*({general_units})\s*\+\s*(\d+(?:[.,]\d+)?)\s*\2(?:\s+de\s+(.*))?'
        match = re.match(pattern, quantity_tempered)

        if match:
            num1 = float(match.group(1).replace(',', '.'))
            num2 = float(match.group(3).replace(',', '.'))
            unit = match.group(2)
            rest = match.group(4) or ""  # "de açúcar", "de água", etc.

            total = num1 + num2
            quantity_tempered = f"{total:.2f} {unit}"
            if quantity_tempered:
                quantity_tempered += f" de {rest}"

    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None
    
    # Pattern for matching "<number> + <number> <rest>"
    try:
        pattern = r'(\d+)\s*\+\s*(\d+)\s+(.*)'
        match = re.match(pattern, quantity_tempered)

        if match:
            num1 = int(match.group(1))
            num2 = int(match.group(2))
            rest = match.group(3)

            total = num1 + num2
            quantity_tempered =  f"{total} {rest}"

    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    # Handle "q.b." (quantity to taste)
    if not units and not value:
        if "q.b." in quantity_tempered:
            value = None
            units = "q.b."
            ingredient = quantity_tempered.replace("q.b.", "").strip()
            
            return quantity_tempered, units, value, extra_units, extra_value, ingredient

    # Handle phrases like "Sumo de 2 laranjas" or "Raspa de 1 limão"
    try:
        pattern = r'^(Sumo|Raspa).*?(\d+)\s+(.*)'
        match = re.match(pattern, quantity_tempered, re.IGNORECASE)
        if match:
            value = match.group(2)
            units = "unid."
            ingredient = match.group(3)
    except Exception as e:
        task.increment_errors(
            logger = logger,
            message = f"Error while processing: {quantity_original}  (Ingredient)",
            stack_trace=traceback.format_exc()
        )
        
        return quantity_tempered, None, None, None, None, None

    # Normalize numeric values and units
    if value and "," in value:
        value = value.replace(",", ".")
    if units == "kg":
        value = float(value) * 1000
        units = "g"
    elif units in ["l", "L", "lt"]:
        value = float(value) * 1000
        units = "ml"
    elif units == "dl":
        value = float(value) * 100
        units = "ml"
    elif units == "cl":
        value = float(value) * 10
        units = "ml"
    elif units == "folhas":
        units = "folha"
    elif units == "dentes":
        units = "dente"

    # Convert value to float if it exists
    if value:
        value = float(value)

    # Handle cases where no numeric value is present
    if not contains_numbers(quantity_tempered):
        value = None
        units = "q.b."
        ingredient = quantity_tempered.strip()

    # Handle cases where only a number and ingredient are present
    if not value and not units:
        try:
            pattern = r'^(\d+(?:[\.,]\d+)?)\s+(.*)$'
            match = re.match(pattern, quantity_tempered.strip())
            if match:
                value = match.group(1).replace(",", ".")
                units = "unid."
                ingredient = match.group(2).strip()
        except Exception as e:
            task.increment_errors(
                logger = logger,
                message = f"Error while processing: {quantity_original}  (Ingredient)",
                stack_trace=traceback.format_exc()
            )
            return quantity_tempered, None, None, None, None, None
    
    
    if ingredient:
        # Replace commas in the ingredient with spaces
        if "," in ingredient:
            ingredient = ingredient.replace(",", " ")

        # Remove "de " from the ingredient
        if "de " in ingredient:
            ingredient = ingredient.replace("de ", "")

    return quantity_tempered, units, value, extra_units, extra_value, ingredient




def normalize_portion(logger, portion: str):
    
    _portion = portion.strip()
    _portion_units = "pessoas"
    _portion_lower_bound = None
    _portion_upper_bound = None
    
    _portion = remove_multiple_spaces(_portion)
    
    if " - " in _portion:
        _portion = _portion.replace(" - ", " ")
    
    
    try:
        match = re.match(r'(\d+)-(\d+) pessoas', _portion)
    
        if match:
            _portion_lower_bound = int(match.group(1))  # First number is the lower bound
            _portion_upper_bound = int(match.group(2))  # Second number is the upper bound
            
    except Exception as e:
        logger.error(f"Error while processing: {portion} (_portion)")
        logger.error(e)
        return portion, _portion_units

    try:
        match = re.match(r'(\d+) pessoas', _portion)
    
        if match:
            _portion_lower_bound = int(match.group(1))

        
    except Exception as e:
        logger.error(f"Error while processing: {portion} (Portion)")
        logger.error(e)
        return portion, _portion_units

    return _portion_lower_bound, _portion_upper_bound, _portion_units

def normalize_time(logger, time: str):
    
    _time = time.strip()
    _time_units = "min"
    
    _time = remove_multiple_spaces(_time)
    
    try:
        match = re.match(r'(\d+) min', time)
    
        if match:
            # Convert the captured number to integer
            bound = int(match.group(1))  # Both bounds are the same in this case
            return bound, bound  # Return both bounds as the same number

    except Exception as e:
        logger.error(f"Error while processing: {time} (Time)")
        logger.error(e)
        return time, _time_units

    return _time, _time_units

