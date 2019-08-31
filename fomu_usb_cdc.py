#!/usr/bin/env python3
"""Based on DummyUSB from ValentyUSB.
"""
from enum import IntEnum

from migen import *
from migen.genlib import fsm

from valentyusb.usbcore.endpoint import EndpointType, EndpointResponse
from valentyusb.usbcore.pid import PID, PIDTypes
from valentyusb.usbcore.sm.transfer import UsbTransfer
from valentyusb.usbcore.cpu.usbwishbonebridge import USBWishboneBridge

class FomuUSBCDC(Module):
    """
        Basic CDC implementation for the Fomu 6502 core.
    """

    def __init__(self, iobuf, debug=False, vid=0x1209, pid=0x5bf0,
        product="Fomu 6502 Bridge",
        manufacturer="Dark Devices"):
        
        # USB Core
        self.submodules.usb_core = usb_core = UsbTransfer(iobuf)
        if usb_core.iobuf.usb_pullup is not None:
            self.comb += usb_core.iobuf.usb_pullup.eq(1)
        self.iobuf = usb_core.iobuf

        # SETUP packets contain a DATA segment that is always 8 bytes
        # (for our purposes)
        bmRequestType = Signal(8)
        bRequest = Signal(8)
        wValue = Signal(16)
        wIndex = Signal(16)
        wLength = Signal(16)
        setup_index = Signal(4)

        address = Signal(7, reset=0)
        self.comb += usb_core.addr.eq(address),

        def make_usbstr(s):
            usbstr = bytearray(2)
            # The first byte is the number of characters in the string.
            # Because strings are utf_16_le, each character is two-bytes.
            # That leaves 126 bytes as the maximum length
            assert(len(s) <= 126)
            usbstr[0] = (len(s)*2)+2
            usbstr[1] = 3
            usbstr.extend(bytes(s, 'utf_16_le'))
            return list(usbstr)

        usb_descriptors = {
            0x100: [ # usb_device_descriptor
                    0x12, # bLength
                    0x01, # bDescriptorType
                    0x00, 0x02, # bcdUSB
                    0x02, # USB class CDC
                    0x00, # Subclass
                    0x00, # Protocol
                    0x40, # bMaxPacketSize0
                    (vid>>0)&0xff, (vid>>8)&0xff, # Vendor ID
                    (pid>>0)&0xff, (pid>>8)&0xff, # Product ID
                    0x01, 0x01, # bcdDevice (version)
                    0x01, # iManufacturer
                    0x02, # iProduct
                    0x00, # iSerialNumber
                    0x01  # bNumConfigurations
            ],

            0x200: [ # usb_config_descriptor
                0x09, # bLength
                0x02, # bDescriptorType
                0x12, 0x00, # wTotalLength
                0x02, # bNumInterfaces
                0x01, # bConfigurationValue
                0x00, # iConfiguration
                0x80, # bmAttributes
                50, # bMaxPower (50=100mA)
                
                # interface descriptor for CDC
                0x09, # bLength
                0x04, # bDescriptorType
                0x00, # bInterfaceNumber
                0x00, # bAlternateSetting
                0x01, # bNumEndpoints
                0x02, # bInterfaceClass - CDC
                0x02, # bInterfaceSubClass - CDC ACM
                0x01, # bInterfaceProtocol - CDC AT-protocol
                0x00, # iInterface
            
                # Header functional descriptor
                0x05, # bLength
                0x24, # bDescriptorType - CS_INTERFACE
                0x00, # bDescriptorSubType - USB_CDC_TYPE_HEADER
                0x10, 0x01, # bcdCDC Spec release number

                # Call Management Functional Descriptor
                0x05, # bFunctionLength
                0x24, # bDescriptorType - CS_INTERFACE
                0x01, # bDescriptorSubType - USB_CDC_TYPE_CALL_MANAGEMENT
                0x00, # bmCapabilities
                0x01, # bDataInterface: 1

                # ACM Functional Descriptor
                0x04, # bFunctionLength
                0x24, # bDescriptorType - CS_INTERFACE
                0x02, # bDescriptorSubType - USB_CDC_TYPE_ACM
                6,    # bmCapabilities

                # Union Functional Descriptor - should be needed but
                # seems to work if omitted. This allows us to fit
                # the descriptor in under 64 bytes.
                #0x05, # bFunctionLength
                #0x24, # bDescriptorType - CS_INTERFACE
                #0x06, # bDescriptorSubType - USB_CDC_TYPE_UNION
                #0x00, # bMasterInterface: Communication class interface
                #0x01, # bSlaveInterface0: Data class interface

                # Endpoint Descriptor
                0x07, # bLength
                0x05, # bDescriptorType - USB_DT_ENDPOINT
                0x81, # bEndpointAddress
                0x03, # bmAttributes - USB_ENDPOINT_ATTR_INTERRUPT
                0x10, 0x00, # wMaxPacketSize
                0xFF, # bInterval

                # Interface Descriptor, CDC data.
                0x09, # bLength
                0x04, # bDescriptorType - USB_DT_INTERFACE
                0x01, # bInterfaceNumber
                0x00, # bAlternateSetting
                0x02, # bNumEndpoints
                0x0A, # bInterfaceClass - USB_CLASS_DATA
                0x00, # bInterfaceSubClass
                0x00, # bInterfaceProtocol
                0x00, # iInterface

                # Endpoint Descriptor
                0x07, # bLength
                0x05, # bDescriptorType - USB_DT_ENDPOINT
                0x82, # bEndpointAddress
                0x02, # bmAttributes - USB_ENDPOINT_ATTR_BULK
                0x40, 0x00, # wMaxPacketSize
                0x01, # bInterval
                
                # Endpoint Descriptor
                0x07, # bLength
                0x05, # bDescriptorType - USB_DT_ENDPOINT
                0x02, # bEndpointAddress
                0x02, # bmAttributes - USB_ENDPOINT_ATTR_BULK
                0x40, 0x00, # wMaxPacketSize,
                0x01, # bInterval
                ],
        0x300: [ # usb_string0_descriptor
                    0x04, 0x03, 0x09, 0x04,
                ],
        0x301: make_usbstr(manufacturer),
        0x302: make_usbstr(product),
        0x3EE: [ # usb_msft_descriptor 
                0x12, # bLength
                0x03, # bDescriptorType - String
                0x4D, 0x00, # String, "MSFT100"
                0x53, 0x00,
                0x46, 0x00,
                0x54, 0x00,
                0x31, 0x00,
                0x30, 0x00,
                0x30, 0x00,
                0x20, # Vendor Code
                0x00 # Padding
            ],
        0xff00: [ # usb_bos_descriptor 
                0x05, 0x0f, 0x1d, 0x00, 0x01, 0x18, 0x10, 0x05,
                0x00, 0x38, 0xb6, 0x08, 0x34, 0xa9, 0x09, 0xa0,
                0x47, 0x8b, 0xfd, 0xa0, 0x76, 0x88, 0x15, 0xb6,
                0x65, 0x00, 0x01, 0x02, 0x01,
                ],
        
        }

        # Windows WCID descriptor - not accessed through
        # normal get descriptor requests, but through a special
        # vendor request instead.
        usb_wcid_descriptor = [
            40, 0, 0, 0, # Length
            0x00, 0x01, # Version
            0x04, 0x00, # Compatibility ID descriptor index
            0x01, # Number of sections
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # 7 reserved bytes.
            0x00, # Interface number
            0x01, # Reserved
            ord('W'), ord('I'), ord('N'), ord('U'), ord('S'), ord('B'), 0, 0, # Compatible ID
            0,0,0,0,0,0,0,0, # Sub-compatible ID
            0, 0, 0, 0, 0, 0, # Reserved
            ]
            
        # Default (i.e. blank) device status report.
        usb_device_status_report = [
            0x00, 0x00,
            ]

        # Patch the wTotalLength value for the config descriptor.
        usb_descriptors[0x200][2] = (len(usb_descriptors[0x200])     ) & 0xFF # LSB
        usb_descriptors[0x200][3] = (len(usb_descriptors[0x200]) >> 8) & 0xFF  # MSB

        # Map all the descriptors into a single block of memory,
        # and store the address of the start of each one.
        descriptor_start_address = {}
        next_address = 0
        memory_contents = []
        for descriptor_id, descriptor_data in usb_descriptors.items():
            descriptor_start_address[descriptor_id] = next_address
            memory_contents += descriptor_data
            descriptor_length = len(descriptor_data)
            next_address += descriptor_length
            if descriptor_length > 63:
                raise ValueError("Descriptor",descriptor_id,"is too long (",descriptor_length,"> 64 (wMaxPacketSize) and won't work.")
            print("Mapped descriptor", descriptor_id,"to",hex(next_address))

        # We also need to store the WCID descriptor and default status report here.
        usb_wcid_descriptor_address = next_address
        memory_contents += usb_wcid_descriptor
        next_address += len(usb_wcid_descriptor)

        usb_device_status_report_address = next_address
        memory_contents += usb_device_status_report
        next_address += len(usb_device_status_report)

        # Set up the actual buffer.
        out_buffer = self.specials.out_buffer = Memory(8, len(memory_contents), init=memory_contents)
        descriptor_bytes_remaining = Signal(6) # Maximum number of bytes in USB is 64
        self.specials.out_buffer_rd = out_buffer_rd = out_buffer.get_port(write_capable=False, clock_domain="usb_12")

        # Indicates DATA1 or DATA0
        dtb_polarity = Signal()

        last_start = Signal()

        # Set to 1 if we have a response that matches the requested descriptor
        have_response = self.have_response = Signal()

        # Needs to be able to index Memory
        response_addr = Signal(9)
        response_len = Signal(7)
        response_ack = Signal()

        # Used to respond to Transaction stage
        transaction_queued = Signal()
        new_address = Signal(7)

        # Generate debug signals, in case debug is enabled.
        debug_packet_detected = Signal()
        debug_data_mux = Signal(8)
        debug_data_ready_mux = Signal()
        debug_sink_data = Signal(8)
        debug_sink_data_ready = Signal()
        debug_ack_response = Signal()

        # Delay the "put" signal (and corresponding data) by one cycle, to allow
        # the debug system to inhibit this write.  In practice, this doesn't
        # impact our latency at all as this signal runs at a rate of ~1 MHz.
        data_recv_put_delayed = self.data_recv_put_delayed = Signal()
        data_recv_payload_delayed = self.data_recv_payload_delayed = Signal(8)
        self.sync += [
            data_recv_put_delayed.eq(usb_core.data_recv_put),
            data_recv_payload_delayed.eq(usb_core.data_recv_payload),
        ]

        # Wire up debug signals if required
        if debug:
            debug_bridge = USBWishboneBridge(usb_core)
            self.submodules.debug_bridge = ClockDomainsRenamer("usb_12")(debug_bridge)
            self.comb += [
                debug_packet_detected.eq(~self.debug_bridge.n_debug_in_progress),
                debug_sink_data.eq(self.debug_bridge.sink_data),
                debug_sink_data_ready.eq(self.debug_bridge.sink_valid),
                debug_ack_response.eq(self.debug_bridge.send_ack | self.debug_bridge.sink_valid),
            ]

        self.comb += [
            # This needs to be correct *before* token is finished, everything
            # else uses registered outputs.
            usb_core.sta.eq((~(have_response | response_ack) & ~debug_packet_detected) & ~debug_sink_data_ready),
            usb_core.arm.eq(((have_response | response_ack) & ~debug_packet_detected) | debug_ack_response),
            usb_core.dtb.eq(dtb_polarity | debug_packet_detected),

            If(debug_packet_detected,
                debug_data_mux.eq(debug_sink_data),
                debug_data_ready_mux.eq(debug_sink_data_ready),
            ).Else(
                debug_data_mux.eq(out_buffer_rd.dat_r),
                debug_data_ready_mux.eq(response_len > 0),
            ),
            out_buffer_rd.adr.eq(response_addr),
            usb_core.data_send_have.eq(debug_data_ready_mux),
            usb_core.data_send_payload.eq(debug_data_mux),
            have_response.eq(response_len > 0),
        ]

        # Function for generating an "if" and eq limiting a value to a maximum.
        # Used to limit the response lengths.
        def limit_eq(var, value, limiting_value):
            return If(value > limiting_value, var.eq(limiting_value)).Else(var.eq(value))
        
        # Build cases for reads of USB descriptors.
        descriptor_cases = {
            descriptor_id: [
                response_addr.eq(descriptor_start_address[descriptor_id]),
                limit_eq(response_len, wLength, len(usb_descriptors[descriptor_id]))
                ]
             for descriptor_id in usb_descriptors.keys()}
        
        self.sync += [
            last_start.eq(usb_core.start),
            If(last_start,
                If(usb_core.tok == PID.SETUP,
                    setup_index.eq(0),
                    dtb_polarity.eq(1),
                    response_len.eq(0),
                ).Elif(transaction_queued,
                    response_ack.eq(1),
                    transaction_queued.eq(0),
                    address.eq(new_address),
                )
            ),
            If(usb_core.tok == PID.SETUP,
                If(data_recv_put_delayed,
                    If(setup_index < 8,
                        setup_index.eq(setup_index + 1),
                    ),
                    Case(setup_index, {
                        0: bmRequestType.eq(data_recv_payload_delayed),
                        1: bRequest.eq(data_recv_payload_delayed),
                        2: wValue.eq(data_recv_payload_delayed),
                        3: wValue.eq(Cat(wValue[0:8], data_recv_payload_delayed)),
                        4: wIndex.eq(data_recv_payload_delayed),
                        5: wIndex.eq(Cat(wIndex[0:8], data_recv_payload_delayed)),
                        6: wLength.eq(data_recv_payload_delayed),
                        7: wLength.eq(Cat(wLength[0:8], data_recv_payload_delayed)),
                    }),
                ),
            ),


            # Handle USB control endpoint commands.
            If(usb_core.setup,
                   Case (bmRequestType, {
                       0x80: If(bRequest == 0x06,
                                    Case(wValue, descriptor_cases)).Elif(
                           bRequest == 0x00,
                           response_addr.eq(usb_device_status_report_address),
                           limit_eq(response_len, wLength, len(usb_device_status_report))
                           ),
                              # MS Extended Compat ID OS Feature
                0xc0: [
                    response_addr.eq(usb_wcid_descriptor_address),
                    limit_eq(response_len, wLength, len(usb_wcid_descriptor))
                    ],
                # Set Address / Configuration
                0x00: [
                    response_ack.eq(1),
                    # Set Address
                    If(bRequest == 0x05,
                           new_address.eq(wValue[0:7]),
                           )
                    ]
                })
            ),
            If(usb_core.data_send_get,
                response_ack.eq(1),
                response_addr.eq(response_addr + 1),
                If(response_len,
                    response_len.eq(response_len - 1),
                ),
            ),
            If(self.data_recv_put_delayed,
                response_ack.eq(0),
                transaction_queued.eq(1),
            ),
        ]

        self.sync += [
            If(usb_core.error,
                usb_core.reset.eq(1),
            ),
        ]
        
