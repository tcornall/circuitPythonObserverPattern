import time, random, digitalio, board,touchio
from adafruit_debouncer import Debouncer
"""
Observable class that checks for events and handles observers registering/deregistering
#and notifications.
events are self-contained descriptions of what and how to check to see if they have happened
check() can be passed funcs that it then calls to check for events
extra args and kwargs can be passed to the class at instantiation that get passed in notifications
"""
#pass around an event type that contains info about what happened and when as well as the check function.
#The event contains an object that has a value attr, a checkFunc, value, lastValue and timestamp
#that allows it to decide if it has happened, when and why
class SimpleEvent:   # a base event type with a simple checFunc
    def __init__(self,obj, name='simpleEvent'): #needs an object with a value attr and a function to test it with
        self.name = name
        self.value = 0 #the value that caused the event
        self.obj = obj #obj must have an attribute of 'value' or it will cause issues.
                       #note that in real python lambdas and other functions can have attributes!
                       # e.g. f=lambda:None f.value = False.  BUT NOT IN CIRCUITPYTHON
        self.timestamp = 0 #the time at which the event went true
        self.lastValue = 0 #the value before the event went true
    def checkFunc(self): #default check function. Over-ride it in the children classes
        update = getattr(self.obj, "update", None)  #like a Debouncer has an update function that needs to be called
        if callable(update):
            update()    #need to do this e.g. for a debounced pin.
        self.lastValue = self.value #remeber what it was
        self.value = self.obj.value #and then get a new value from the obj
        return self.obj.value   #just use the event object's value as the check

class Observable:
    def __init__(self, name, event, *args, **kwargs):
        self._observers = []
        self.name = name
        self.event = event
        self.args = args
        print(args)
        self.kwargs = kwargs    #pop off any kwargs meant only for this class first
        print(kwargs)

    #check() calls events checkFunc to decide if time for notifications.
    #When using this observable in an eventloop, just call its check()
    def check(self):
        res = self.event.checkFunc()  #remember the result, not just true or false
        if res:  #if the event has happened
            self.event.timestamp = time.monotonic()
            self.notify()  #pass the result on to the observer, with the event info
            return True
        else:
            return False

    def register(self, observer):
        self._observers.append(observer)

    def deregister(self, observer):
        if observer in self._observers:    #don't try to remove it if it isn't there
            self._observers.remove(observer)

    def notify(self): #tell observers that check was true and pass on the result that caused it
        for observer in self._observers:
            observer.notify(self.name, self.event,**self.kwargs) #send the name and the repacked args and kwargs

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
        el = now - self.startTime
        if el >= self.period: #time elapsed yet?
            self.startTime = now
            self.notify(res=el)  #Tell all your observers how much time actually elapsed
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
                self.notify(res=inpV)  #Tell all your observers
                return True    #return result
            else:
                return False
        else:
            return False #if no pin, just say 'No'

class Observer:
    def __init__(self, name, observable):
        observable.register(self)
        self.name = name
    def notify(self,observableName, event, **kwargs): #args and kwargs also
        print(self.name, 'Got event', event.name, 'value=', event.value,'lastValue=', event.lastValue, 'at time', event.timestamp, 'kwargs=', kwargs, 'From', observableName)
        if 'led' in kwargs: #was there an indicator led given to the observable? Wonder if this should be in the event instead?
            led = kwargs.pop('led')
            led.value = not led.value #toggle led to indicate observer has been notifed

############################## main #########################
def demoLoop():
    led = digitalio.DigitalInOut(board.D13)
    led.direction = digitalio.Direction.OUTPUT
    touchA0 = touchio.TouchIn(board.A0)  #built-in capacitive sensor. needs no external h/w except 1MOhm pulldown
    touchSwA0=Debouncer(touchA0)
    simpleEvent = SimpleEvent(obj=touchSwA0) #Watch the touch sw on A0 and report if it goes True

    testSimpleEventObservable = Observable(name='simpleEventObserver', event=simpleEvent, led=led)

    observer1 = Observer('observer1', testSimpleEventObservable)

    observerableList = [testSimpleEventObservable]

    #The forever loop. Causes observable to check their events and then notify their observers.
    while True:
        for obs in observerableList:
            res=obs.check() #ask this observable to check it event. This will cause a notify if it has happened
            time.sleep(0.1) #need this if you are calling print