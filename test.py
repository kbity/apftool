from wbmptool import decodewbmp

# apf
# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'input.apf'
#with open(file_path, 'r') as f:
#    file_content = f.read()
#decodedapf = decodeapf(file_content)
#with open("output.png", "wb") as f:
#    f.write(decodedapf)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
#file_path = 'output.png'
#with open(file_path, "rb") as f:
#    data = io.BytesIO()
#    data = f.read()

#encodedapf = encodeapf(data, 3, True)
#with open("output.apf", "w") as f:
#    f.write(encodedapf)



# af2
# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'input.af2'
#with open(file_path, 'r') as f:
#    file_content = f.read()
#decodedapf = decodeaf2(file_content, 'PNG')
#with open("output.png", "wb") as f:
#    f.write(decodedapf)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
#file_path = 'input.png'
#with open(file_path, "rb") as f:
#    data = io.BytesIO()
#    data = f.read()

#encodedapf = encodeaf2(data, 9, False, False, True)
#with open("output.af2", "w") as f:
#    f.write(encodedapf)



# wbmp
# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'input.wbmp'
#with open(file_path, 'rb') as f:
#    file_content = f.read()
#decodedwbmp = decodewbmp(file_content)
#with open("output.png", "wb") as f:
#    f.write(decodedwbmp)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
#file_path = 'output.png'
#with open(file_path, "rb") as f:
#    data = io.BytesIO()
#    data = f.read()

#encodedwbmp = encodewbmp(data)
#with open("output.wbmp", "w") as f:
#    f.write(encodedwbmp)
