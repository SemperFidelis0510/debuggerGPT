from docx import Document
import sys


def docx_to_txt(path):
    try:
        document = Document(path)
        result = [p.text for p in document.paragraphs]
        return '\n'.join(result)
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    file_path = sys.argv[1]
    print(docx_to_txt(file_path))
