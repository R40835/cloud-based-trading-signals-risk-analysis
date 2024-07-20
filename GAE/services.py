import os
import json
import time
import http.client

from costs import CostCalculator
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod


class Service(ABC):
    """
    Abstract base class that defines a common interface for services.
    """
    @property
    @abstractmethod
    def get_warmup_cost(self) -> dict:
        pass

    @property
    @abstractmethod
    def get_endpoints(self) -> dict:
        pass

    @abstractmethod
    def get_var9599(self, *args, **kwargs) -> tuple:
        pass

    @abstractmethod
    def terminate(self) -> None:
        pass

    @abstractmethod
    def check_scaled_ready(self) -> bool:
        pass

    @abstractmethod
    def check_terminated(self) -> bool:
        pass

    @abstractmethod
    def _scale(self) -> list | None:
        pass

    @abstractmethod
    def _simulation(self, *args, **kwargs) -> tuple:
        pass

    @abstractmethod
    def _format_callstrings(self, *args, **kwargs) -> dict:
        pass


class EC2(Service):
    def __init__(self, runs: int):
        """
        Constructor initialises the DNS for the Lambda intermediary function.
        When an object is created, EC2 servers are scaled to the specified 
        number of runs, through the Lambda function. The EC2 instances ids
        are stored for other operations.
        """
        self.name = "ec2"
        self.lambda_ec2_host = os.getenv('EC2_URL')
        self.runs = runs
        self.instances_ids = self._scale()
        self.instances_dns = None 

    @property
    def get_warmup_cost(self) -> dict:
        """
        Returns the time and cost of warmup for the Lambda used to automate 
        the creation of EC2 instances.
        """
        return CostCalculator.lambda_cost(self.warmup_time)
    
    @property
    def get_endpoints(self) -> dict:
        """
        Returns the EC2 instances' endpoints and their respective call strings.
        """
        return self._format_callstrings(self.instances_dns)

    def get_var9599(self, mean: float, std: float, shots: int) -> tuple:
        """
        Performs parallel requests to the EC2 instances intended for computations.
        The number of parallel requests is proportional to the number of servers
        launched as per the scale specified by the user.
        """
        with ThreadPoolExecutor() as executor:
            results = executor.map(lambda dns: self._simulation(dns, mean, std, shots), [dns for dns in self.instances_dns])
        var95, var99 = zip(*results)
        return var95, var99
    
    def terminate(self) -> None:
        """
        Terminates the EC2 instances launched on warm up. A call is made 
        to the intermediary lambda function that runs the process in the 
        background without waiting for the instances to be terminated. 
        """
        try:
            client = http.client.HTTPSConnection(self.lambda_ec2_host)
            payload = json.dumps({
                "action": "terminate",
                "ids": self.instances_ids
            })
            client.request("POST", "/default/function_two", payload)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))
            print(f"response {data}")
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_ec2_host}')

    def check_scaled_ready(self) -> bool:
        """
        Sends a post request to the intermediary lambda function to check 
        whether the EC2 instances are up and running. This is done using 
        the ids stored when the instances were launched. If the scale is
        ready, the dns of each instance is returned.
        """
        try: 
            client = http.client.HTTPSConnection(self.lambda_ec2_host)
            payload = json.dumps({
                "action": "confirm_creation",
                "ids": self.instances_ids
            })
            client.request("POST", "/default/function_two", payload)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))

            if data["warm"] == True:
                self.instances_dns = data["instances_dns"]
                return True
            return False
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_ec2_host}') 

    def check_terminated(self) -> bool:
        """
        Sends a post request to the intermediary lambda function to check 
        whether the servers are terminated. This is done using the ids
        stored when the EC2 instances were launched.
        """
        try:
            client = http.client.HTTPSConnection(self.lambda_ec2_host )
            payload = json.dumps({
                "action": "confirm_termination",
                "ids": self.instances_ids
            })
            client.request("POST", "/default/function_two", payload)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))
            if data["terminated"] == True:
                return True
            return False
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_ec2_host }') 

    def _scale(self) -> list:
        """
        Scales up the number of EC2 instances to the scale specified.
        A call is made to the intermediary lambda function that sets
        the process in motion and confirms the launch of instances
        without waiting for them to be running. On success the
        instances launched ids are returned.
        """
        start = time.time()
        try:
            client = http.client.HTTPSConnection(self.lambda_ec2_host)
            payload = json.dumps({
                "action": "create",
                "r": self.runs
            })
            client.request("POST", "/default/function_two", payload)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))
            self.warmup_time = time.time() - start
            return data['instances_ids']
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_ec2_host}') 
    
    def _simulation(self, dns: str, mean: float, std: float, shots: int) -> tuple:
        """
        Sends a post request to an EC2 server created during the scale based on the 
        dns provided. The service computes the risks by taking the mean, standard 
        deviation, and the number of shots.
        """
        try:
            client = http.client.HTTPConnection(dns, timeout=10)
            payload = json.dumps({
                "mean": mean,
                "std": std,
                "shots": shots,
            })
            headers = {
                "Content-Type": "application/json",
            }
            client.request("POST", "/calculate_var9599", payload, headers)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))
            return data['var95'], data['var99']
        except IOError:
            print(f'Couldn\'t connect to {dns}')
                
    def _format_callstrings(self, instances_dns: list[str]) -> dict:
        """
        Formats the call strings for the services made available upon warmup.
        """
        endpoints = [
            "http://" + dns + "/calculate_var9599" for dns in instances_dns
        ]
        call_strings = {
            f"{endpoint}": 'curl -s -H "Content-Type: application/json" -X POST -d  \'{{"mean": "0.5", "std": "0.5", "shots": "1"}}\' {}'.format(endpoint) 
            for endpoint in endpoints
        }
        return call_strings


class Lambda(Service):
    def __init__(self, runs: int):
        """
        Constructor initialises the DNS for the Lambda function. When an object 
        is created, the Lambda function is scaled to the number of runs 
        specified by the user.
        """
        self.name = "lambda"
        self.lambda_host = os.getenv('LAMBDA_URL')
        self.terminated = False
        self.runs = runs
        self._scale()

    @property
    def get_warmup_cost(self) -> dict:
        """
        Returns the time and cost of warmup for the Lambda function.
        Unlike EC2 intermediary lambda, we specify the number of 
        instances as the cost formula accounts for that.
        """
        return CostCalculator.lambda_cost(self.warmup_time, self.runs)
    
    @property
    def get_endpoints(self) -> dict:
        """
        Returns the Lambda function endpoint and its call string.
        """
        return self._format_callstrings(self.lambda_host)

    def get_var9599(self, mean: float, std: float, shots: int) -> tuple:
        """
        Performs parallel requests to the Lambda service intended for computations.
        The number of parallel requests is the scale specified by the user. Lambda 
        scales automatically by creating new instances of the function.
        """
        with ThreadPoolExecutor() as executor:
            results = executor.map(lambda _: self._simulation(mean, std, shots), range(self.runs))
        var95, var99 = zip(*results)
        return var95, var99
    
    def terminate(self) -> None:
        """
        Lambda infrastructure is handled by AWS.
        """
        self.terminated = True

    def check_scaled_ready(self) -> bool:
        """
        Lambda would be ready after the parallel call with the number of instances
        specified by the user on warmup.
        """
        if self.terminated == True:
            return False
        return True
            
    def check_terminated(self) -> bool:
        """
        Lambda infrastructure is handled by AWS.
        """
        return True
            
    def _scale(self) -> None:
        """
        As AWS will scale lambda, we make parallel calls so that AWS will 
        scale it to the number of instances specified by the user. Dummy
        data are sent since the aim is purely to ensure Lambda is scaled
        to avoid a cold start.
        """
        start = time.time()
        self.get_var9599(mean=0, std=0, shots=1)
        self.warmup_time = time.time() - start
    
    def _simulation(self, mean: float, std: float, shots: int) -> tuple:
        """
        Computes the risks by taking the mean, standard deviation, and the 
        number of shots. The request is sent to the Lambda function.
        """
        try:
            client = http.client.HTTPSConnection(self.lambda_host)
            payload = json.dumps({
                "mean": mean,
                "std": std,
                "shots": shots,
            })
            client.request("POST", "/default/function_one", payload)
            response = client.getresponse()
            data = json.loads(response.read().decode('utf-8'))
            return data['var95'], data['var99']
        except IOError:
            print(f'Couldn\'t connect to {self.lambda_host}') 

    def _format_callstrings(self, instance_dns: str) -> dict:
        """
        Formats the call strings for the services made available upon warm up.
        """
        endpoint = "https://" + instance_dns + "/default/function_one"
        call_strings = {
            f"{endpoint}": 'curl -s -H "Content-Type: application/json" -X POST -d \'{{"mean": "0.5", "std": "0.5", "shots": "1"}}\' {}'.format(endpoint) 
        }
        return call_strings