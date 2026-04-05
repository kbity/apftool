import random

apf2data = "" # create blank image
randomletters = "qwertyuiopasdfghjklzxcvbnm "
randomhexchars = "1234567890ABCDEF"

apf2data += "APERTURE IMAGE FORMAT (c) 1993" # add header
w = random.randint(1, 999)
h = random.randint(1, 999)
header = []
header.append(f"{w}x{h}")
flags = ""
if (random.randint(1, 4) == 1):
    flags+= "l"
if (random.randint(1, 2) == 1):
    flags+= "t"
header.append(flags)
header.append(str(random.randint(1, h)))
if (random.randint(1, 2) == 1):
    randomdesc = ""
    for _ in range(1, random.randint(1, 100)):
        randomdesc += random.choice(randomletters)
    header.append(randomdesc)
apf2data += "\n"+",".join(header)

if 'l' in flags:
    rcol = ""
    for _ in range(0,6):
        rcol += random.choice(randomhexchars)
    pal = f"{rcol}."
    rcol = ""
    for _ in range(0,6):
        rcol += random.choice(randomhexchars)
    pal += rcol
else:
    pal = ""
    for i in range(0, 95):
        rcol = ""
        for _ in range(0,6):
            rcol += random.choice(randomhexchars)
        pal += f"{chr(i+32)}{rcol}"

apf2data += "\n"+pal

# print(apf2data) # output random af2 header

fent = random.randint(1, 99801)
if not 'l' in flags:
    fent = fent*2

data = ""
for _ in range(0,fent):
    data += chr(random.randint(32, 126))

apf2data += "\n"+data

randomname = ""
for _ in range(1, random.randint(1, 45)):
    randomname += random.choice(randomletters)

print(f"{randomname}.apf2")
with open(f"{randomname}.apf2", "w") as text_file:
    text_file.write(apf2data)