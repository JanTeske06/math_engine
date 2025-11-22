import decimal


#from ..plugin_manager import BasePlugin
# from abc import ABC, abstractmethod
#
#
#
#
class Hallo(BasePlugin):
    name = "Hallo"
    def __init__(self):
        pass

    def register_function(self):
        return {
                "function"              : "ln",            # required to be in brackets, e.g. : ln(1) and must be string
                "number_of_parameters"  : 2,                # Only whole numbers 0 <= allowed
                "type"                  : decimal.Decimal,              # String, Decimal, Bool, int or float
                "divided_by"            : ",",              # Default is ',', but can be adjusted, except '(' or ')'
                "implementation_class"  : Hallo             # Name of ur Class
                                                        }
    def execute(self, problem):
        pass