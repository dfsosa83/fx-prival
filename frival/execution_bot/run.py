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

    # Pull credentials from Frival's .env if available (always overwrite placeholders)
    frival_env = Path(__file__).resolve().parents[1] / "config" / ".env"
    env_file = config_dir / "credentials.env"
    if frival_env.exists():
        import shutil
        shutil.copy(frival_env, env_file)
        print(f"Credentials synced from {frival_env}")

    if not config_dir.exists():
        print(f"Config directory not found: {config_dir}")
        print("Create execution_bot/config/ with settings.yaml and credentials.env")
        sys.exit(1)

    try:
        config = ConfigManager(str(config_dir))
    except Exception as e:
        print(f"Config error: {e}")
        sys.exit(1)

    if config.is_emergency_stop():
        print("EMERGENCY STOP active in config — exiting.")
        sys.exit(0)

    # ── Validate MT5 credentials ────────────────────────────────
    creds = config.get_mt5_credentials()
    if not creds.get("login") or not creds.get("password"):
        print("MT5 credentials not configured in credentials.env")
        sys.exit(1)

    print(f"Account: {creds['login']} | Server: {creds['server']}")
    print(f"Demo mode: {config.is_demo_mode()}")
    print(f"Pairs: {list(config.get_config('pairs', {}).keys())}")
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