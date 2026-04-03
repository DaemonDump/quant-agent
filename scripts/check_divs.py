
with open('d:/web development/quant/app/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

open_divs = content.count('<div')
close_divs = content.count('</div')

print(f"Open divs: {open_divs}")
print(f"Close divs: {close_divs}")

# Trace nesting
stack = []
lines = content.split('\n')
for i, line in enumerate(lines):
    # This is a very rough check
    if '<div' in line:
        stack.append(i+1)
    if '</div>' in line:
        if stack:
            stack.pop()
        else:
            print(f"Extra closing div at line {i+1}")

if stack:
    print(f"Unclosed divs starting at lines: {stack}")
