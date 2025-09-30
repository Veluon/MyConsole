import os

COMMANDS = {}

def command(name=None):
    def deco(fn):
        cmd_name = name or fn.__name__
        COMMANDS[cmd_name] = fn
        return fn
    return deco

@command("exit")
def cmd_exit():
    exit()


@command("echo")
def cmd_echo(*args):
    pass

@command("add")
def cmd_add(a="0", b="0"):
    pass

@command("pwd")
def cmd_pwd():
    pass

@command("ls")
def cmd_ls(path="."):
    pass

@command("cd")
def cmd_cd(path=None):
    pass


