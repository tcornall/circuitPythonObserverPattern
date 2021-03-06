import time, random, digitalio, board,touchio
from adafruit_debouncer import Debouncer
"""
Observable class that checks for events and handles observers registering/deregistering
#and notifications.
check() can be passed funcs that it then calls to check for events
extra args and kwargs can be passed to the class at instantiation that get passed in notifications
"""
class Observable():
    def __init__(self, name, checkFunc=None, *args, **kwargs):
        self._observers = []
        self.name = name
        self.checkFunc = checkFunc
        self.args = args
        print(args)
        self.kwargs = kwargs    #pop off any kwargs meant only for this class first
        print(kwargs)

    #check() calls checkFunc to decide if time for notifications.
    #Can use a lambda at instantiation  for this
    #IF using this observable in an eventloop, just call its check()
    def check(self):
        if self.checkFunc is not None:
            if self.checkFunc():  #if the event has happened
                self.notify()
                return True
            else:
                return False
        else:
            return False  #if no checkFunc defined, return False

    def register(self, observer):
        self._observers.append(observer)

    def deregister(self, observer):
        if observer in self._observers:    #don't try to remove it if it isn't there
            self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.notify(self.name, **self.kwargs) #send the name and the repacked args and kwargs

#make an Observable where the event is elapsed time. It repeats by default, i.e is periodic
#period is in ms and has been tested down to 1 ms OK.
class TimerObservable(Observable):
    def __init__(self, name, *args, **kwargs):
        self.period = kwargs.pop('period') #period is in ms
        #print(self.period)
        super().__init__(name, *args, **kwargs)
        self.startTime = time.monotonic() * 1000 #remember when you were started

    def check(self):  #
        now = time.monotonic() * 1000
        if now - self.startTime >= self.period: #time elapsed yet?
            self.startTime = now
            self.notify()  #Tell all your observers
            return True
        else:
            return False

"""
make an Observable where the event is an object with a 'value' attribute.
i.e. it remembers the last input and compares the current one
and check() is true of input.value has just changed from False to True
If the object is an instance of Debouncer it also does the Debouncer.update()
"""
class WentTrueObservable(Observable):
    def __init__(self, name, inp=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.inp = inp #period is in ms
        print(self.name, 'inp=', self.inp)
        if inp is not None:
            self.lastPin = inp.value #remember what the pin was

    def check(self):  #
        if self.inp is not None:
            if isinstance(self.inp, Debouncer):
                self.inp.update()    #need to do this for a debounced pin.
            inpV = self.inp.value #read the pin
            res = inpV and not self.lastPin  #in the pin now True but wasn't last time?
            self.lastPin = inpV #remember for next time
            if res:
                self.notify()  #Tell all your observers
                return True    #return result
            else:
                return False
        else:
            return False #if no pin, just say 'No'

class Observer:
    def __init__(self, name, observable):
        observable.register(self)
        self.name = name

    def notify(self, observableName, **kwargs): #args and kwargs also
        print(self.name, 'Got', 'kwargs=', kwargs, 'From', observableName)
        led = kwargs.pop('led')
        led.value = not led.value #can't print fast enough to keep up! so turn print off and flash instead

############################## main #########################
def demoLoop():
    led = digitalio.DigitalInOut(board.D13)
    led.direction = digitalio.Direction.OUTPUT
    touchA0 = touchio.TouchIn(board.A0)  #built-in capacitive sensor. needs no external h/w except 1MOhm pulldown
    touchSwA0=Debouncer(touchA0)

    testObservable = Observable('testObservable', lambda: random.randint(0,1000) < 1,\
                   'something has happened', 'call me', 12345, event='random', reason='Dunno', led=led) #an observer with a random check
    testTimer = TimerObservable('testTimer',period=1000, led=led); #period is in ms
    testWentTrue = WentTrueObservable('testWentTrue', inp=touchSwA0, led=led)

    observer1 = Observer('observer1', testObservable)
    observer2 = Observer('observer2', testWentTrue)
    observer3 = Observer('observer3', testTimer)

    observerableList = [testObservable, testWentTrue, testTimer]

    #The forever loop. Causes observable to check their events and then notify their observers.
    while True:
        for obs in observerableList:
            res=obs.check() #ask this observable to check it event. This will cause a notify if it has happened
            if res and obs.name == 'testObservable':  #did testObservable happen?
                if observer1 in testObservable._observers: #if so, remove observer1. He's finished now
                    testObservable.deregister(observer1)      #and here is how you can deregister. Would be useful to be able to reregister
        #Don't need time.sleep() here UNLESS there is a print-storm. Keep the probability of testObservable <= 1/1000
        #and keep testTimer period >10ms  and it'll be OK. Or else, remove the print()s