import fitz

def read_pdf(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

text = read_pdf("document.pdf")
print(text)