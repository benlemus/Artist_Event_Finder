with open('supported_countries.txt', 'r') as file:
    line = file.readline()
    
    splits = line.split(',')

    for split in splits:
        words = split.split('(')

        second = words[1].replace(')', '"')
        full = f'"{words[0].strip()}": "{second.strip()},' 
        with open('new_countries.txt', 'a') as file2:
            file2.write(f'\n{full}')

