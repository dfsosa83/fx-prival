"""
Frival Order Execution Bot — Entry Point.

Monitors Frival signal output and auto-executes FIRED signals via MT5.

Usage:
    python run.py                     # Start monitoring
    python run.py --once              # Process any pending signals and exit

Emergency stop:
    Create frival/data/emergency_stop.txt to halt all execution.
    Delete the file to resume.

Configuration:
    frival/execution_bot/config/settings.yaml  — trading, risk, pair config
    frival/execution_bot/config/credentials.env — MT5 login credentials
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config_manager import ConfigManager
from signal_watcher import watch_loop
from order_bot import OrderBot, EMERGENCY_STOP


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Frival Order Execution Bot")
    parser.add_argument("--once", action="store_true",
                       help="Process pending signals once and exit")
    parser.add_argument("--config", default="config",
                       help="Path to config directory")
    args = parser.parse_args()

# ── Load configuration ──────────────────────────────────────
    config_dir = Path(__file__).resolve().parent / args.config

    # Read credentials directly from Frival's .env (bypasses ConfigManager issues)
    frival_env = Path(__file__).resolve().parents[1] / "config" / ".env"
    if frival_env.exists():
        import os as _os
        with open(frival_env, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _, _val = _line.partition("=")
                    _os.environ[_key.strip()] = _val.strip()
        print(f"Loaded credentials from {frival_env}")
        # Inject defaults ConfigManager requires but Frival .env doesn't have
        _os.environ.setdefault("MT5_TERMINAL_PATH", "auto")
        _os.environ.setdefault("DEMO_MODE", "true")
        _os.environ.setdefault("EMERGENCY_STOP", "false")
        _os.environ.setdefault("LOG_LEVEL", "INFO")
        _os.environ.setdefault("MAX_DAILY_TRADES", "5")
        _os.environ.setdefault("MAX_DAILY_LOSS", "50.0")

        # Also write a proper credentials.env so ConfigManager internals get real values
        env_file = config_dir / "credentials.env"
        with open(frival_env, encoding="utf-8") as src, open(env_file, "w", encoding="utf-8") as dst:
            dst.write(src.read())
            dst.write("\nMT5_TERMINAL_PATH=auto\nDEMO_MODE=true\nEMERGENCY_STOP=false\n")
            dst.write("LOG_LEVEL=INFO\nMAX_DAILY_TRADES=5\nMAX_DAILY_LOSS=50.0\n")

    if not config_dir.exists():
        print(f"Config directory not found: {config_dir}")
        sys.exit(1)

    try:
        config = ConfigManager(str(config_dir))
    except Exception as e:
        print(f"Config error: {e}")
        sys.exit(1)

    if config.is_emergency_stop():
        print("EMERGENCY STOP active in config — exiting.")
        sys.exit(0)

    # Read credentials directly from Frival .env (beyond ConfigManager's load_dotenv)
    def _read_env(path):
        env = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
        return env

    if frival_env.exists():
        frival_creds = _read_env(frival_env)
        login = frival_creds.get("MT5_LOGIN", "")
        password = frival_creds.get("MT5_PASSWORD", "")
        server = frival_creds.get("MT5_SERVER", "")
    else:
        login = password = server = ""

    if not login or not password:
        print("MT5 credentials not configured in frival/config/.env")
        sys.exit(1)

    print(f"Account: {login} | Server: {server}")
    print(f"Demo mode: {config.is_demo_mode()}")
    pairs = config.get_config('pairs')
    print(f"Pairs: {list(pairs.keys() if pairs else [])}")
    print(f"Max daily loss: ${config.get_risk_config().get('max_daily_loss', 50):.2f}")
    print(f"Emergency stop file: {EMERGENCY_STOP}")
    print()

    # ── Start the bot ───────────────────────────────────────────
    bot = OrderBot(config)

    if not bot.start():
        print("Failed to start bot — check MT5 connection.")
        sys.exit(1)

    if args.once:
        # Single pass: process any pending signals and exit
        print("Single-pass mode — processing pending signals...")
        from signal_watcher import read_new_signals

        signals = read_new_signals()
        for sig in signals:
            bot.handle_signal(sig)
        bot.stop()
        print("Done.")
        return

    # Continuous monitoring
    print("\n[Bot] Monitoring for new signals. Press Ctrl+C to stop.\n")

    try:
        watch_loop(callback=bot.handle_signal)
    except KeyboardInterrupt:
        print("\n[Bot] Shutdown requested.")
    finally:
        bot.stop()


if __name__ == "__main__":
    main()