# Matlab Classify Modulator

This application implement the ADI Matlab generated classify modulator with the holoscan basic network operator
and expect to receive the raw data samples on a UDP port.

### Configuration

The application is configured using the file matlab_classify_modulator.yaml, where RX will receive packets on a UDP port. 
Depending on how the machine is configured, the IP and UDP port likely need to be configured. All other settings do not need to be changed.

The application also store the classification ouput on a file defined in matlab_classify_modulator.yaml

Please refer to the basic network operator documentation for more configuration information.

The application expect to receive 4 complex (I / Q) channels with int16_t data type.

### Requirements

This application requires:
1. Linux

### Build Instructions

Please refer to the top level Holohub README.md file for information on how to build this application.

### Run Instructions

Running the sample uses the standard HoloHub `run` script:


```bash
# Start the receiver
./run launch basic_networking_ping <language> --extra_args basic_networking_ping_rx.yaml
# Start the transmitter
./run launch basic_networking_ping <language> --extra_args basic_networking_ping_tx.yaml
```

Language can be either C++ or Python.
