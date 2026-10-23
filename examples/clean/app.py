import os as system
from os import getenv as read_env

endpoint = system.environ["SERVICE_ENDPOINT"]
model = read_env("MODEL_NAME", "synthetic-model")
