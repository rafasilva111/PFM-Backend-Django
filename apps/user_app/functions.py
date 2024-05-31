from .constants import NORMAL_WEIGHT_BMI_LOWER_LIMIT,NORMAL_WEIGHT_BMI_UPPER_LIMIT

def calculate_bmi(weight_kg, height_cm):
    height_m_squared = (height_cm/100)** 2
    bmi = weight_kg / height_m_squared
    return  round(bmi, 2),round(height_m_squared * NORMAL_WEIGHT_BMI_LOWER_LIMIT, 2),round(height_m_squared * NORMAL_WEIGHT_BMI_UPPER_LIMIT, 2) 


