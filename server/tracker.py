from product_harvester.harvester import ErrorLogger, HarvestError


class ErrorCollector(ErrorLogger):
    def __init__(self):
        self.errors: list[HarvestError] = []

    def track_errors(self, errors: list[HarvestError]):
        super().track_errors(errors)
        self.errors.extend(errors)
