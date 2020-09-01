import re

class BlizzColors:
    """
    Simple wrapper to hold hexcolors of WoW's classes
    Attributes
    ----------
    class_hexcolor : dict
        dict containing class -> color map
   
    """

    def __init__(self):
        #raw data string from https://wow.gamepedia.com/Class_colors 
        data = """
            Death_Knight        196     31      59      0.77    0.12    0.23    #C41F3B Red_†
            Demon_Hunter        163     48      201     0.64    0.19    0.79    #A330C9 Dark_Magenta
            Druid       255     125     10      1.00    0.49    0.04    #FF7D0A Orange
            Hunter      169     210     113     0.67    0.83    0.45    #A9D271 Green
            Mage        64      199     235     0.25    0.78    0.92    #40C7EB Light_Blue
            Monk        0       255     150     0.00    1.00    0.59    #00FF96 Spring_Green
            Paladin     245     140     186     0.96    0.55    0.73    #F58CBA Pink
            Priest      255     255     255     1.00    1.00    1.00    #FFFFFF White*
            Rogue       255     245     105     1.00    0.96    0.41    #FFF569 Yellow*
            Shaman      0       112     222     0.00    0.44    0.87    #0070DE Blue
            Warlock     135     135     237     0.53    0.53    0.93    #8787ED Purple
            Warrior     199     156     110     0.78    0.61    0.43    #C79C6E Tan 
            """
        self.parse_colors(data)

    def parse_colors(self, data):
        """parse classes/colors mapping"""
        self.class_hexcolor = {}
        for line in data.split('\n'):
            line = line.strip()
            if re.match('\w', line):
                s = line.split()
                self.class_hexcolor[s[0].lower()] = s[-2] 
    
    def get_color(self, class_name):
        """returns hex color given class name"""
        return self.class_hexcolor[class_name.lower()]
