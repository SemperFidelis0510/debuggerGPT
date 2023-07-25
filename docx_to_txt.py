from docx import Document
import sys


def docx_to_txt(path):
    document = Document(path)
    result = [p.text for p in document.paragraphs]
    return '\n'.join(result)


if __name__ == '__main__':
    file_path = sys.argv[1]
    print(docx_to_txt(file_path))
