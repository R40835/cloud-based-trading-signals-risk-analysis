import os
import json
import time
import http.client
import yfinance as yf
import pandas as pd

from services import Lambda, EC2
from costs import CostCalculator
from datetime import date, timedelta
from pandas_datareader import data as pdr

yf.pdr_override()
today = date.today()
timePast = today - timedelta(days=1095)
GOOGLE_DATA = 'GOOG'
data = pdr.get_data_yahoo(GOOGLE_DATA, start=timePast, end=today) 


class Analyser:

    lambda_s3_host = os.getenv('S3_URL')

    def __init__(self, s: str, r: int):
        """
        Constructor initialises and scales a service based on the user choice.
        The signals and data needed for the analysis are also readied.
        """
        self.var95s = []
        self.var99s = []
        self.profit_loss = []
        self.time_cost = None
        self.data = data
        self.data['Buy'] = 0
        self.data['Sell'] = 0
        self.analysis_complete = False
        if s.lower() == 'lambda':
            self.service = Lambda(runs=r)
        elif s.lower() == 'ec2':
            self.service = EC2(runs=r)

        self._detect_signals()
        
    @property
    def get_warmup_cost(self) -> dict:
        return self.service.get_warmup_cost
    
    @property
    def get_endpoints(self) -> dict:
        return self.service.get_endpoints
    
    @property
    def get_time_cost(self) -> dict:
        return self.time_cost

    @property
    def get_var9599(self) -> dict:
        return {'var95': self.var95s, 'var99': self.var99s}
    
    @property
    def get_profit_loss(self) -> dict:
        return {'profit_loss': self.profit_loss}
        
    @property
    def get_avg_var9599(self) -> dict: 
        var95_avg = self._compute_avg(self.var95s)
        var99_avg = self._compute_avg(self.var99s)
        return {'var95': var95_avg, 'var99': var99_avg}
            
    @property
    def get_tot_profit_loss(self) -> dict: 
        profit_loss_tot = sum(self.profit_loss)
        return {'profit_loss': profit_loss_tot}
        
    @classmethod
    def get_audit(cls) -> dict:
        """
        Retreives all the information about previous runs. This method
        ensures that the data are always accessible as it won't depend
        on instances of the class that are stored in global variables.
        It sends a post requests to the Lambda function responsible
        for managing the system's S3 bucket used for storage.
        """
        try:
            client = http.client.HTTPSConnection(cls.lambda_s3_host)
            payload = json.dumps({
                "action": "read", 
            })
            client.request("POST", "/default/function_three", payload)
            response = client.getresponse()
            return json.loads(response.read().decode('utf-8'))
        except IOError:
            print(f'Couldn\'t connect to {cls.lambda_s3_host}') 
                    
    def analyse_risk(self, h: int, d: int, t: str, p: int) -> None:
        """
        Analyses the risks using the service specified on the object creation.
        Higher and lower risk values are averaged before being stored. Also,
        the method stores all the analysis information in a S3 Bucket once 
        complete.
        """
        if t.lower() == "sell":
            target = self.data.Sell
        elif t.lower() == "buy":
            target = self.data.Buy
        
        start = time.time()
        for i in range(h, len(self.data)): 
            if target[i]==1: # buy/sell signal 
                mean=self.data.Close[i-h:i].pct_change(1).mean()
                std=self.data.Close[i-h:i].pct_change(1).std()
                var95: tuple 
                var99: tuple
                # performing the simulation using the service specified by the user
                var95, var99 = self.service.get_var9599(mean, std, d)
                # averaging values and storing them
                self.var95s.append(self._compute_avg(var95))
                self.var99s.append(self._compute_avg(var99))
                # computing profit/loss
                if i + p < len(self.data): # the number of days after the signal shouldn't be out of range
                    self.profit_loss.append(
                        self._compute_profit_loss(
                            trade=t.lower(),
                            entry_price=self.data.Close[i],
                            exit_price=self.data.Close[i+p]
                        )
                    )
        time_taken = time.time() - start
        self.analysis_complete = True
        # computing costs
        if self.service.name == "ec2":
            self.time_cost = CostCalculator.ec2_cost(time_taken, self.service.runs)
        elif self.service.name == "lambda":
            self.time_cost = CostCalculator.lambda_cost(time_taken, self.service.runs)
        # storing results
        self._save_results_s3(
            h=h, 
            d=d, 
            t=t, 
            p=p, 
            time=self.time_cost['billable_time'], 
            cost=self.time_cost['cost']
        )

    def service_scaled_ready(self) -> bool:
        """
        Checks that the service scale specified by the user is complete.
        """
        return self.service.check_scaled_ready()
    
    def service_terminated(self) -> bool:
        """
        Checks that the service specified by the user is terminated.
        """
        return self.service.check_terminated()

    def terminate_service(self) -> None:
        """
        Terminates the service specified by the user.
        """
        return self.service.terminate()
    
    def reset(self) -> None:
        """
        Resetting all the class properties for another analysis. This ensures 
        that the service in use is kept along with the scale specified with
        no lurking results.
        """
        self.var95s.clear()
        self.var99s.clear()
        self.profit_loss.clear()
        self.analysis_complete = False
        if self.time_cost:
            self.time_cost["billable_time"] = ""
            self.time_cost["cost"] = ""

    def _detect_signals(self) -> None:
        """
        Gets all the buy/sell signals. The method is called upon the creation
        of an object of this class to ready the data on warmup as requested.
        """
        for i in range(2, len(self.data)): 

            body = 0.01

            # Three Soldiers
            if (self.data.Close[i] - self.data.Open[i]) >= body  \
        and self.data.Close[i] > self.data.Close[i-1]  \
        and (self.data.Close[i-1] - self.data.Open[i-1]) >= body  \
        and self.data.Close[i-1] > self.data.Close[i-2]  \
        and (self.data.Close[i-2] - self.data.Open[i-2]) >= body:
                self.data.at[self.data.index[i], 'Buy'] = 1

            # Three Crows
            if (self.data.Open[i] - self.data.Close[i]) >= body  \
        and self.data.Close[i] < self.data.Close[i-1] \
        and (self.data.Open[i-1] - self.data.Close[i-1]) >= body  \
        and self.data.Close[i-1] < self.data.Close[i-2]  \
        and (self.data.Open[i-2] - self.data.Close[i-2]) >= body:
                self.data.at[self.data.index[i], 'Sell'] = 1

    def _save_results_s3(self, h: int, d: int, t: str, p: int, time: float, cost: float) -> None:
        """
        Stores relevant information to the latest analysis in a file of an S3 bucket.
        The method is called once the analysis is complete and achieve its purposes
        by calling the lambda function created to manage our system's storage.
        """
        try:
            client = http.client.HTTPSConnection(self.lambda_s3_host)
            payload = json.dumps({
                "action": "write",
                "s": self.service.name, 
                "r": self.service.runs,
                "h": h,
                "d": d,
                "t": t,
                "p": p,
                "profit_loss": self.get_tot_profit_loss['profit_loss'],
                "av95": self.get_avg_var9599['var95'],
                "av99": self.get_avg_var9599['var99'],
                "time": time,
                "cost": cost,
            })
            client.request("POST", "/default/function_three", payload)
            response = client.getresponse()
            return json.loads(response.read().decode('utf-8'))
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_s3_host}') 

    @staticmethod
    def _compute_avg(iterable: list | tuple) -> float:
        return sum(iterable) / len(iterable)
    
    @staticmethod
    def _compute_profit_loss(trade: str, entry_price: float, exit_price: float) -> float:
        if trade == "buy":
            return exit_price - entry_price
        elif trade == "sell":
            return -1 * (exit_price - entry_price)