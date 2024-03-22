import os
import sys
import toml


def get_config_file():
    if len(sys.argv) > 1:
        return os.path.join(os.getcwd(), sys.argv[1])
    elif os.path.isfile(os.path.join(os.getcwd(), "config.toml")):
        return os.path.join(os.getcwd(), "config.toml")
    else:
        raise FileNotFoundError("config not found")


config = toml.load(get_config_file())
