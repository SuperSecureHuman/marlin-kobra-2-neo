// src/HAL/GD32_MFL/tft_spi.h
#pragma once

#include "../../../inc/MarlinConfig.h"
#include "../../platforms.h"
#ifdef ARDUINO_ARCH_MFL
#include "../HAL_SPI.h"

#ifdef TFT_GENERIC

class TFT_SPI {
    static bool tft_busy;

public:
    // Initialization and state
    static void init();
    static void set_busy(bool state);
    static bool get_busy();
    static bool isBusy();
    static void abort();

    // Identification and control
    static uint32_t getID();
    static void backlight(bool on);

    // Geometry
    static void setDisplayAddress(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
    static void setWindow(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
    static void clearScreen(uint16_t color);

    // Transaction control
    static void dataTransferBegin(uint16_t dataWidth = 16);
    static void dataTransferEnd();

    // Low-level write
    // writeReg: uint8_t since display commands are always 8-bit
    static void writeReg(uint16_t reg);

    // writeData: uint16_t to accept colors and coordinates (MSB->LSB)
    // and to avoid compiler overflow warnings with 0xFFFF
    static void writeData(uint16_t data);

    // Init script parser
    static void commandList(const uint16_t *list);

    // Bulk transfer (uint32_t counters for screens > 256x256)
    static void writeSequence(const uint16_t *data, uint32_t count);
    static void writeMultiple(uint16_t color, uint32_t count);

    // DMA-compatible wrappers (in our implementation, call the regular methods)
    static void writeSequence_DMA(uint16_t *data, uint32_t count);
    static void writeMultiple_DMA(uint16_t color, uint32_t count);
};
typedef TFT_SPI TFT_IO_DRIVER;
#endif // TFT_GENERIC
#endif // ARDUINO_ARCH_MFL
