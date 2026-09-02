"""Run one command (or an sftp batch) on the HA host using $HA_EDIT_KEY.

The key is written to a mode-0600 temp file and unlinked in a finally block, so
it never persists and never enters a command line that gets displayed.
"""
import os, pathlib, subprocess, sys, tempfile

HOST, PORT = "root@192.168.4.141", "2222"
OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR"]


def main():
    mode, arg = sys.argv[1], sys.argv[2]
    fd, path = tempfile.mkstemp(prefix="ha-edit-key-")
    keyfile = pathlib.Path(path)
    try:
        key = os.environ["HA_EDIT_KEY"]
        os.write(fd, (key if key.endswith("\n") else key + "\n").encode())
        os.close(fd)
        keyfile.chmod(0o600)
        if mode == "ssh":
            cmd = ["ssh", "-i", str(keyfile), "-p", PORT, *OPTS, HOST, arg]
        else:
            cmd = ["sftp", "-i", str(keyfile), "-P", PORT, *OPTS, "-b", arg, HOST]
        r = subprocess.run(cmd, timeout=120)
        sys.exit(r.returncode)
    finally:
        keyfile.unlink(missing_ok=True)


main()
