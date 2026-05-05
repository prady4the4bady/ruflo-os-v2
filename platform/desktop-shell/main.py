from prady_shell.app import PradyShellApp


def main() -> int:
    app = PradyShellApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
