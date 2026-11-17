import argparse

from dotenv import load_dotenv

from .config import Settings


def main():
    parser = argparse.ArgumentParser(description="CyberCheck API and worker")
    parser.add_argument("command", choices=["api", "worker"])
    parser.add_argument("--once", action="store_true", help="Worker: process at most one request")
    args = parser.parse_args()
    load_dotenv()
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    if args.command == "worker":
        from .worker import run
        run(settings, once=args.once)
    else:
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
