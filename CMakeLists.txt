cmake_minimum_required(VERSION 2.8.1)
project(plasma-toolchain)

find_package(PythonInterp 3.3 REQUIRED)

if(PYTHONINTERP_FOUND)
    get_filename_component(PYTHON_DIR ${PYTHON_EXECUTABLE} DIRECTORY CACHE)
else()
    message(FATAL_ERROR "Python not found")
endif()


function(convert_to_vhd_internal target converter)
    add_custom_command(
        TARGET ${target}
        POST_BUILD
        COMMAND python3 ${converter} $<TARGET_FILE:${target}> ${target}_ram_image vhd ${memory.template}
        DEPENDS ${converter}
        COMMENT "Converting binary to VHD memory image using ${converter}"
    )
endfunction()

function(convert_to_mif_internal target converter)
    add_custom_command(
        TARGET ${target}
        POST_BUILD
        COMMAND python3 ${converter} $<TARGET_FILE:${target}> ${target}_ram_image mif
        DEPENDS ${converter}
        COMMENT "Converting binary to MIF memory image using ${converter}"
    )
endfunction()

set(convert.cmd ${CMAKE_CURRENT_LIST_DIR}/convert.py CACHE FILEPATH "Converter location")
set(memory.template ${CMAKE_CURRENT_LIST_DIR}/ram_xilinx.vhd CACHE FILEPATH "Memory template file")

add_library(linker_cfg INTERFACE)
target_link_libraries(
        linker_cfg
        INTERFACE
        "-Wl,-T,${CMAKE_CURRENT_LIST_DIR}/plasma.ldscript,-Map,testnew.map,-s,-N")

function(postprocess_binary target)
    convert_to_mif_internal(${target} ${convert.cmd})
endfunction()
