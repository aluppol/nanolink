from nanolink.entrypoints.http_server import serve_http
from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.notifier.app import create_notifier_app
from nanolink.entrypoints.notifier.services import open_notifier_services
from nanolink.entrypoints.settings import log_level, notifier_settings


def run() -> None:
    settings = notifier_settings()
    configure_logging(log_level())
    serve_http(create_notifier_app(lambda: open_notifier_services(settings)), settings.port, log_level())


if __name__ == "__main__":
    run()
