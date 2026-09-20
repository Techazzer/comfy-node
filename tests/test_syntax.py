from pathlib import Path
import py_compile

root = Path(__file__).resolve().parents[1]
py_compile.compile(str(root / "__init__.py"), doraise=True)
print("python syntax ok")
