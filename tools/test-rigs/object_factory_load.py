import sys, types
fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake
def load(path):
    mod = types.ModuleType("of"); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod
