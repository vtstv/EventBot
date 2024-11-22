import yaml

class ConfigLoader:
    def __init__(self, config_path='config/config.yml'):
        self.config_path = config_path

    def load_config(self):
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

    def save_config(self, config):
        with open(self.config_path, 'w') as file:
            yaml.dump(config, file)
