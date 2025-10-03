import os
import shlex
import socket
import importlib
import traceback
import argparse
from tkinter import *
from tkinter.scrolledtext import ScrolledText

COMMANDS = {}
COMMANDS_MODULE_NAME = "commands"
LOADED_COMMANDS_MODULE = None

# интерфейс коммандой строки
def parse_cli():
    p = argparse.ArgumentParser(description="Emulator GUI")
    p.add_argument("--vfs", dest="vfs_path", help="Путь к JSON VFS (источник)", default=None)
    p.add_argument("--script", dest="startup_script", help="Путь к стартовому скрипту (файл с командами эмулятора)", default=None)
    return p.parse_args()

ARGS = parse_cli()

# GUI имя
def setGUITitle():
    try:
        user = os.getlogin()
    except Exception:
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    try:
        host = socket.gethostname()
    except Exception:
        host = os.environ.get("HOSTNAME", "unknown")
    return f"Эмулятор - [{user.strip()}@{host.strip()}]"

# запись в консоль
def write_console(msg):
    console.configure(state='normal')
    console.insert(END, str(msg) + '\n')
    console.configure(state='disabled')
    console.see(END)

# парсер комманд
def parser(line):
    try:
        raw_tokens = shlex.split(line, posix=True)
    except ValueError as e:
        write_console(f"Ошибка разбора строки: {e}")
        return []
    expanded = []
    for token in raw_tokens:
        token = os.path.expanduser(token)
        token = os.path.expandvars(token)
        if ("$HOME" in token or "${HOME}" in token or "%HOME%" in token) and os.environ.get("HOME") is None:
            home = os.path.expanduser("~")
            token = token.replace("$HOME", home).replace("${HOME}", home).replace("%HOME%", home)
        expanded.append(token)
    return expanded

# загрузчик команд
def commands_loader():
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
    new_commands = {}
    if hasattr(LOADED_COMMANDS_MODULE, "COMMANDS") and isinstance(getattr(LOADED_COMMANDS_MODULE, "COMMANDS"), dict):
        for k, v in getattr(LOADED_COMMANDS_MODULE, "COMMANDS").items():
            if callable(v):
                new_commands[str(k)] = v
    else:
        for name in dir(LOADED_COMMANDS_MODULE):
            if name.startswith("_"):
                continue
            obj = getattr(LOADED_COMMANDS_MODULE, name)
            if callable(obj):
                if name.startswith("cmd_"):
                    cmd_name = name[4:]
                else:
                    cmd_name = name
                new_commands[cmd_name] = obj
    # встроенные комманды
    new_commands.setdefault("help", builtin_help)
    COMMANDS = new_commands
    write_console(f"Команды загружены: {', '.join(sorted(COMMANDS.keys()))}")


def builtin_help():
    names = sorted(COMMANDS.keys())
    return "Доступные команды: " + (", ".join(names) if names else "(нет команд)")

# использование комманды
def use_command(tokens):
    if not tokens:
        return True
    name = tokens[0]
    args = tokens[1:]
    fn = COMMANDS.get(name)
    if fn is None:
        write_console(f"Неизвестная команда: {name}")
        return False
    try:
        res = fn(*args)
    except TypeError as e:
        write_console(f"Ошибка вызова команды '{name}': {e}")
        return False
    except Exception as e:
        write_console(f"Исключение при выполнении команды '{name}': {e}")
        write_console(traceback.format_exc())
        return False
    # exit токен
    if isinstance(res, str) and res == "__EXIT__":
        write_console("Команда exit: завершение эмулятора.")
        try:
            root.quit()
        except Exception:
            pass
        return False
    if isinstance(res, (list, tuple)):
        for line in res:
            write_console(line)
    elif res is None:
        pass
    else:
        write_console(res)
    if isinstance(res, str) and ("Ошибка" in res or "ошибка" in res or "error" in res.lower()):
        return False
    return True

# стартовый скрипт
def run_startup_script(path):
    if not path:
        return True
    if not os.path.isfile(path):
        write_console(f"Стартовый скрипт не найден: {path}")
        return False
    write_console(f"Выполнение стартового скрипта: {path}")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        write_console(f"> {line}")
        # сохраняем в историю
        HISTORY.append(line)
        tokens = parser(line)
        if not tokens:
            write_console(f"Ошибка разбора на строке {idx+1}: {line}")
            return False
        ok = use_command(tokens, source="script")
        if not ok:
            write_console(f"Скрипт остановлен из-за ошибки на строке {idx+1}: {line}")
            return False
    write_console("Стартовый скрипт выполнен успешно.")
    return True

# TKINTER
root = Tk()
root.title(setGUITitle())
root.geometry("750x520")

console = ScrolledText(root, wrap=WORD, background="black", foreground="white", font=("Consolas", 11))
console.pack(fill="both", expand=True, padx=6, pady=(6,3))
console.configure(state='disabled')

bottom = Frame(root)
bottom.pack(fill="x", side="bottom", padx=6, pady=6)

entry = Entry(bottom, font=("Consolas", 11))
entry.pack(fill="x", side="left", expand=True)

# история комманд
HISTORY = []
# загрузка комманд и установка истории комманд
try:
    import commands as cmds
    cmds.HISTORY = HISTORY
except Exception:
    pass

def on_enter(event=None):
    line = entry.get().strip()
    if not line:
        return "break"
    write_console(f"> {line}")
    # сохраняем в историю
    HISTORY.append(line)
    # если модуль commands импортирован, обновим его глобальную историю
    try:
        import commands as cmds
        cmds.HISTORY = HISTORY
    except Exception:
        pass
    tokens = parser(line)
    use_command(tokens, source="interactive")
    entry.delete(0, END)
    return "break"

entry.bind("<Return>", on_enter)
entry.focus_set()

# вывод дебаг параметров
write_console("=== Параметры запуска ===")
write_console(f"VFS path   : {ARGS.vfs_path}")
write_console(f"Startup scr: {ARGS.startup_script}")
write_console(f"Working dir: {os.getcwd()}")
write_console(f"Environment: HOME={os.environ.get('HOME')}; USER={os.environ.get('USER') or os.environ.get('USERNAME')}")

# запуск стартового скрипта
if ARGS.startup_script:
    run_startup_script(ARGS.startup_script)

write_console("Эмулятор готов. Введите 'help' для списка команд.")
root.mainloop()
