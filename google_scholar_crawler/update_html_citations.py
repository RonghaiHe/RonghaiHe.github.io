import json
import re

# 1. 读取爬虫数据
with open("results/gs_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. 构建 cites_id → 引用数 映射，处理 None 值
citesid_map = {}
for pub in data.get("publications", []):
    num_citations = pub.get("num_citations", 0)
    if num_citations is None:
        num_citations = 0
    for cid in pub.get("cites_id", []) or []:
        citesid_map[str(cid)] = int(num_citations)

# fix path typo — point to index.html
file_path = "../index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# --- find Publications HTML block (not markdown) ---
match = re.search(
    r'(<\!-- ######################### Publications ######################### -->.*?)(?=<\!-- ######################### Projects ######################### -->|\Z)',
    content,
    flags=re.S | re.I,
)
if match:
    papers_section = match.group(1)

    for cites_id, cites in citesid_map.items():
        pattern = rf'(<p[^>]*class="[^"]*abstract-links[^"]*"[^>]*>.*?cites={re.escape(cites_id)}.*?</p>)'

        def repl_paragraph(m):
            links_paragraph = m.group(1)

            # New badge html (use a stable color)
            badge_html_plain = f'<a href="https://scholar.google.com/scholar?oi=bibs&cites={cites_id}" target="_blank"><img src="https://img.shields.io/badge/Citations-{cites}-007bff" alt="Citations"></a>'

            # Detect any shields.io image whose alt contains "Citations" (handles malformed labels like "H-007bff")
            if re.search(r'<img\b(?=[^>]*src="https://img\.shields\.io/badge/)(?=[^>]*alt="[^"]*Citations[^"]*")[^>]*>', links_paragraph, flags=re.I):
                # replace the first such img tag with a proper Citations-{count}-007bff img
                links_paragraph = re.sub(
                    r'<img\b(?=[^>]*src="https://img\.shields\.io/badge/)[^>]*>',
                    f'<img src="https://img.shields.io/badge/Citations-{cites}-007bff" alt="Citations">',
                    links_paragraph,
                    count=1,
                    flags=re.I,
                )
                # ensure the surrounding href (if present) points to the correct cites_id
                links_paragraph = re.sub(
                    r'href="https://scholar\.google\.com/scholar\?[^"]*cites=[^"]*"',
                    f'href="https://scholar.google.com/scholar?oi=bibs&cites={cites_id}"',
                    links_paragraph,
                    count=1,
                    flags=re.I,
                )
                # if the img is not wrapped in an anchor, wrap it (optional): replace standalone img with the anchored version
                if not re.search(r'<a[^>]*href="https://scholar\.google\.com/scholar\?[^"]*cites=[^"]*"[^>]*>\s*<img[^>]*>\s*</a>', links_paragraph, flags=re.I):
                    # attempt to replace the img with the anchored badge_html_plain
                    links_paragraph = re.sub(
                        r'(<img\b[^>]*src="https://img\.shields\.io/badge/Citations-[^"]*"[^>]*>)',
                        badge_html_plain,
                        links_paragraph,
                        count=1,
                        flags=re.I,
                    )
            else:
                # No existing Citation badge found: append the new badge before </p>
                links_paragraph = links_paragraph.replace('</p>', f' {badge_html_plain}</p>', 1)

            return links_paragraph

        papers_section = re.sub(pattern, repl_paragraph, papers_section, flags=re.I | re.S)

    content = content.replace(match.group(1), papers_section)

# 保存
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 已使用 cites_id 更新 Publications 段落中的 Citation Badge（HTML 版）")
