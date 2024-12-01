from datetime import datetime
import json
import os


# Class to call which will collect statistics of the files in the network.
class Network_Statistics:
    def __init__(self, file_name='network_statistics.json'):
        self.transfer_statistics = []
        self.stats_file = file_name
        # Creates 'network_statistics.json' file if it doesn't exist. If it does, modifies the data.
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r') as file:
                    self.transfer_statistics = json.load(file)
            except (json.JSONDecodeError, IOError):
                self.transfer_statistics = []

    # Function to collect the statistics of the files in the network.
    def transfer_stats(self, operation, file_name, size, duration, rate):
        self.transfer_statistics.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'filename': file_name,
            'byte_size': size,
            'seconds_duration': duration,
            'mbps_rate': rate
        })

        self.save_stats()

    # Saves the statistics in json format which is very efficient to view offline.
    def save_stats(self, file_name='network_statistics.json'):
        with open(file_name, 'w') as file:
            json.dump(self.transfer_statistics, file, indent=2)

