from apps.etl_app.recipe.transform.continente.utils import convert_fractions, remove_special_characters,\
    remove_fraction_characters, remove_multiple_spaces, contains_numbers
    
import re
import traceback

general_units = (
    r"kg|g|ml|dl|cl|l|lt|L|c\. de sopa|c\. de chá|c\. de café|c\. de sobremesa|cháv\."
    r"|folhas|folha|dentes|dente|pacotes|pacote|embalagens|embalagem|garrafas|garrafa"
)


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

