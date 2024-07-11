import os

from flask import Flask, request, render_template
from flask.json import jsonify

from analysis import Analyser
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
analyser = None


@app.route("/warmup", methods=['POST'])
def api_warmup():
    global analyser
    data = request.json
    analyser = Analyser(s=data.get('s'), r=int(data.get('r')))
    return {"result": "ok"}
    

@app.route("/scaled_ready", methods=['GET'])
def api_scaled_ready():
    global analyser
    if not analyser: 
        return {"warm": "false"} 
    if analyser.service_scaled_ready():
        return {"warm": "true"}
    return {"warm": "false"}


@app.route("/get_warmup_cost", methods=['GET'])
def api_get_warmup_cost():
    global analyser
    return analyser.get_warmup_cost


@app.route("/get_endpoints", methods=['GET'])
def api_get_endpoints():
    global analyser
    return analyser.get_endpoints


@app.route("/analyse", methods=['POST'])
def api_analyse():
    global analyser
    data = request.json
    analyser.analyse_risk(
        h=int(data.get('h')),
        d=int(data.get('d')),
        t=data.get('t'),
        p=int(data.get('p')),
    )
    return {"result": "ok"}


@app.route("/get_sig_vars9599", methods=['GET'])
def api_get_sig_vars9599():
    global analyser
    return analyser.get_var9599


@app.route("/get_avg_vars9599", methods=['GET'])
def api_get_avg_vars9599():
    global analyser
    return analyser.get_avg_var9599


@app.route("/get_sig_profit_loss", methods=['GET'])
def api_get_sig_profit_loss():
    global analyser
    return analyser.get_profit_loss


@app.route("/get_tot_profit_loss", methods=['GET'])
def api_get_tot_profit_loss():
    global analyser
    return analyser.get_tot_profit_loss


@app.route("/get_chart_url", methods=['GET'])
def api_get_chart_url():
    url = os.getenv('GAE_URL') + '/chart'
    return {"url": url}


@app.route("/get_time_cost", methods=['GET'])
def api_get_time_cost():
    global analyser
    return analyser.get_time_cost


@app.route("/get_audit", methods=['GET'])
def api_get_audit():
    return Analyser.get_audit()


@app.route("/reset", methods=['GET'])
def api_reset():
    global analyser
    analyser.reset()
    return {"result": "ok"}


@app.route("/terminate", methods=['GET'])
def api_terminate():
    global analyser
    analyser.terminate_service()
    return {"result": "ok"}


@app.route("/scaled_terminated", methods=['GET'])
def api_scaled_terminated():
    global analyser
    if analyser.service_terminated():
        return {"terminated": "true"}
    return {"terminated": "false"}


@app.route('/chart', methods=['GET'])
def view_chart():
    global analyser
    if analyser.analysis_complete:
        risk_var95s: list = analyser.get_var9599['var95']
        risk_var99s: list = analyser.get_var9599['var99']

        avg_risk_var95: float = analyser.get_avg_var9599['var95']
        avg_risk_var99: float = analyser.get_avg_var9599['var99']
        avg_risk_var95s = [avg_risk_var95 for _ in range(len(risk_var95s))]
        avg_risk_var99s = [avg_risk_var99 for _ in range(len(risk_var99s))]
        signal_names = ['Signal {}'.format(i) for i in range(len(risk_var95s))]
        risks = [
            risk_var95s,
            risk_var99s,
            avg_risk_var95s,
            avg_risk_var99s,
        ]
    
        risks = '|'.join(','.join(map(str, risk)) for risk in risks)
        signal_names = '|'.join(signal_names)
        return render_template('chart.html', 
                            risks=risks, 
                            signal_names=signal_names)
    return "<h1>No analysis data, please complete the analysis first.</h1>"


if __name__ == '__main__':
    app.run(debug=True)