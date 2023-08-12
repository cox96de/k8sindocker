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
    process = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = ""

    for i in process.stdout:
        output += i.decode('utf-8')
        print(i.decode('utf-8'), end='')

    process.wait()
    output = output.strip()
    error = process.stderr.read().decode('utf-8').strip()

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, args, output=output, stderr=error)

    return output


def try_until_success_or_timeout(args, timeout=60):
    for i in range(timeout):
        try:
            run(args)
            return
        except Exception as e:
            print(e)
            time.sleep(1)
    raise Exception("Timeout")
