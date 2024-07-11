import json
import boto3


def lambda_handler(event, context):
    """
    Lambda function with AMI role to manage our S3 bucket (read/write)/
    """
    if event["action"] == "write":
        s = event["s"]
        r = event["r"]
        h = event["h"]
        d = event["d"]
        t = event["t"]
        p = event["p"]
        profit_loss = event["profit_loss"]
        av95 = event["av95"]
        av99 = event["av99"]
        time = event["time"]
        cost = event["cost"]
        return write_s3(s, r, h, d, t, p, profit_loss, av95, av99, time, cost)
    elif event["action"] == "read":
        return read_s3()


def write_s3(s: str, r: int, h: int, d: int, t: str, p: int, 
             profit_loss: float, av95: float, av99: float, time: float, cost: float) -> dict:
    """
    Writes results of an analysis into our S3 bucket.
    """
    s3 = boto3.client('s3')
    bucket_name = 'analysis-audit'
    audit_file = 'results.json'
    response = s3.get_object(Bucket=bucket_name, Key=audit_file)
    last_audit: list = json.loads(response['Body'].read().decode('utf-8'))
    last_audit.append(
        {
            "s": s, 
            "r": r,
            "h": h,
            "d": d,
            "t": t,
            "p": p,
            "profit_loss": profit_loss,
            "av95": av95,
            "av99": av99,
            "time": time,
            "cost": cost,
        }        
    )
    updated_audit = json.dumps(last_audit)
    s3.put_object(Bucket=bucket_name, Key=audit_file, Body=updated_audit)
    return {"result": "ok"}


def read_s3() -> dict:
    """
    Reads previous results of analyses stored in our S3 bucket.
    """
    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.get_object(Bucket='analysis-audit', Key='results.json')
    audit = json.loads(response['Body'].read().decode('utf-8'))
    return audit