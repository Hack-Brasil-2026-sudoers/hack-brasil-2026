import argparse
import json

from dotenv import load_dotenv

from .config import Settings


def main():
    parser = argparse.ArgumentParser(description="CyberCheck repository and website security checks")
    parser.add_argument("command", choices=["api", "worker", "web"])
    parser.add_argument("url", nargs="?", help="Web: public HTTP(S) URL to assess")
    parser.add_argument("--authorization-confirmed", action="store_true",
                        help="Web: confirm ownership or written authorization for the target hostname")
    parser.add_argument("--once", action="store_true", help="Worker: process at most one request")
    args = parser.parse_args()
    if args.command == "web":
        from .web import WebError, analyze_web
        if not args.url or args.once:
            parser.error("The web command requires a URL and does not support --once.")
        try:
            report = analyze_web(args.url, authorization_confirmed=args.authorization_confirmed)
        except WebError as exc:
            parser.error(str(exc))
        print(json.dumps(report, indent=2))
        raise SystemExit({"completed": 0, "partial": 2, "failed": 1}[report["status"]])
    if args.url or args.authorization_confirmed:
        parser.error("URL and --authorization-confirmed are only valid for the web command.")
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
