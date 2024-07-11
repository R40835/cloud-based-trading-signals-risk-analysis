class CostCalculator:
    """
    The specifications are the same across the three Lambda Functions
    created for the system. EC2 specifications are also the same for
    all instances as these are created off an image.
    """
    EC2_PRICE_T2MICRO_1H = 0.0116               
    LAMBDA_COMPUTE_PRICE_100S = 0.0000166667    
    LAMBDA_MEMORY_ALLOCATED_GB = 128            
    LAMBDA_REQUEST_PRICE_1M = 0.2               

    @classmethod
    def ec2_cost(cls, time_taken: float, instances: int) -> dict:
        """
        Calculates the cost of ec2 based on the EC2 image specifications.
        The calculation is done for one instance where the official price 
        for one hour is used to work out the cost of the computation and 
        then the total cost is established by multiplying the result by
        the amount of instances used. The time is then returned in ms.
        https://aws.amazon.com/ec2/pricing/on-demand/
        """
        cost = (time_taken * cls.EC2_PRICE_T2MICRO_1H / 3600) * instances 
        time_ms = time_taken * 1000 
        return {"billable_time": time_ms, "cost": cost}

    @classmethod
    def lambda_cost(cls, time_taken: float, instances: int=1) -> dict:
        """
        Calculates the cost of a Lambda function based on its specifications.
        The calculation takes into account both compute and request cost.
        The time is also converted to ms when return so that the results
        align with EC2's. https://aws.amazon.com/lambda/pricing/
        """
        total_compute_seconds = instances * time_taken
        allocated_memory_gb = cls.LAMBDA_MEMORY_ALLOCATED_GB / 1024
        total_compute_gb_s = total_compute_seconds * allocated_memory_gb
        compute_cost = total_compute_gb_s * cls.LAMBDA_COMPUTE_PRICE_100S
        total_requests = instances
        request_cost = (total_requests / 1000000) * cls.LAMBDA_REQUEST_PRICE_1M
        cost = compute_cost + request_cost
        time_ms = time_taken * 1000
        return {"billable_time": time_ms, "cost": cost}