# homeassistant-selve
Home Assistant Custom component to manage Selve devices


It can be used with the [python-selve library](https://github.com/gpulido/python-selve) and a usb-rtf gateway.
Just plug a gateway on the same pc where Home assistant is running, check for the usb interface and add the following to the ha configuration file (change ttyUSB0 for the right interface)
```
selve:
  port: /dev/ttyUSB0
```
