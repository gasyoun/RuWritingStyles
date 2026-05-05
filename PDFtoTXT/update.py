import re
import unicodedata

def normalize_text(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace('\xad', '').replace('\u200b', '')
    text = re.sub(r'([а-яА-Яa-zA-Z])-\s*\n\s*([а-яА-Яa-zA-Z])', r'\1\2', text)
    return text

def fix_initials(name):
    for lat, cyr in zip('ABCEHKMOPTX', 'АВСЕНКМОРТХ'):
        name = re.sub(r'\b' + lat + r'\.', cyr + '.', name)
    return name.replace('Вiлкул', 'Вилкул')

def get_search_regex(name, section):
    name = name.replace('*', '').strip()
    words = [w for w in re.split(r'[\s,]+', name) if w]
    if not words: return None
    
    common_names = {"Иван", "Василий", "Юрий", "Андрей", "Георгий", "Изяслав", "Анна"}
    if section == 2 and words[0] in common_names and len(words) > 1:
        w1, w2 = words[0], words[1]
        if len(w2) > 4: w2 = w2[:-2] 
        return r'\b' + w1 + r'\b.{0,30}\b' + w2 + r'[а-яА-Я]*\b'
    
    surname = words[0]
    if surname == "Даль": return r'\b(?:Даль|Даля|Далю|Далем|Дале)\b'
    if surname == "Гак": return r'\bГак[ауеом]?\b'
    if surname == "Рену": return r'\bРену\b'
    
    stem = surname
    for suf in ['ский', 'ская', 'ского', 'ской', 'ским', 'ские', 'ских', 'скими', 
                'цкий', 'цкая', 'цкого', 'цкой', 'цким', 'цкие', 'цких', 'цкими', 
                'ова', 'ева', 'ина', 'ову', 'еву', 'ину', 'овой', 'евой', 'иной', 
                'овым', 'евым', 'иным', 'ов', 'ев', 'ин', 'ый', 'ий', 'ая', 'яя']:
        if surname.endswith(suf) and len(surname) - len(suf) >= 3:
            stem = surname[:-len(suf)]
            break
    else:
        if len(surname) > 5: stem = surname[:-2]
        elif len(surname) > 4: stem = surname[:-1]
        
    return r'\b' + stem + r'[а-яА-Яa-zA-Z]*\b'

def update_index(txt_file="AAZ_Zametki_2025.txt", md_file="AAZ_Zametki_2025-index.md", out_file="AAZ_Zametki_2025-index-updated.md", missing_file="AAZ_Zametki_2025-index-missing.md"):
    with open(txt_file, 'r', encoding='utf-8') as f:
        clean_txt = normalize_text(f.read())

    page_markers = []
    for match in re.finditer(r'^[ \t]*(\d+)[ \t]*$', clean_txt, re.MULTILINE):
        page_markers.append((match.start(), int(match.group(1))))

    with open(md_file, 'r', encoding='utf-8') as f:
        md_lines = f.readlines()

    updated_lines = []
    missing_lines = ["# Имена, исключенные из издания 2025 года\n\n"]
    section = 1
    
    # Множество для отслеживания уже обработанных имен (защита от задвоения)
    seen_names = set()
    
    for line in md_lines:
        if line.startswith('#'):
            missing_lines.append('\n' + line)

        if "Раздел 2" in line:
            section = 2
            
        match = re.match(r'^(\s*-\s+)(.*)$', line.rstrip())
        if match:
            prefix = match.group(1)
            full_name_raw = match.group(2)
            
            original_name = re.sub(r'\s+([,\d\s]+|\[не найдено\])$', '', full_name_raw).strip()
            if not original_name:
                updated_lines.append(line)
                continue

            # Если мы уже находили этого человека в этом разделе — пропускаем дубликат
            if (section, original_name) in seen_names:
                continue
            seen_names.add((section, original_name))

            search_name = fix_initials(original_name)
            pattern = get_search_regex(search_name, section)
            
            if not pattern:
                updated_lines.append(f"{prefix}{original_name}\n")
                continue
                
            found_pages = set()
            for occ in re.finditer(pattern, clean_txt, re.IGNORECASE):
                match_str = occ.group(0)
                if match_str and match_str[0].islower():
                    continue
                    
                pos = occ.start()
                current_page = None
                for marker_pos, p_num in page_markers:
                    if marker_pos < pos:
                        current_page = p_num
                    else:
                        break
                if current_page is not None:
                    found_pages.add(current_page)
                    
            if found_pages:
                pages_str = ", ".join(map(str, sorted(list(found_pages))))
                updated_lines.append(f"{prefix}{original_name} {pages_str}\n")
            else:
                missing_lines.append(f"{prefix}{original_name}\n")
        else:
            updated_lines.append(line)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)

    with open(missing_file, 'w', encoding='utf-8') as f:
        f.writelines(missing_lines)

if __name__ == "__main__":
    update_index()