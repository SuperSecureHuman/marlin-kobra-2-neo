/**
 * Marlin 3D Printer Firmware
 * Copyright (c) 2025 MarlinFirmware [https://github.com/MarlinFirmware/Marlin]
 *
 * Based on Sprinter and grbl.
 * Copyright (c) 2011 Camiel Gubbels / Erik van der Zalm
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 */

#include "../platforms.h"

#ifdef ARDUINO_ARCH_MFL

#include "../../inc/MarlinConfig.h"
#include "MarlinSerial.h"

#if ENABLED(EMERGENCY_PARSER)
  #include "../../feature/e_parser.h"

  // Parser states for each port (0-4)
  static EmergencyParser::State e_states[5];

  // Get port index
  static uint8_t get_serial_index(usart::USART_Base base) {
    // Convert base address to index via switch
    // Compiler optimizes this into a jump table
    switch(base) {
      case usart::USART_Base::USART0_BASE: return 0;
      case usart::USART_Base::USART1_BASE: return 1;
      case usart::USART_Base::USART2_BASE: return 2;
      case usart::USART_Base::UART3_BASE:  return 3;
      case usart::USART_Base::UART4_BASE:  return 4;
      case usart::USART_Base::INVALID:     return 0;
    }
    return 0; // Fallback for unrecognized base address
  }

  // Implementation for DMA mode
  #if ENABLED(SERIAL_DMA)
    static size_t dma_shadow_heads[5];
  #endif

  // Implementation for IRQ mode
  #if !ENABLED(SERIAL_DMA)
    // Instance pointers for interrupts
    static MarlinSerial* instances[5];

    // Interrupt handlers for each port
    static void emergency_isr_0() { if (instances[0]) instances[0]->emergency_isr(); }
    static void emergency_isr_1() { if (instances[1]) instances[1]->emergency_isr(); }
    static void emergency_isr_2() { if (instances[2]) instances[2]->emergency_isr(); }
    static void emergency_isr_3() { if (instances[3]) instances[3]->emergency_isr(); }
    static void emergency_isr_4() { if (instances[4]) instances[4]->emergency_isr(); }

    // Handler table
    static constexpr void (*isr_handlers[5])() = {
      emergency_isr_0, emergency_isr_1, emergency_isr_2,
      emergency_isr_3, emergency_isr_4
    };
  #endif
#endif // EMERGENCY_PARSER

using namespace arduino;

// Factory - simple type cast
MarlinSerial& MarlinSerial::get_instance(usart::USART_Base Base, pin_size_t rxPin, pin_size_t txPin) {
  return static_cast<MarlinSerial&>(UsartSerial::get_instance(Base, rxPin, txPin));
}

// Port initialization
#if USING_HW_SERIAL0
  MSerialT MSerial0(true, MarlinSerial::get_instance(usart::USART_Base::USART0_BASE, NO_PIN, NO_PIN));
  arduino::UsartSerial& Serial = MSerial0;
#endif

#if USING_HW_SERIAL1
  MSerialT MSerial1(true, MarlinSerial::get_instance(usart::USART_Base::USART1_BASE, NO_PIN, NO_PIN));
  arduino::UsartSerial& Serial1 = MSerial1;
#endif

#if USING_HW_SERIAL2
  MSerialT MSerial2(true, MarlinSerial::get_instance(usart::USART_Base::USART2_BASE, NO_PIN, NO_PIN));
  arduino::UsartSerial& Serial2 = MSerial2;
#endif

#if USING_HW_SERIAL3
  MSerialT MSerial3(true, MarlinSerial::get_instance(usart::USART_Base::UART3_BASE, NO_PIN, NO_PIN));
  arduino::UsartSerial& Serial3 = MSerial3;
#endif

#if USING_HW_SERIAL4
  MSerialT MSerial4(true, MarlinSerial::get_instance(usart::USART_Base::UART4_BASE, NO_PIN, NO_PIN));
  arduino::UsartSerial& Serial4 = MSerial4;
#endif

// Port initialization
void MarlinSerial::begin(unsigned long baudrate, uint16_t config) {
  // Initialize the base driver
  UsartSerial::begin(baudrate, config, ENABLED(SERIAL_DMA));

  #if ENABLED(EMERGENCY_PARSER)
    uint8_t idx = get_serial_index(usart_.get_base());
    e_states[idx] = EmergencyParser::State::EP_RESET;

    #if ENABLED(SERIAL_DMA)
      dma_shadow_heads[idx] = 0;
    #else
      instances[idx] = this;
      usart_.register_interrupt_callback(usart::Interrupt_Type::INTR_RBNEIE, isr_handlers[idx]);
    #endif
  #endif
}

// Buffer update for DMA mode
void MarlinSerial::updateRxDmaBuffer() {
  // Update data from DMA
  UsartSerial::updateRxDmaBuffer();

  #if ENABLED(EMERGENCY_PARSER) && ENABLED(SERIAL_DMA)
    uint8_t idx = get_serial_index(usart_.get_base());

    auto& ring = usart_.get_rx_buffer();
    size_t current_head = ring.getHead();
    const uint8_t* buffer = ring.data();
    size_t capacity = ring.capacity();

    // Fast exit if no data
    if (capacity == 0) return;

    // Process new data
    size_t& shadow = dma_shadow_heads[idx];
    while (shadow != current_head) {
      emergency_parser.update(e_states[idx], buffer[shadow]);

      shadow++;
      if (shadow >= capacity) shadow = 0;
    }
  #endif
}

// Interrupt handler for IRQ mode
#if !ENABLED(SERIAL_DMA)
void MarlinSerial::emergency_isr() {
  #if ENABLED(EMERGENCY_PARSER)
    // Read byte from register (clears interrupt flag)
    uint8_t c = usart_.receive_data8();

    // Process emergency command
    uint8_t idx = get_serial_index(usart_.get_base());
    emergency_parser.update(e_states[idx], c);
  #endif
}
#endif

#endif // ARDUINO_ARCH_MFL
