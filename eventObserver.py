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
    def __init__(self,obj=None, name='simpleEvent'): #needs an object with a value attr and a function to test it with
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
        self.value = self.obj.value #and then get a new value from the obj
        return self.obj.value   #just use the event object's value as the check

"""
TimerEvent is an the event where the thing to check for is elapsed time. It repeats by default, i.e is periodic
period is in ms
Based on SimpleEvent and overrides the checkFunc()
"""
class TimerEvent(SimpleEvent):
    def __init__(self, obj=None, name='simpleEvent', period=1000, *args, **kwargs): #have a default period of 1000ms
        self.period = period #period is in ms
        #print(self.period)
        super().__init__(obj=obj, name=name, *args, **kwargs)
        self.startTime = time.monotonic() * 1000 #remember when you were started

    def checkFunc(self):  #
        now = time.monotonic() * 1000
        elapsedTime = now - self.startTime
        self.value = elapsedTime
        if elapsedTime >= self.period: #time elapsed yet?
            self.startTime = now
            return True  #returning True triggers the notification of the observers by the observable
        else:
            return False

"""
WentTrueEvent where the event is an object with a 'value' attribute.
The event remembers the last value of the object and compares to the current one
and if it has just changed from False to True its observable then notifies its observers
If the object is an instance of Debouncer it also does the Debouncer.update()
"""
class WentTrueEvent(SimpleEvent):
    def __init__(self, obj=None, name='wentTrueEvent', *args, **kwargs):
        super().__init__(obj=obj, name=name, *args, **kwargs)

    def checkFunc(self):  #
        super().checkFunc()  #call the base checkFunc to get objects value and last value
        if self.value and not self.lastValue: #was it False and just now turned True?
            return True  #
        else:
            return False


"""
Observable is a class that takes an event and calls its checkFunc and then notifies its observers
which register/deregister with it.
"""
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
        self.event.lastValue = self.event.value #remember what it was
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



class Observer:
    def __init__(self, name, observable, *args, **kwargs):
        observable.register(self)
        self.name = name
        self.args = args
        self.kwargs=kwargs
        if 'led' in self.kwargs: #was there an indicator led given to the observable? Wonder if this should be in the event instead?
            self.led = kwargs.pop('led')
        else: self.led=None
    def notify(self,observableName, event, **kwargs): #args and kwargs also
        print(self.name, 'Got event', event.name, 'value=', event.value,'lastValue=', event.lastValue, 'at time', event.timestamp, 'kwargs=', kwargs, 'From', observableName)
        if self.led: #was there an indicator led given to the observer
            self.led.value = not self.led.value #toggle led to indicate observer has been notifed

############################## main #########################
def demoLoop():
#indicators
    redLed = digitalio.DigitalInOut(board.D13)
    redLed.direction = digitalio.Direction.OUTPUT

#objects that cause events
    touchA0 = touchio.TouchIn(board.A0)  #built-in capacitive sensor. needs no external h/w except 1MOhm pulldown
    touchSwA0=Debouncer(touchA0)

#Events that determine if the objects they monitor hae done something interesting
    simpleEvent = SimpleEvent(obj=touchSwA0) #Watch the touch sw on A0 and report if it IS True
    timerEvent = TimerEvent(name='timerEvent', period=3000)  #this one doesn't have an 'obj' as it monitors time
    wentTrueEvent = WentTrueEvent(obj=touchSwA0, name='wentTrueEvent') #Watch the touch sw on A0 and report if it GOES True

#Observables that monitor events and notify registered observers
    testSimpleEventObservable = Observable(name='testSimpleEventObservable', event=simpleEvent)
    testTimerEventObservable = Observable(name='testTimerEventObservable', event=timerEvent)
    testWentTrueObservable = Observable(name='testWentTrueObservable', event=wentTrueEvent)

#observers that get notifications from observables and do something about it
    simpleObserver = Observer('simpleObserver', testSimpleEventObservable, led=redLed) #who the observable should notify if event happens
    timerObserver = Observer('timerObserver', testTimerEventObservable, led=redLed)
    wentTrueObserver = Observer('wentTrueObserver', testWentTrueObservable, testWentTrueObservable, led=redLed)

#list of observables to be checked in the 'forever' loop
    #observerableList = [testSimpleEventObservable, testTimerEventObservable, testWentTrueObservable]
    observerableList = [testWentTrueObservable]

#The forever loop. Causes observable to check their events and then notify their observers.
    while True:
        for obs in observerableList:
            res=obs.check() #ask this observable to check it event. This will cause a notify if it has happened
        #time.sleep(0.1) #might need this if you are calling print every time else it stalls Mu