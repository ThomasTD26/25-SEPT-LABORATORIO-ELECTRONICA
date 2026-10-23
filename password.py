import os
import sys


def pedir_password(prompt="Password: "):
    sys.stdout.write(prompt)
    sys.stdout.flush()

    password = ""

    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            elif ch == b"\x08":
                if password:
                    password = password[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == b"\x03":
                raise KeyboardInterrupt
            else:
                try:
                    char = ch.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                password += char
                sys.stdout.write("*")
                sys.stdout.flush()
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                elif ch == "\x7f" or ch == "\x08":
                    if password:
                        password = password[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":
                    raise KeyboardInterrupt
                else:
                    password += ch
                    sys.stdout.write("*")
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return password
