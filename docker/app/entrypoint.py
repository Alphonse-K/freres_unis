#!/usr/bin/env python3
"""Container entrypoint: fix bind-mount ownership, then drop to appuser.

Bind-mounted host directories (uploads/, media/, logs/) keep whatever
ownership they have on the host, which shadows the chown baked into the
image at build time. When a host directory doesn't exist yet, Docker
creates it owned by root before the container starts, so the app --
which must run as the non-root `appuser` -- can't write into it (see the
PermissionError on /app/logs/app.log this was written to fix). Chown the
mount points here, as root, before handing off to the real process.

Runs as PID 1: os.execvp() replaces this process in place rather than
forking, so Docker's signals (SIGTERM on `docker stop`, etc.) still reach
the real process directly.
"""
import os
import pwd
import sys

APP_USER = "appuser"
WRITABLE_DIRS = ["/app/uploads", "/app/media", "/app/logs"]


def main():
    if os.geteuid() != 0:
        # Not running as root (e.g. invoked outside Docker) -- nothing to fix.
        os.execvp(sys.argv[1], sys.argv[1:])
        return

    user = pwd.getpwnam(APP_USER)

    for path in WRITABLE_DIRS:
        os.makedirs(path, exist_ok=True)
        os.chown(path, user.pw_uid, user.pw_gid)

    os.initgroups(APP_USER, user.pw_gid)
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)

    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
