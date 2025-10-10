import platform

COMMANDS = {}
vfs = None   # main присвоит объект vfs
HISTORY = [] # main будет пушить сюда вводы

def command(name=None):
    def deco(fn):
        cmd_name = name or fn.__name__
        COMMANDS[cmd_name] = fn
        return fn
    return deco

# КОМАНДЫ БЕЗ VFS

@command("exit") # выход из консоли
def cmd_exit():
    return "__EXIT__"

@command("echo") # эхо ввода
def cmd_echo(*args):
    return " ".join(args) if args else ""

# КОМАНДЫ РАБОТАЮЩИЕ С VFS

def need_vfs(): # проверка, что vfs подключен
    if 'vfs' not in globals():
        return False, "VFS не подключён"
    return True, None

@command("ls") # текущая директория
def cmd_ls(path="."):
    ok, err = need_vfs()
    if not ok:
        return f"Ошибка: {err}"
    try:
        return "\n".join(vfs.listdir(path))
    except Exception as e:
        return f"Ошибка ls: {e}"

@command("cd") # смена директории
def cmd_cd(path=None):
    ok, err = need_vfs()
    if not ok:
        return f"Ошибка: {err}"
    if not path:
        return "Usage: cd <path>"
    try:
        vfs.chdir(path)
        return vfs.getcwd()
    except Exception as e:
        return f"Ошибка cd: {e}"

@command("cat") # вывод содержимого файла
def cmd_cat(path=None):
    ok, err = need_vfs()
    if not ok:
        return f"Ошибка: {err}"
    if not path:
        return "Usage: cat <path>"
    try:
        return vfs.read_text(path)
    except Exception as e:
        return f"Ошибка cat: {e}"

@command("mkdir") # создать директорию
def cmd_mkdir(path=None):
    pass

@command("write") # записать текст в файл
def cmd_write(path=None, *text):
    ok, err = need_vfs()
    if not ok:
        return f"Ошибка: {err}"
    if not path:
        return "Usage: write <path> <text>"
    data = " ".join(text)
    try:
        vfs.write_text(path, data)
        return f"Выполнено"
    except Exception as e:
        return f"Ошибка write: {e}"

@command("rm") # удалить файл или пустую директорию
def cmd_rm(path=None):
    pass

@command("rmdir") # удалить директорию
def cmd_rmdir(path=None):
    pass

@command("uname") # вывести имя
def cmd_uname():
    u = platform.uname()
    return f"{u.system} {u.node} {u.release}"

@command("history") # история комманд
def cmd_history():
    global HISTORY
    lines = HISTORY
    return "\n".join(lines)

@command("help") # вывести отсортированный список комманд
def cmd_help(*args):
    names = sorted(COMMANDS.keys())
    return "Доступные команды: " + ", ".join(names)


@command("save") # комманда разработчика для сохранения json для радактирования
def cmd_save(name=None):
    ok, err = need_vfs()
    debug_mode = False

    if vfs.filename and not name:
        name = vfs.filename
    if name != vfs.filename and not debug_mode:
        return "Создание нового файла в реальной OC запрещено"
    try:
        vfs.save(name)
        return f"vfs {name} сохранена"
    except Exception:
        return "Usage: <file_name>.json"