import sys
print(f"sys.argv: {sys.argv}")
print(f"sys.executable: {sys.executable}")
command = [sys.executable] + sys.argv[1:]
print(f"Command formed: {command}")
