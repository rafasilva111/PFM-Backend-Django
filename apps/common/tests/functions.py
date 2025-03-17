###
#       General imports
##

##
#   Extras
#

import inspect



def print_prologue():
    
    print("----------------------------------------------------------------------")
    print("\n")
    print(f"Running test: {inspect.currentframe().f_back.f_code.co_name}")
    print("\n")