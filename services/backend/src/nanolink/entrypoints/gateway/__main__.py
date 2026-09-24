from nanolink.entrypoints.gateway.app import create_gateway_app
from nanolink.entrypoints.gateway.services import open_gateway_services
from nanolink.entrypoints.http_server import serve_http
from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.settings import gateway_settings, log_level


def run() -> None:
    settings = gateway_settings()
    configure_logging(log_level())
    serve_http(create_gateway_app(lambda: open_gateway_services(settings)), settings.port, log_level())


if __name__ == "__main__":
    run()
