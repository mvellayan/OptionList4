import time, threading

def foo(name):
    print(time.ctime(), "Thread %s: starting", name)
    time.sleep(2)
    print(time.ctime(), "Thread %s: finishing", name)


print(time.ctime(), "Main1")
x = threading.Thread(target=foo, args=(1,))
x.start()
time.sleep(1)
print(time.ctime(), "Main2")

time.sleep(2)
print(time.ctime(), "Main3")
