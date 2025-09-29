import re


# Regular expression pattern for separating quantity, unit, and ingredient
pattern = re.compile(r'(\d+)\s*(c\. [a-zA-Z]+|c\. sopa|c\. chá|ml|g)?\s*(.*)')

# Function to separate elements
def separate_unit_title(title):
    match = pattern.match(title)
    if match:
        quantity = match.group(1)
        unit = match.group(2)
        ingredient = match.group(3)
        return quantity, unit, ingredient
    else:
        return None

