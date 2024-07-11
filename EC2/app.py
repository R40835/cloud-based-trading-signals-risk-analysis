from flask import Flask, request, jsonify
import random

app = Flask(__name__)


@app.route('/calculate_var9599', methods=['POST'])
def calculate_var():
    data = request.json
    mean = float(data['mean'])
    std = float(data['std'])
    shots = int(data['shots'])
    
    simulated = [random.gauss(mean, std) for x in range(shots)]
    simulated.sort(reverse=True)
    var95 = simulated[int(len(simulated) * 0.95)]
    var99 = simulated[int(len(simulated) * 0.99)]
    
    var = {
        'var95': var95,
        'var99': var99
    }
    
    return jsonify(var)


if __name__ == '__main__':
    app.run(debug=True)