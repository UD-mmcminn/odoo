#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import threading
import time


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import odoo.cli
from odoo.tools import config as odoo_config


HOLD_TIMEOUT_SECONDS = 60


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run an Odoo HTTP server with a one-shot held portal audit event.",
    )
    parser.add_argument('--hold-event-type', required=True)
    parser.add_argument('--hold-signer-id', required=True, type=int)
    parser.add_argument('--hold-start-file', required=True)
    parser.add_argument('--hold-release-file', required=True)
    parser.add_argument('odoo_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.odoo_args or args.odoo_args[0] != '--':
        parser.error("Odoo CLI args must be passed after '--'.")
    args.odoo_args = args.odoo_args[1:]
    if not args.odoo_args:
        parser.error("Missing Odoo CLI args after '--'.")
    return args


def _install_hold_patch(args):
    from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController

    start_file = Path(args.hold_start_file)
    release_file = Path(args.hold_release_file)
    start_file.parent.mkdir(parents=True, exist_ok=True)
    release_file.parent.mkdir(parents=True, exist_ok=True)
    if start_file.exists():
        start_file.unlink()
    if release_file.exists():
        release_file.unlink()

    original = OpenSignPortalController._append_audit_event
    hold_lock = threading.Lock()
    held_once = {'value': False}

    def wrapped(controller, signer, event_type, *, event_at, metadata=None, consent_text_hash=False):
        should_hold = False
        if event_type == args.hold_event_type and signer.id == args.hold_signer_id:
            with hold_lock:
                if not held_once['value']:
                    held_once['value'] = True
                    should_hold = True
        if should_hold:
            start_file.write_text('held\n', encoding='utf-8')
            deadline = time.monotonic() + HOLD_TIMEOUT_SECONDS
            while not release_file.exists():
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"Timed out waiting for release file {release_file} "
                        f"while holding {args.hold_event_type} for signer {args.hold_signer_id}."
                    )
                time.sleep(0.05)
        return original(
            controller,
            signer,
            event_type,
            event_at=event_at,
            metadata=metadata,
            consent_text_hash=consent_text_hash,
        )

    OpenSignPortalController._append_audit_event = wrapped


def main():
    args = _parse_args()
    odoo_config.parse_config(args.odoo_args)
    _install_hold_patch(args)
    sys.argv = [os.fspath(ROOT_DIR / 'odoo-bin'), *args.odoo_args]
    odoo.cli.main()


if __name__ == '__main__':
    main()
