
with open('d:/web development/quant/app/templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Simple div counting
    opens = line.count('<div')
    closes = line.count('</div>')
    
    for _ in range(opens):
        stack.append(line_num)
    
    for _ in range(closes):
        if not stack:
            print(f"Extra closing div at line {line_num}")
        else:
            stack.pop()
            if not stack:
                print(f"Stack empty at line {line_num}")

if stack:
    print(f"Unclosed divs starting at: {stack}")
