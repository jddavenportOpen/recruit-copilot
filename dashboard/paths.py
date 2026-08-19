#!/usr/bin/env python3
"""Where your workspace lives.

This is deliberately OUTSIDE the plugin install directory. Claude Code installs a
plugin into a version-scoped path (.../recruit/<version>/), so anything written
inside the plugin tree is stranded the moment the plugin updates. Your experience
bank is the one file you cannot regenerate, so it does not live there.

Resolution order:
  1. $RECRUIT_HOME            - you set it, you own it
  2. $XDG_DATA_HOME/recruit-copilot
  3. ~/.recruit-copilot       - the default
"""
from __future__ import annotations

import os

APP_DIR = "recruit-copilot"


def home(create: bool = False) -> str:
    """Absolute path to the workspace root."""
    env = os.environ.get("RECRUIT_HOME")
    if env:
        p = os.path.abspath(os.path.expanduser(env))
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        p = (os.path.join(os.path.expanduser(xdg), APP_DIR) if xdg
             else os.path.join(os.path.expanduser("~"), "." + APP_DIR))
    if create:
        for sub in ("", "resumes", "state"):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
    return p


def state(create: bool = False) -> str:
    return os.path.join(home(create), "state")


def resumes(create: bool = False) -> str:
    return os.path.join(home(create), "resumes")


if __name__ == "__main__":
    print(home())
