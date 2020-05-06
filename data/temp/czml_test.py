# Import the library
from czml import czml

# Initialize a document
doc = czml.CZML()

# Create and append the document packet
packet1 = czml.CZMLPacket(id='document', name="czml", version='1.0')
doc.packets.append(packet1)

# Create and append a billboard packet
packet2 = czml.CZMLPacket(id='rect', name="visibility")
bb = czml.Billboard(scale=0.7, show=True)
bb.image = 'http://localhost/img.png'
bb.color = {'rgba': [0, 255, 127, 55]}
packet2.billboard = bb
doc.packets.append(packet2)

# Write the CZML document to a file
filename = "example.czml"
doc.write(filename)