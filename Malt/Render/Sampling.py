import math

import random
#Don't share state
random = random.Random()

#Rotated Grid Super Sampling pattern
#https://en.wikipedia.org/wiki/Supersampling#Rotated_grid
def get_RGSS_samples(grid_size, width=1.0):
    samples = []
    for x in range(0, grid_size):
        for y in range(0, grid_size):
            _x = (x / grid_size) * 2.0 - 1.0 #(-1 ... +1 range)
            _y = (y / grid_size) * 2.0 - 1.0 #(-1 ... +1 range)

            angle = math.atan(1/2)
            sin = math.sin(angle)
            cos = math.cos(angle)
            r_x = _x * cos - _y * sin
            r_y = _x * sin + _y * cos
            
            scale = math.sqrt(5)/2
            r_x *= scale
            
            #discard samples where radius > 1
            if r_x * r_x + r_y * r_y <= 1:
                r_x *= width
                r_y *= width
                samples.append((r_x,r_y))

    random.seed(0)
    #randomize the sampling order to get better early results
    samples = sorted(samples, key=lambda k: random.random())

    #Make sure there's at least one sample
    if len(samples) == 0:
        samples = [(0,0)]

    return samples
    

#Random sampling. Best results at high sample counts
def get_random_samples(grid_size, width=1.0):
    random.seed(0)
    samples = []
    for _ in range(0, grid_size * grid_size):
        x = 2
        y = 2

        #discard samples where radius > 1
        while x**2 + y**2 > 1.0:
            x = random.random() * 2.0 - 1.0 #(-1 ... +1 range)
            y = random.random() * 2.0 - 1.0 #(-1 ... +1 range)

        x *= width
        y *= width

        samples.append((x,y))

    #Make sure there's at least one sample
    if not samples:
        samples = [(0,0)]

    return samples
