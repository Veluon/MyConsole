import os
import json
import base64

# нормирование пути
def _norm_path(p):
    if not p: # если пустая - вернем корень
        return "/"
    # если неправильно повернут слэш - заменяем
    p = p.replace("\\", "/")
    # пересборка пути
    parts = [seg for seg in p.split("/") if seg not in ("", ".")]

    # возвращение нормированной строки
    return "/" + "/".join(parts) if parts else "/"

# разбиение строки
def _split_path(p):
    p = _norm_path(p) # нормируем
    if p == "/": # если корневая
        return []

    # преобразуем в список и возвращаем
    return p.strip("/").split("/")

# класс VFS файлов
class JSONVFS:
    def __init__(self, root_node = None, filename = None):
        if root_node is None: # если коревая нода не задана - задаем пустую
            root_node = {"type": "dir", "entries": {}}
        self.root = root_node # корневая нода
        self.cwd = "/" # текущая рабочая папка
        self.filename = filename # имя файла

    # возвращает родит. узел и имя конечного элемента
    def _walk_parent(self, path, create = False):
        path = self.abspath(path) # получаем абсолютный путь
        if path == "/": # если корневая - возвращаем корневую
            return self.root, "/"

        parts = _split_path(path) # делим путь на части

        node = self.root # создаем переменную-ноду
        for part in parts[:-1]: # проходимся от корня до последнего элемента
            entries = node.setdefault("entries", {}) # берем по ключу entries или задаем пустой словарь
            if part not in entries: # если ноды нету в дочерних нодах
                if create: # если создание директорий включено - создаем
                    entries[part] = {"type": "dir", "entries": {}}
                else: # иначе - возвращаем ненахождение
                    return None, None
            node = entries[part] # переходим дальше по пути
            if node.get("type") != "dir": # если нода не директория - вовзращаем ненахождение
                return None, None
        return node, parts[-1] # возвращаем родителя и конечный элемент

    # проверка на существование
    def exists(self, path):
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        if parent is None: # если нет родителя - не существует - не нашли
            return False
        if name == "/": # если корневая - всегда существует
            return True
        return name in parent.get("entries", {}) # возвращаем флаг поиска элемента в родителе

    # проверка, что директория
    def is_dir(self, path):
        if _norm_path(path) == "/": # если корневая - всегда директория
            return True
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        if not parent: # нет родителя - не нашли
            return False

        node = parent.get("entries", {}).get(name) # ищем конечный элемент в родителе

        return bool(node and node.get("type") == "dir") # если элемент есть и его тип - директория = истина

    # проверка, что файл
    def is_file(self, path):
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        if not parent: # нет родителя - не нашли
            return False

        node = parent.get("entries", {}).get(name) # ищем конечный элемент в родителе

        return bool(node and node.get("type") == "file") # если элемент есть и его тип - файл = истина

    # (ls) возвращает открытый каталог
    def listdir(self, path = "/"):
        abs_path = self.abspath(path) # получаем абсолютный путь
        if abs_path == "/": # если корень - берем корневой узел
            node = self.root
        else: # иначе
            parent, name = self._walk_parent(abs_path) # находим родит. узел и конечный элемент
            if not parent: # если нет родителя - поднимаем ошибку
                raise FileNotFoundError(path)

            node = parent.get("entries", {}).get(name) # находим нужный элемент в родителе

        if not node or node.get("type") != "dir": # если не директория - поднимаем ошибку
            raise NotADirectoryError(path)
        return sorted(list(node.get("entries", {}).keys())) # выводим отсортированный список элементов узла

    # чтение из base64
    def read_bytes(self, path):
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        if not parent: # если нет родителя - поднимаем ошибку
            raise FileNotFoundError(path)

        node = parent.get("entries", {}).get(name) # находим нужный элемент в родителе

        if not node or node.get("type") != "file": # если не файл - поднимаем оишбку
            raise FileNotFoundError(path)

        # возвращаем декодированные из base64 данные по ключу data или пустую строку
        return base64.b64decode(node.get("data", ""))

    # чтение текстового файла в VFS
    def read_text(self, path, encoding="utf-8"):
        # читаем base64 данные, декодируем в UTF-8 и возвращаем флаг
        return self.read_bytes(path).decode(encoding)

    # запись в base64 данные
    def write_bytes(self, path, data, overwrite=True):
        # находим родит. узел и конечный элемент (создаем узлы при необходимости)
        parent, name = self._walk_parent(path, create=True)
        if not parent: # если нет родителя - поднимаем ошибку
            raise FileNotFoundError(path)

        entries = parent.setdefault("entries", {}) # берем по ключу entries или задаем пустой словарь
        # если элемент не файлого типа, есть в entries и перезапись не включена - ошибка
        if name in entries and not overwrite and entries[name].get("type") == "file":
            raise FileExistsError(path)
        if name in entries and entries[name].get("type") != "file": # если не файл - ошибка
            raise TypeError(path)
        # добавляем (меняем) элемент в entries с заданной data, закодированной в base64
        entries[name] = {"type": "file", "data": base64.b64encode(data).decode("ascii")}
        return True

    # запись в файл VFS
    def write_text(self, path, text, encoding="utf-8", overwrite=True):
        # записываем текст в base64 (при необходимости перезаписываем) и возвращаем флаг
        return self.write_bytes(path, text.encode(encoding), overwrite=overwrite)

    # создание директории
    def mkdir(self, path, exist_ok=False):
        # находим родит. узел и конечный элемент (создаем узлы при необходимости)
        parent, name = self._walk_parent(path, create=True)
        if not parent: # если нет родителя - поднимаем ошибку
            raise FileNotFoundError(path)

        entries = parent.setdefault("entries", {}) # берем по ключу entries или задаем пустой словарь

        if name in entries: # если уже существует такой элемент
            if entries[name].get("type") == "dir": # если это директория
                if exist_ok: # если не считаем ошибкой (по умолчанию ошибка)
                    return # ничего
                raise FileExistsError(path) # иначе ошибка
            raise FileExistsError(path)

        entries[name] = {"type": "dir", "entries": {}} # создаем директорию

    # удалить элемент VFS
    def remove(self, path):
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        # если нет родителя или элемента - ошибка
        if not parent or name not in parent.get("entries", {}):
            raise FileNotFoundError(path)

        node = parent["entries"][name] # берем найденный элемент по ключу

        # если это директория и содержит элементы - ошибка
        if node.get("type") == "dir" and node.get("entries"):
            raise OSError("Directory not empty")

        del parent["entries"][name]  # удаляем элемент из словаря родителя

    # удаление директории
    def rmdir(self, path):
        parent, name = self._walk_parent(path) # находим родит. узел и конечный элемент
        # если нет родителя или элемента - ошибка
        if not parent or name not in parent.get("entries", {}):
            raise FileNotFoundError(path)

        node = parent["entries"][name] # берем найденный элемент по ключу

        if node.get("type") != "dir": # если не директория - ошибка
            raise NotADirectoryError(path)
        if node.get("entries"): # если не пустая директория - ошибка
            raise OSError("Directory not empty")
        del parent["entries"][name] # удаляем элемент из словаря родителя

    # получить абсолютный путь
    def abspath(self, path):
        if not path: # если пусто - возвращаем текущую директорию
            return self.cwd
        if path.startswith("/"): # если уже абсолютный путь - нормируем и возвращаем
            return _norm_path(path)
        #
        return _norm_path(os.path.join(self.cwd.lstrip("/"), path))

    # (cd) смена текущей рабочей директории
    def chdir(self, path):
        new = self.abspath(path) # получаем абсолютный путь до нового расположения
        if not self.is_dir(new): # если путь не до директории - ошибка
            raise NotADirectoryError(new)
        self.cwd = new # иначе - присвоение новой рабочей директории

    # получить текущую рабочую директорию
    def getcwd(self):
        return self.cwd

    # возможность сохранить json файл VFS в реальной OC
    def save(self, filename = None):
        # берем название объекта VFS
        fn = filename or self.filename
        if not fn: # если имя было не задано - ошибка
            raise ValueError("filename required to save VFS")

        # сохраняем данные vfs в словарь
        payload = {"cwd": self.cwd, "root": self.root}

        # открываем файл на запись в папке vfs
        with open("..\\vfs\\" + fn, "w", encoding="utf-8") as f:
            # записываем данные в файл с расстоянием 2 между подэлементами
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return True

# открыть vfs из json файла
def open_vfs_from_json(filename):
    if filename and os.path.isfile(filename): # если есть имя и файл с таким именем
        with open(filename, "r", encoding="utf-8") as f: # открываем на чтение
            payload = json.load(f) # загружаем данные из json в словарь

        # достаем корневую папку или создаем пустую
        root = payload.get("root", {"type": "dir", "entries": {}})
        # создаем объект типа класса JSONVFS с аргументами корневой папки и имени файла (vfs)
        v = JSONVFS(root, filename)
        # передаем объекту текущую рабочую директорию или корневую папку
        v.cwd = payload.get("cwd", "/")
        return v # возвращаем объект vfs

    # если не получилось найти в файлах - создаем пустой fs
    return JSONVFS({"type": "dir", "entries": {}}, filename)
