# circuitPythonObserverPattern
Implementing the observerPattern on an ItsyBitsy with CircuitPython to make polling for and handling events more efficient.

Because CircitPython has no asyncio and no other examples of structured concurrency that I can find, I thought the observer pattern would provide an efficient means of polling for events like timers and digital inputs.

Also, circuitPython doen't have any built-in form of a delay function that can nonetheless allow other code to keep running, other than polling for events in a loop. The observer pattern facilitates this and simplifies the code by putting the event checking and notification into the 'observables' class(es) and the event handling into the 'observer' class(es).  (Because a variety of classes can inherit from the base class to make interesting variations, implementing different observer behaviour such as 'persistant' and 'one-shot' and different event checking in the observable like the stateless 'some expression is True' or the stateful 'some expression only just then became True') Observables can use a fixed expression in the check() or be passed one via a lambda function.

The observerPattern.py defines classes for observables that check for events by calling a function that was either passed to the class during instantiation or was built-in to a child class by overriding the base check().  The observer class instances then register with the observable and get notified when observable.check() returns True.

There can be many types of observables. Two given in the examples code are a periodic  timer and one that gets a lambda function as its check(). Others that might be a added are one-shot timer and one to check digital input pins.

The demoObserverPattern.py implements a 'while True:' loop that instantiates a list of observables and associated observers and calls the 'check()' on each observable in the list without need for a time.sleep() to slow things down. If the check() in each observable is True, the observable instance handles notifying each observer that is registered with it and the observer instances decide what to do about it.

14-Sept-2020 I added the event classes to more easily encapsulate event checkable objects and the checkFunc() and keep some state such as lastValue and timestamp of last time the event happened.
15-Sept-2020 Fixed and testd the WentTrueEvent so that observers are only notified the first tme the event's object value goes True. Good for buttons and such.
