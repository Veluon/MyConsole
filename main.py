from tkinter import *
from tkinter.scrolledtext import ScrolledText
import shlex
import socket
import os
import importlib
import traceback


COMMANDS = {}
COMMANDS_MODULE_NAME = "commands"
LOADED_COMMANDS_MODULE = None

def setGUITitle():
    # юзернейм
    try:
        user = os.getlogin()
    except Exception:
        user = None
    if not user:
        user = "unknown"

    # хостнейм
    try:
        host = socket.gethostname()
    except Exception:
        host = os.environ.get("HOSTNAME", "unknown")

    return f"Эмулятор - {user.strip()}@{host.strip()}"

def write_console(msg): # запись в консоль
    console.configure(state='normal')
    console.insert(END, msg + '\n')
    console.configure(state='disabled')
    console.see(END)

def on_enter(): # при вводе
    line = entry.get().strip()

    if line == "":
        return "break"

    write_console(f"> {line}")


    tokens = parser(line)

    use_command(tokens)

    entry.delete(0, END)
    return "break"

def parser(line): # парсер комманд
    try:
        raw_tokens = shlex.split(line)
    except ValueError:
        write_console("error command")
        return []

    if raw_tokens != "":
        expanded = []
        for token in raw_tokens:
            token = os.path.expanduser(token)
            token = os.path.expandvars(token)
            expanded.append(token)
        return expanded

def commands_loader(): # загрузчик комманд
    global LOADED_COMMANDS_MODULE, COMMANDS
    try:
        if LOADED_COMMANDS_MODULE is None:
            LOADED_COMMANDS_MODULE = importlib.import_module(COMMANDS_MODULE_NAME)
        else:
            LOADED_COMMANDS_MODULE = importlib.reload(LOADED_COMMANDS_MODULE)
    except Exception as e:
        write_console(f"Не удалось загрузить модуль {COMMANDS_MODULE_NAME}: {e}")
        write_console(traceback.format_exc())
        COMMANDS = {}
        return

    # собираем команды
    new_commands = {}
    # если модуль экспортирует dict COMMANDS
    if hasattr(LOADED_COMMANDS_MODULE, "COMMANDS") and isinstance(getattr(LOADED_COMMANDS_MODULE, "COMMANDS"), dict):
        for k, v in getattr(LOADED_COMMANDS_MODULE, "COMMANDS").items():
            if callable(v):
                new_commands[str(k)] = v
    else:
        # иначе — пробегаем по атрибутам модуля и регистрируем
        for name in dir(LOADED_COMMANDS_MODULE):
            if name.startswith("_"):
                continue
            obj = getattr(LOADED_COMMANDS_MODULE, name)
            if callable(obj):
                # правило: если имя функции начинается с "cmd_" — команда = name[4:]; иначе используем имя.
                if name.startswith("cmd_"):
                    cmd_name = name[4:]
                else:
                    cmd_name = name
                new_commands[cmd_name] = obj

    COMMANDS = new_commands
    write_console(f"Команды загружены: {', '.join(sorted(COMMANDS.keys()))}")


def use_command(tokens):
    if not tokens:
        return
    name = tokens[0]
    args = tokens[1:]

    # поиск команды
    fn = COMMANDS.get(name)
    if fn is None:
        write_console(f"Неизвестная команда: {name}")
        return

    try:
        res = fn(*args)
        # обработка результата:
        if res is None:
            return
        if isinstance(res, (list, tuple)):
            for line in res:
                write_console(str(line))
        else:
            write_console(str(res))
    except TypeError as e:
        write_console(f"Ошибка вызова: {e}")
    except Exception as e:
        write_console(f"Ошибка выполнения: {e}")
        write_console(traceback.format_exc())

# TKINTER
root = Tk()
root.title(setGUITitle())
root.geometry("650x500")

# окно консоли
console = ScrolledText(root, wrap=WORD, background="black", foreground="white", font=("Consolas", 11))
console.pack(fill="both", expand=True, padx=6, pady=(6, 3))
console.configure(state='disabled')

# окно с вводом
bottom = Frame(root)
bottom.pack(fill="x", side="bottom", padx=6, pady=6)

# ввод команд
entry = Entry(bottom, font=("Consolas", 11))
entry.pack(fill="x", side="left", expand=True)
entry.bind("<Return>", on_enter)

entry.focus_set()

commands_loader()

root.mainloop()
