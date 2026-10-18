import re

with open('portal/application/views/chat_view.php', 'r', encoding='utf-8') as f:
    php_html = f.read()

rendered = php_html
rendered = re.sub(r'<\?php\s+echo\s+html_escape\(\$title\);\s+\?>', 'Report Copilot | Cognitive Market Research', rendered)
rendered = re.sub(r'<\?php\s+echo\s+site_url\(\);\s+\?>', '#', rendered)
rendered = re.sub(r'<\?php\s+echo\s+date\(\'Y\'\);\s+\?>', '2026', rendered)
rendered = re.sub(r'<\?php\s+echo\s+site_url\(["\']chat/send["\']\);\s+\?>', 'http://127.0.0.1:8000/api/v1/chat', rendered)
rendered = re.sub(r'<\?php\s+echo\s+site_url\(["\']chat/feedback["\']\);\s+\?>', 'http://127.0.0.1:8000/api/v1/feedback', rendered)

options_html = '''
<option value="C-01">[C-01] Global Water Solutions (All Reports)</option>
<option value="C-02">[C-02] City of Austin Water Utility (R-101, R-103)</option>
<option value="C-03">[C-03] AquaTech Industrial Corp (R-104, R-106)</option>
<option value="C-04">[C-04] Blue Delta Infrastructure (R-101 only)</option>
<option value="C-05">[C-05] Northwind Utilities (R-105)</option>
<option value="C-06">[C-06] Public Visitor (Public Excerpts only)</option>
'''
rendered = re.sub(r'<\?php\s+foreach\s+\(\$clients\s+as\s+\$cid\s+=>\s+\$cname\):.*?\<\?php\s+endforeach;\s+\?>', options_html, rendered, flags=re.DOTALL)

with open('portal/preview.html', 'w', encoding='utf-8') as f:
    f.write(rendered)

print('Generated portal/preview.html successfully!')
