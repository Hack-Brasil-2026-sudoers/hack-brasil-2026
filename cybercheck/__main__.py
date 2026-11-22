import argparse
import json
import sys

from dotenv import load_dotenv

from .config import Settings


def main():
    parser = argparse.ArgumentParser(description="CyberCheck repository and website security checks")
    parser.add_argument("command", choices=["api", "worker", "web", "web-lab"])
    parser.add_argument("url", nargs="?", help="Web: public HTTP(S) URL to assess")
    parser.add_argument("--authorization-confirmed", action="store_true",
                        help="Web modes: confirm ownership or written authorization")
    parser.add_argument("--profile", choices=["vulnerable", "fixed"], help="Web-lab: generated website profile")
    parser.add_argument("--once", action="store_true", help="Worker: process at most one request")
    args = parser.parse_args()
    if args.command == "web-lab":
        from .web_tools import run_lab
        from .web import WebError
        if args.url or args.once:
            parser.error("The web-lab command does not accept a URL or --once.")
        try:
            report = run_lab(authorization_confirmed=args.authorization_confirmed,
                             profile=args.profile or "vulnerable", progress=lambda message: print(message, file=sys.stderr))
        except WebError as exc:
            parser.error(str(exc))
        print(json.dumps(report, indent=2))
        raise SystemExit({"completed": 0, "partial": 2, "failed": 1}[report["status"]])
    if args.profile is not None:
        parser.error("--profile is only valid for web-lab.")
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
        # OAuth callbacks contain one-time credentials in their query string.
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()
