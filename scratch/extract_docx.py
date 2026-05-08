import zipfile
import xml.etree.ElementTree as ET
import os

def extract_comments(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as z:
            # Word comments are usually in word/comments.xml
            if 'word/comments.xml' not in z.namelist():
                return "No comments found in this document."
                
            xml_content = z.read('word/comments.xml')
            tree = ET.fromstring(xml_content)
            
            # Namespace for Word Comments
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            comments = []
            for c in tree.findall('.//w:comment', ns):
                author = c.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author', 'Unknown')
                # Extract text from comment paragraphs
                para_texts = []
                for p in c.findall('.//w:p', ns):
                    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                    if texts:
                        para_texts.append("".join(texts))
                
                comment_text = "\n".join(para_texts)
                comments.append(f"Author: {author}\nText: {comment_text}\n---")
            
            return "\n".join(comments)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    path = "CommentaryStrategies_Tronsky30_Kostina.docx"
    
    # Extract body text
    # (already done, but let's keep it tidy)
    
    # Extract comments
    notes = extract_comments(path)
    with open("scratch/kostina_notes.md", "w", encoding="utf-8") as f:
        f.write("# Замечания Костиной (Word Comments)\n\n")
        f.write(notes)
    
    print("Successfully extracted comments to scratch/kostina_notes.md")
