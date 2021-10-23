

from threading import Thread, Condition
import time
import random

queue = []
MAX_NUM = 5
condition = Condition()
# count = 0
def producer():
        print("producer fucnction get")
        nums = range(5)
        global queue
        while True:
            condition.acquire()
            if len(queue) == MAX_NUM:
                print("Queue full, producer is waiting") 
                condition.notify()
                condition.release()
                consumer()
                print("Ntified the producer")
                condition.wait()
                
            num = random.choice(nums)
            queue.append(num)
            print("Produced", num)
            time.sleep(random.random())

def consumer():
        print("consumer function get called.")
        global queue
        while True:
            condition.acquire()
            if not queue:
                print("Nothing in queue, consumer is waiting")               
                condition.notify()
                condition.release()
                print("Notified the Producer")
                producer()
                #condition.wait()
            num = queue.pop(0)
            print("Consumed", num)
            # condition.notify()
            # condition.release()
            time.sleep(random.random())

producer()