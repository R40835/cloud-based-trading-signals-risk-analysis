import json
import time
import random

start = time.time()


def lambda_handler(event, context):
    mean = float(event['mean'])
    std = float(event['std'])
    shots = int(event['shots'])
    
    simulated = [random.gauss(mean,std) for x in range(shots)]
    simulated.sort(reverse=True)
    var95 = simulated[int(len(simulated)*0.95)]
    var99 = simulated[int(len(simulated)*0.99)]
    
    var = {
        'var95': var95,
        'var99': var99,
    }
    return var