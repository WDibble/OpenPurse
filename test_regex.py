import re
clean_iban = "GB99MIDL40051522334455"
match = re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", clean_iban)
print("Match?", bool(match))
