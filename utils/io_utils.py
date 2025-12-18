def write_to_file(file_name, contents):
    with open(file_name, "a") as f:
        for content in contents:
            f.write(content + "\n")