# Color difference
def colorDifference(c1, c2):
    c1_p = split_rgb(c1) 
    c2_p = split_rgb(c2) 
    r_diff = max(c1_p[0], c2_p[0]) - min(c1_p[0], c2_p[0])
    g_diff = max(c1_p[1], c2_p[1]) - min(c1_p[1], c2_p[1])
    b_diff = max(c1_p[2], c2_p[2]) - min(c1_p[2], c2_p[2])
    return r_diff + g_diff + b_diff

# Brightness difference
def brightnessDifference(c1, c2):
    def brightness(c):
        (r,g,b) = split_rgb(c)
        return float(r*299+g*587+b*114)/1000
    return abs(brightness(c1) - brightness(c2))

# Relative luminance
def contrastRatio(c1, c2):

    def srgb(c):
        return float(c)/255
        
    def component_luminance(c):
        s = srgb(c)
        if s<= 0.03928:
            return s/12.92
        else:
            return ((s+0.055)/1.055) ** 2.4

    def relativeLuminance(c):
        (r,g,b) = split_rgb(c)
        r_cl = component_luminance(r)
        g_cl = component_luminance(g)
        b_cl = component_luminance(b)
        return 0.2126 * r_cl + 0.7152 * g_cl + 0.0722 * b_cl
        
    (l2, l1) = sorted([relativeLuminance(c1), relativeLuminance(c2)]) 
    
    return (l1 + 0.05) / (l2 + 0.05)

def checkColorAccessibility(c1, c2):
    cd = colorDifference(c1, c2)
    bd = brightnessDifference(c1, c2)
    cr = contrastRatio(c1, c2)
    
    return (bd >= 125 and cd >= 500 and cr >= 4.5)

#Split Hex color code into RGB components
def split_rgb(s):
    d = {}
    d['r'] = int(s[0:2], 16)
    d['g'] = int(s[2:4], 16)
    d['b'] = int(s[4:7], 16)
    return (d['r'], d['g'], d['b'])