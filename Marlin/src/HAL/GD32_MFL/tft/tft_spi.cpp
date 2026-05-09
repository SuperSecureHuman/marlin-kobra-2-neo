// src/HAL/GD32_MFL/tft_spi.cpp
#include "tft_spi.h"
//#include "../../../lcd/tft_io/ST7789v.h"
#include "../../../lcd/tft_io/tft_io.h"
#include "../HAL.h"
#include "../../../inc/MarlinConfig.h"
#include "../HAL_SPI.h"
#include <Arduino.h>

#ifdef TFT_GENERIC
using namespace hal_bridge;

bool TFT_SPI::tft_busy = false;

// =========================================================
// === BASE LOGIC ===
// =========================================================
void TFT_SPI::set_busy(bool state) { tft_busy = state; }
bool TFT_SPI::get_busy() { return tft_busy; }
bool TFT_SPI::isBusy() { return get_busy(); }

void TFT_SPI::backlight(bool on) {
    // Use direct HAL call for reliability or Arduino API
    digitalWrite(TFT_BACKLIGHT_PIN, on ? HIGH : LOW);
}

void TFT_SPI::abort() {
    set_busy(false);
    spi_cs_control_direct(false);
}

// =========================================================
// === LOW LEVEL (FIXED: NO CS) ===
// =========================================================
// These functions are called FROM INSIDE a transaction (when CS is already LOW).
// They MUST NOT touch CS.

void TFT_SPI::writeReg(uint16_t reg) {
    // NOTE: Do not check busy here, as tft_io already set busy in beginTransaction

    // 1. DC = CMD
    hal_bridge::spi_dc_control_direct(false);

    // 2. Send byte (commands are always 8 bits)
    hal_bridge::spi_write_byte_direct(reg & 0xFF);

    // 3. Wait for completion (so DC does not switch prematurely)
    hal_bridge::spi_wait_for_tx_complete_direct();

    // 4. Restore DC to DATA (default state for tft_io)
    hal_bridge::spi_dc_control_direct(true);
}

void TFT_SPI::writeData(uint16_t data) {
    // 1. Send ONLY THE LOW BYTE (8 bits)
    // Marlin in tft_io.cpp splits 16-bit data into two writeData calls itself.
    hal_bridge::spi_write_byte_direct(data & 0xFF);

    // 2. Wait (to preserve ordering on rapid calls)
    hal_bridge::spi_wait_for_tx_complete_direct();
}

// =========================================================
// === TRANSACTION CONTROL (CS LIVES HERE) ===
// =========================================================

void TFT_SPI::dataTransferBegin(uint16_t dataWidth) {
    if (get_busy()) return;
    set_busy(true);

    // 1. Assert CS (begin transaction)
    hal_bridge::spi_cs_control_direct(true);

    // 2. Default DC = DATA
    hal_bridge::spi_dc_control_direct(true);

    // Errata Fix: Flush bus before start
    hal_bridge::spi_wait_for_tx_complete_direct();

    (void)dataWidth;
}

void TFT_SPI::dataTransferEnd() {
    // 1. Wait for all bytes to transmit
    hal_bridge::spi_wait_for_tx_complete_direct();

    // 2. Deassert CS (end transaction)
    hal_bridge::spi_cs_control_direct(false);

    set_busy(false);
}

// =========================================================
// === BULK WRITE (SELF-MANAGED CS) ===
// =========================================================
// Marlin calls these functions directly, so here WE manage CS.

void TFT_SPI::writeSequence(const uint16_t *data, uint32_t count) {
    if (!data || count == 0) return;
    if (get_busy()) return;
    set_busy(true);

    hal_bridge::spi_cs_control_direct(true); // CS Low
    hal_bridge::spi_dc_control_direct(true); // DATA

    // Cast data to 8-bit view for byte-by-byte transmission
    const uint8_t *byte_stream = (const uint8_t *)data;

    // Total byte count (2 bytes per color word)
    uint32_t bytes_total = count * 2;

    while (bytes_total--) {
        // Take current byte from stream and advance
        hal_bridge::spi_write_byte_direct(*byte_stream++);
    }

    hal_bridge::spi_wait_for_tx_complete_direct();
    hal_bridge::spi_cs_control_direct(false); // CS High
    set_busy(false);
}

void TFT_SPI::writeMultiple(uint16_t color, uint32_t count) {
    if (count == 0) return;
    if (get_busy()) return;
    set_busy(true);

    hal_bridge::spi_cs_control_direct(true); // CS Low
    hal_bridge::spi_dc_control_direct(true); // DATA

    // 1. Get the address of color and view it as a byte array.
    // Marlin has already byte-swapped, so they are in memory in the correct order:
    // [0] -> High byte (MSB), [1] -> Low byte (LSB)
    const uint8_t *color_bytes = (const uint8_t *)&color;

    // 2. Cache bytes into local variables to avoid
    // stack/memory access on each loop iteration.
    uint8_t byte_1 = color_bytes[0];
    uint8_t byte_2 = color_bytes[1];

    while (count--) {
        hal_bridge::spi_write_byte_direct(byte_1);
        hal_bridge::spi_write_byte_direct(byte_2);
    }

    hal_bridge::spi_wait_for_tx_complete_direct();
    hal_bridge::spi_cs_control_direct(false); // CS High
    set_busy(false);
}

// =========================================================
// === INITIALIZATION ===
// =========================================================
void TFT_SPI::init() {
    // 1. Hardware init (bridge only)
    spi_init_direct();
    set_busy(false);

    // NOTE: All Reset logic and command sending (commandList)
    // is in tft_io.cpp -> TFT_IO::initTFT().
    // Do not duplicate it here or there will be a double reset and glitches.

    // Just ensure backlight is configured (in case tft_io skips it)
    pinMode(TFT_BACKLIGHT_PIN, OUTPUT);
}

// =========================================================
// === STUBS (tft_io.cpp logic is used) ===
// =========================================================

uint32_t TFT_SPI::getID() { return 0x8552; } // ID for ST7789

void TFT_SPI::writeSequence_DMA(uint16_t *data, uint32_t count) {
    writeSequence(data, count);
}
void TFT_SPI::writeMultiple_DMA(uint16_t color, uint32_t count) {
    writeMultiple(color, count);
}

#endif // TFT_GENERIC
