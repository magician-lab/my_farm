import re
src = open('app.py', encoding='utf-8').read()
routes = re.findall(r'@app\.route\("([^"]+)"', src)
print('\n'.join(sorted(set(routes))))
