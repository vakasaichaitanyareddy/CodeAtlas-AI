import re

text = """### [Source 1] File: docs/design.rst (Lines 136-229)
```
Design Decisions in Flask
```

### [Source 2] File: src/flask/ctx.py (Lines 154-206, Symbol: copy_current_request_context [FUNCTION])
```python
def copy_current_request_context():
    pass
```"""

pat = re.compile(
    r"###\s+\[Source\s+\d+\]\s+File:\s+([A-Za-z0-9_\-\./]+\.[a-zA-Z0-9]+)\s+\(Lines\s+(\d+)-(\d+)(?:,\s*Symbol:\s*([^\[\n\)]+?))?(?:\s*\[([^\]]+)\])?\)\s*```[a-zA-Z0-9]*\n(.*?)```",
    re.DOTALL
)

for m in pat.finditer(text):
    print("Match:", m.group(1), f"L{m.group(2)}-L{m.group(3)}", "Symbol:", m.group(4))
