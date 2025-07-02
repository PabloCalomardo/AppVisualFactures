def parse_txt_file(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            # Assuming each line in the .txt file is a record
            record = line.strip().split(',')
            data.append(record)
    return data