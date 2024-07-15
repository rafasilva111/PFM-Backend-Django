
from enum import Enum

class RECIPES_SORTING_TYPE(Enum):
    VERIFIED = "VERIFIED"
    DATE = "DATE"
    LIKES = "LIKES"
    SAVES = "SAVES"
    RANDOM = "RANDOM"
    CLASSIFICATION = "CLASSIFICATION"

# Creating a set of the values of the enum
RECIPES_SORTING_TYPE_SET = [item.value for item in RECIPES_SORTING_TYPE]


class RECIPES_BACKGROUND_TYPE(Enum):
    LIKED = "L"
    SAVED = "S"

# Creating a set of the values of the enum
RECIPES_BACKGROUND_TYPE_SET = [item.value for item in RECIPES_BACKGROUND_TYPE]