@echo off
set endpoint=https://xxxx-123456.nw.r.appspot.com/

rem LAMBDA

echo Warmup Lambda
curl -s -H "Content-Type: application/json" -X POST -d "{\"s\":\"lambda\", \"r\":\"3\"}" %endpoint%/warmup

set ready=""
:check_ready
curl -s %endpoint%/scaled_ready | jq ".warm" > temp.json
for /f %%i in (temp.json) do set ready=%%i
del temp.json

if %ready% neq "\"true\"" if %ready% neq "true" if %ready% neq "\"True\"" (
    echo Scale not ready yet, waiting 10 seconds before retrying.
    timeout /t 10 > nul
    goto check_ready
)

echo Warm cost
curl -s %endpoint%/get_warmup_cost

echo Scalable service endpoints
curl -s %endpoint%/get_endpoints

echo Analyse
curl -s -H "Content-Type: application/json" -X POST -d "{\"h\": \"101\", \"d\": \"10000\", \"t\": \"sell\", \"p\": \"7\"}" %endpoint%/analyse

echo Results 
curl -s %endpoint%/get_sig_vars9599
curl -s %endpoint%/get_avg_vars9599

echo Profits 
curl -s %endpoint%/get_sig_profit_loss
curl -s %endpoint%/get_tot_profit_loss

echo Chart
echo you have 20 seconds to check the chart.
curl -s %endpoint%/get_chart_url
timeout /t 20 > nul

echo Time cost
curl -s %endpoint%/get_time_cost

echo Audit
curl -s %endpoint%/get_audit

echo Endpoints
curl -s %endpoint%/get_endpoints

echo 3 tidyup calls
curl -s %endpoint%/reset
curl -s %endpoint%/terminate

set gone=""
:check_terminated
curl -s %endpoint%/scaled_terminated | jq ".terminated" > temp.json
for /f %%i in (temp.json) do set gone=%%i
del temp.json

if %gone% neq "\"true\"" if %gone% neq "true" if %gone% neq "\"True\"" (
    echo Scale not terminated yet, waiting 10 seconds before retrying.
    timeout /t 10 > nul
    goto check_terminated
)

echo Process completed

rem EC2

echo Warmup EC2
curl -s -H "Content-Type: application/json" -X POST -d "{\"s\":\"ec2\", \"r\":\"3\"}" %endpoint%/warmup

set ready=""
:check_ready
curl -s %endpoint%/scaled_ready | jq ".warm" > temp.json
for /f %%i in (temp.json) do set ready=%%i
del temp.json

if %ready% neq "\"true\"" if %ready% neq "true" if %ready% neq "\"True\"" (
    echo Scale not ready yet, waiting 10 seconds before retrying.
    timeout /t 10 > nul
    goto check_ready
)

echo Warm cost
curl -s %endpoint%/get_warmup_cost

echo Scalable service endpoints
curl -s %endpoint%/get_endpoints

echo Analyse
curl -s -H "Content-Type: application/json" -X POST -d "{\"h\": \"101\", \"d\": \"10000\", \"t\": \"sell\", \"p\": \"7\"}" %endpoint%/analyse

echo Results 
curl -s %endpoint%/get_sig_vars9599
curl -s %endpoint%/get_avg_vars9599

echo Profits 
curl -s %endpoint%/get_sig_profit_loss
curl -s %endpoint%/get_tot_profit_loss

echo Chart
echo you have 20 seconds to check the chart.
curl -s %endpoint%/get_chart_url
timeout /t 20 > nul

echo Time cost
curl -s %endpoint%/get_time_cost

echo Audit
curl -s %endpoint%/get_audit

echo Endpoints
curl -s %endpoint%/get_endpoints

echo 3 tidyup calls
curl -s %endpoint%/reset
curl -s %endpoint%/terminate

set gone=""
:check_terminated
curl -s %endpoint%/scaled_terminated | jq ".terminated" > temp.json
for /f %%i in (temp.json) do set gone=%%i
del temp.json

if %gone% neq "\"true\"" if %gone% neq "true" if %gone% neq "\"True\"" (
    echo Scale not terminated yet, waiting 10 seconds before retrying.
    timeout /t 10 > nul
    goto check_terminated
)

echo Process completed
