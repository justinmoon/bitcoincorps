
# coding: utf-8

# # Homework
# 
# I created a file in the root of our repository called packets.txt
# 
# It's a binary file composed of raw Bitcoin Network messages.
# 
# Below is some code which can read the messages and print out a little statement about each message.
# 
# I want you to try to parse some of these messages. This is open-ended homework. See how far you get. Ask questions in Slack. I'll give you more prompts as the weeks progresses.

# In[4]:


from ibd.one.complete import Packet, FakeSocket
# Packet was called Message in the first lesson, but I renamed it ...

packets = open('packets.txt', 'rb').read()
fake_socket = FakeSocket(packets)

while True:
    try:
        pkt = Packet.from_socket(fake_socket)
        print(f"{pkt.command} with {len(pkt.payload)}-byte payload")
    except RuntimeError:
        print("reached the end")
        break

