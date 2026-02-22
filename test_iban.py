def check_iban(iban: str):
    clean_iban = iban.replace(" ", "").upper()
    rearranged = clean_iban[4:] + clean_iban[:4]
    numeric_iban = ""
    for char in rearranged:
        if char.isalpha():
            numeric_iban += str(ord(char) - 55)
        else:
            numeric_iban += char
    return int(numeric_iban) % 97

print("GB90:", check_iban("GB90MIDL40051522334455"))
print("GB99:", check_iban("GB99MIDL40051522334455"))
print("GB00:", check_iban("GB00MIDL40051522334455"))

