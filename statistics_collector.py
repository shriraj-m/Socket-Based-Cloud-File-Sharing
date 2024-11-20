from datetime import datetime
import json


class Network_Statistics:
    def __init__(self):
        self.transfer_statistics = []

    def transfer_stats(self, operation, file_name, size, duration, rate):
        self.transfer_statistics.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'filename': file_name,
            'byte_size': size,
            'seconds_duration': duration,
            'mbps_rate': rate
        })

    # Json very efficient to view offline
    def save_stats(self, file_name='network_statistics.json'):
        with open(file_name, 'w') as file:
            json.dump(self.transfer_statistics, file, indent=2)

