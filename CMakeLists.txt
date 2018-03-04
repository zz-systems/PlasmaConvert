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
        COMMAND python3 ${converter} $<TARGET_FILE:${target}> ${memory.template} ${target}_ram_image.vhd ${target}_ram_image.bin
        DEPENDS ${converter}
        COMMENT "Converting binary to VHD memory image using ${converter}"
    )
endfunction()

set(convert.cmd ${CMAKE_CURRENT_LIST_DIR}/convert.py CACHE FILEPATH "Legacy converter location")
set(convertnew.cmd ${CMAKE_CURRENT_LIST_DIR}/convertnew.py CACHE FILEPATH "New converter location")
set(memory.template ${CMAKE_CURRENT_LIST_DIR}/ram_xilinx.vhd CACHE FILEPATH "Memory template file")


function(postprocess_binary target)
    convert_to_vhd_internal(${target} ${convert.cmd})
endfunction()

function(postprocess_binary_new target)
    convert_to_vhd_internal(${target} ${convertnew.cmd})
endfunction()
