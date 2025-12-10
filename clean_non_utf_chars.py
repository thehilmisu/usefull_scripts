import os
import chardet

def is_utf8(text):
    try:
        text.encode('utf-8').decode('utf-8')
    except UnicodeDecodeError:
        return False
    return True

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
    return result['encoding']

def clean_file(file_path, encoding):
    with open(file_path, 'r', encoding=encoding) as file:
        lines = file.readlines()

    cleaned_lines = []
    for line in lines:
        #cleaned_line = line.encode(encoding, errors='ignore').decode(encoding)
        cleaned_line = ''.join(c for c in line if is_utf8(c))
        cleaned_lines.append(cleaned_line)

    if encoding == "ISO-8859-1":
        new_encoding  = 'utf-8'
    else:
        new_encoding  = encoding

    with open(file_path, 'w', encoding=new_encoding) as file:
        file.writelines(cleaned_lines)

def main():
    project_directory = '../code/src/'  # Change this to your project directory

    for root, _, files in os.walk(project_directory):
        for filename in files:
            if filename.endswith('.c') or filename.endswith('.h'):
                file_path = os.path.join(root, filename)
                try:
                    encoding = detect_encoding(file_path)
                    print(f"cleaning file {file_path} with encoding {encoding}")
                    clean_file(file_path, encoding)
                except Exception as e:
                    print(f"Error processing file: {file_path}")
                    print(e)

if __name__ == "__main__":
    main()
