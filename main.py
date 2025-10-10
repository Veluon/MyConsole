import os
import shlex
import socket
import importlib
import traceback
import argparse
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from vfs_json import open_vfs_from_json

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
    # попытка установки имени пользователя
    try:
        user = os.getlogin()
    except Exception:
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    # попытка установки хоста
    try:
        host = socket.gethostname()
    except Exception:
        host = os.environ.get("HOSTNAME", "unknown")
    return f"Эмулятор - [{user.strip()}@{host.strip()}]"

# запись в консоль
def write_console(msg):
    console.configure(state='normal') # включаем редактирование
    console.insert(END, str(msg) + '\n') # записываем в конец
    console.configure(state='disabled') # выключаем редактирование
    console.see(END) # проматываем вниз

# загрузка VFS
vfs = None
if ARGS.vfs_path:
    vfs = open_vfs_from_json(ARGS.vfs_path)


# парсер комманд
def parser(line):
    try: # пытаемся с помощью модуля шлекс разобрать строку на токены
        raw_tokens = shlex.split(line, posix=True)
    except ValueError as e: # если не получилось - ошибка
        write_console(f"Ошибка разбора строки: {e}")
        return []
    expanded = []
    for token in raw_tokens:
        # раскрытие окружения реальной OC
        token = os.path.expanduser(token) #раскрывает ~d
        token = os.path.expandvars(token) #раскрыавает %d%, $HOME, ${HOME}
        if "$HOME" in token or "${HOME}" in token or "%HOME%" in token: # если методы сверху не сработали
            home = os.path.expanduser("~")
            token = token.replace("$HOME", home).replace("${HOME}", home).replace("%HOME%", home)
        # добавляем токен в конечный список
        expanded.append(token)
    return expanded

# загрузчик команд
def commands_loader():
    global LOADED_COMMANDS_MODULE, COMMANDS
    try:
        if LOADED_COMMANDS_MODULE is None: # если не загружен модуль комманд - загружаем
            LOADED_COMMANDS_MODULE = importlib.import_module(COMMANDS_MODULE_NAME)
        else: # иначе перезагружаем
            LOADED_COMMANDS_MODULE = importlib.reload(LOADED_COMMANDS_MODULE)
    except Exception as e: # в случае ошибки
        # выводим сообщение о модуле
        write_console(f"Не удалось загрузить модуль {COMMANDS_MODULE_NAME}: {e}")
        # выводим ошибку python
        write_console(traceback.format_exc())
        COMMANDS = {}
        return
    # добавляем комманды
    new_commands = {}
    # проверяем, что существует объект COMMANDS и что он словарь
    if hasattr(LOADED_COMMANDS_MODULE, "COMMANDS") and isinstance(getattr(LOADED_COMMANDS_MODULE, "COMMANDS"), dict):
        for k, v in getattr(LOADED_COMMANDS_MODULE, "COMMANDS").items(): # проходимя по словарю и добавляем команды
            if callable(v):
                new_commands[str(k)] = v
    # встроенные комманды
    new_commands.setdefault("reload", builtin_reload)
    new_commands.setdefault("help", builtin_help)

    COMMANDS = new_commands
    write_console(f"Команды загружены: {', '.join(sorted(COMMANDS.keys()))}")

# пробуем импортировать commands и присвоить vfs/HISTORY
try:
    import commands
    # присвоим vfs в модуле commands
    commands.vfs = vfs
except Exception:
    pass

# перезагрузка
def builtin_reload():
    # снова загружаем комманды
    commands_loader()
    # снова установим файловую систему и историю в модуль комманд
    try:
        import commands
        commands.vfs = vfs
        commands.HISTORY = HISTORY
    except Exception:
        pass
    return "Перезагрузка комманд выполнена."

# выводит список команд
def builtin_help():
    names = sorted(COMMANDS.keys())
    return "Доступные команды: " + (", ".join(names) if names else "(нет команд)")

# использование комманды
def use_command(tokens, source=""):
    if not tokens:
        return True
    # разбиваем список на название команды и аргументы и вызываем команду
    name = tokens[0]
    args = tokens[1:]
    fn = COMMANDS.get(name)
    if fn is None:
        write_console(f"Неизвестная команда: {name}")
        return False
    try:
        res = fn(*args) # выполняем команду и получаем результат
    except TypeError as e: # в случае ошибки ввода
        write_console(f"Ошибка вызова команды '{name}': {e}")
        return False
    except Exception as e: # при иных ошибках
        write_console(f"Исключение при выполнении команды '{name}': {e}")
        write_console(traceback.format_exc())
        return False
    # если строка и exit токен - прекращаем работу
    if isinstance(res, str) and res == "__EXIT__":
        write_console("Команда exit: завершение эмулятора.")
        try:
            root.quit()
        except Exception:
            pass
        return False
    # если содержимое результата список или кортеж - выводим на экран поэлементно
    if isinstance(res, (list, tuple)):
        for line in res:
            write_console(line)
    elif res is None: # если нет результата - пропускаем
        pass
    else: # если один элемент - выводим его
        write_console(res)
    if isinstance(res, str) and ("Ошибка" in res or "ошибка" in res or "error" in res.lower()): # если вернулась ошибка
        return False
    return True

# стартовый скрипт
def run_startup_script(path):
    # в случае ошибок загрузки скрипта
    if not path:
        return False
    if not os.path.isfile(path):
        write_console(f"Стартовый скрипт не найден: {path}")
        return False

    # выполнение скрипта
    write_console(f"Выполнение стартового скрипта: {path}")
    with open(path, "r", encoding="utf-8") as f: # открываем для чтения
        lines = f.readlines() # считываем строки
    for idx, raw in enumerate(lines): # переделываем в словарь и проходимся по всем строкам
        # очищаем строку от лишнего
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue

        # пишем строку в консоль
        write_console(f"> {line}")
        # сохраняем в историю
        HISTORY.append(line)
        # токенизируем команду
        tokens = parser(line)
        if not tokens: # если не разобрали комманду - стопаем
            write_console(f"Ошибка разбора на строке {idx+1}: {line}")
            return False

        # выполняем комманду
        ok = use_command(tokens, source="script")

        if not ok: # если комманда выдала ошибку - стопаем
            write_console(f"Скрипт остановлен из-за ошибки на строке {idx+1}: {line}")
            return False

    write_console("Стартовый скрипт выполнен успешно.")
    return True

# TKINTER
# основное окно
root = Tk()
root.title(setGUITitle())
root.geometry("750x520")

# окно консоли с историем комманд и их выводом
console = ScrolledText(root, wrap=WORD, background="black", foreground="white", font=("Consolas", 11))
console.pack(fill="both", expand=True, padx=6, pady=(6,3))
console.configure(state='disabled')

# окошко для размещения строки ввода
bottom = Frame(root)
bottom.pack(fill="x", side="bottom", padx=6, pady=6)

# строка ввода
entry = Entry(bottom, font=("Consolas", 11))
entry.pack(fill="x", side="left", expand=True)

# история комманд
HISTORY = []
# установка истории комманд из модуля комманд
try:
    import commands
    HISTORY = commands.HISTORY
except Exception:
    pass

# при нажатии Enter после ввода текста в строку ввода
def on_enter(event=None):
    line = entry.get().strip()

    if not line:
        return "break"

    # выводим комманду в консоль
    write_console(f"> {line}")
    # сохраняем в историю
    HISTORY.append(line)
    # если модуль commands импортирован, обновим его глобальную историю
    try:
        import commands
        commands.HISTORY = HISTORY
    except Exception:
        pass

    # токенизируем ввод
    tokens = parser(line)
    # вызываем комманду
    use_command(tokens, source="interactive")
    # очищаем строку ввода
    entry.delete(0, END)
    return "break"

# биндим ввод на Enter
entry.bind("<Return>", on_enter)
# ставим фокус на дисплее на приложение консоли
entry.focus_set()

# загрузка VFS и истории команд в модуль комманд
commands_loader()
try:
    import commands
    commands.vfs = vfs
    commands.HISTORY = HISTORY
except Exception:
    pass

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
