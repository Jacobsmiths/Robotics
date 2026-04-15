# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico2 CACHE STRING "Board type")

 cmake_minimum_required(VERSION 3.13)

# Include the Pico SDK macros
include(pico_sdk_import.cmake)

project(arducam_capture C CXX ASM)

# Initialize the SDK
pico_sdk_init()

add_executable(arducam_capture
    main.cpp
    arduCAM.cpp
    rp2.c
)

# Pull in the required hardware libraries
target_link_libraries(arducam_capture 
    pico_stdlib 
    hardware_spi 
    hardware_i2c
)

# Enable USB output so you can see printf() in a serial monitor
pico_enable_stdio_usb(arducam_capture 1)
pico_enable_stdio_uart(arducam_capture 0)

# Create the .uf2 file for flashing
pico_add_extra_outputs(arducam_capture)