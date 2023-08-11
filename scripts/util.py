import subprocess
import time


def echo(msg):
    print(msg, flush=True)


def run(args):
    """
    Run a command and print it
    :param args:
    :return:
    """
    echo("+ " + args)
    subprocess.check_call(args=args, shell=True)


def run_output(args) -> str:
    """
    Run a command and return its output
    :param args:
    :return:
    """
    echo("+ " + args)
    return subprocess.check_output(args=args, shell=True).decode("utf-8").strip()


def try_until_success_or_timeout(args, timeout=60):
    for i in range(timeout):
        try:
            run(args)
            return
        except Exception as e:
            print(e)
            time.sleep(1)
    raise Exception("Timeout")
