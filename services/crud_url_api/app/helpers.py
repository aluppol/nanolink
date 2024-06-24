import os


# Fetch and validate environment variables
def get_env_variable(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable {name} is not set.")
    return value
