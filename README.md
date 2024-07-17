# cloud-based-trading-signals-risk-analysis
A cloud system that integrates GAE and AWS services including Lambda, EC2, and S3 for scalable risk analysis and trading strategy optimisation. GAE manages API requests, while AWS handles computation and storage. 

# Architecture
All API calls are processed within Google App Engine (GAE). When /warmup is invoked, it triggers a subsequent call to an AWS Lambda function. Three distinct Lambda functions were designed for specific tasks: one for direct computations, another for scaling out EC2 instances, and the last for managing storage in an S3 bucket.

| API Endpoint         | Purpose                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| /warmup              | Prepares to the specified scale for one of the services (EC2/Lambda).                                                           |
| /scaled_ready        | Obtains confirmation that the specified scale is prepared for analysis.                                                         |
| /get_warmup_cost     | Obtains the total billable time for warming up to the requested scale and the associated costs.                                 |
| /get_endpoints       | Obtains call strings necessary for directly accessing each unique endpoint made available during warmup.                        |
| /analyse             | Conducts the analysis to enable retrieval of results through the successive API calls.                                          |
| /get_sig_vars9599    | Obtains pairs of 95% and 99% Value at Risk (VaR) values for each signal.                                                        |
| /get_avg_vars9599    | Obtains the average risk values across all signals at both 95% and 99%.                                                         |
| /get_sig_profit_loss | Obtains profit/loss values for all signals.                                                                                     |
| /get_tot_profit_loss | Obtains total profit/loss.                                                                                                      |
| /get_chart_url       | Obtains the URL for a chart generated using the previous VaR values.                                                            |
| /get_time_cost       | Obtains the total billable time for the analysis and related cost.                                                              |
| /get_audit           | Obtains relevant information about all previous runs.                                                                           |
| /reset               | Performs necessary cleanup operations to prepare for another analysis, while retaining the initially requested warmed-up scale. |
| /terminate           | Terminates as needed to scale down to zero, necessitating a restart from the /warmup phase to resume operations.                |
| /scaled_terminated   | Obtains confirmation of scale-to-zero.                                                                                          |

The first Lambda function executes when the user specifies "s" as "lambda" along with specified scaling parameters (mean, std, shots). Its primary role is to scale the Lambda function efficiently for upcoming analyses. AWS dynamically scales the function instances based on concurrent requests.

The second Lambda function is activated when the user opts for EC2. It receives a JSON payload {"action": "create", "r": "r"} where "r" denotes the user-specified scaling factor. This function, equipped with IAM roles, orchestrates the creation and termination of EC2 instances without waiting for them to become operational. It returns the IDs of created instances, crucial for subsequent API operations.

The /scaled_ready API sends a POST request to the second Lambda function with a JSON payload {"action": "confirm_creation", "ids": ids} containing instance IDs. If the instances are not yet running, it returns {"warm": "false"}; otherwise, {"warm": "true", "instances_dns": dns} with DNS entries of running instances. This API operates independently of external cloud services when Lambda handles warm-up due to AWS's efficient management of Lambda scaling.

During analysis with Lambda, /analyse executes parallel POST requests to the first Lambda function responsible for computations. The number of requests is scaled according to the user-specified factor "r". Each Lambda function instance receives JSON input {"mean": mean, "std": std, "shots": shots} and returns computed values for var95 and var99, averaged within GAE.

In contrast, analysis using EC2 involves parallel requests to EC2 instances launched during warm-up, identified by their DNS entries. The payload format remains consistent, and the number of parallel requests matches the specified scaling factor for EC2 warm-up.

After completing analysis, relevant data is stored in a JSON file within an AWS S3 bucket using the third Lambda function, which is authorized to read from and write to dedicated S3 storage. The write operation includes essential information like service name, scaling factor, historical parameters, risk values, billing details, and costs.

To retrieve analysis results, /get_audit loads the JSON file from the S3 bucket via the same Lambda function. Here, the action "read" is specified, and the returned payload contains previous analysis results.
![audit](https://github.com/user-attachments/assets/0342badb-9ba6-410e-89c7-3b33393214cb)

For users opting to terminate EC2 services post-analysis, /terminate sends a post request to the second Lambda function to scale down to zero. The JSON payload {"action": "terminate", "ids": ids} includes instance IDs, and the response {"result": "ok"} confirms successful termination. Lambda does not support termination directly, as AWS manages its service infrastructure.

Lastly, /scaled_terminated checks if EC2 instances used for analysis were successfully terminated by invoking the second Lambda function with {"action": "confirm_termination" , "ids": ids}. The function responds with {"result": "ok"} upon successful termination confirmation.

# Chart 
The chart displays risk values for each signal, featuring two values for each signal and two average lines, one for 95% signal values and another for 99% signal values.
![chart](https://github.com/user-attachments/assets/bd4ad87a-1657-447e-9a63-5fb52595fa6f)
