function (rtllib_rtl_target RTL_KERNEL RTLLIB_SRC_DIR RTLLIB_TCL_DIR RTLLIB_GEN_DIR RTLLIB_MODULES RTLLIB_XO)
    # Files and directories for the kernel
    set (RTLLIB_HDL_DIR        "${RTLLIB_SRC_DIR}/hdl")
    set (RTLLIB_KERNEL_DIR     "${RTLLIB_HDL_DIR}/${RTL_KERNEL}")
    file(GLOB RTLLIB_SRCS      "${RTLLIB_KERNEL_DIR}/*.*v")
    set (RTLLIB_CTRL           "${RTLLIB_KERNEL_DIR}/${RTL_KERNEL}_Control.v")
    if (NOT EXISTS "${RTLLIB_CTRL}")
        set (RTLLIB_SRCS ${RTLLIB_SRCS} "${RTLLIB_GEN_DIR}/${RTL_KERNEL}_Control.v")
    endif()
    set (RTLLIB_TOP            "${RTLLIB_KERNEL_DIR}/${RTL_KERNEL}_top.v")
    if (NOT EXISTS "${RTLLIB_TOP}")
        set (RTLLIB_SRCS ${RTLLIB_SRCS} "${RTLLIB_GEN_DIR}/${RTL_KERNEL}_top.v")
    endif()
    set (RTLLIB_PKG            "${RTLLIB_TCL_DIR}/${RTL_KERNEL}_package.tcl")
    set (RTLLIB_SYNTH          "${RTLLIB_TCL_DIR}/${RTL_KERNEL}_synth.tcl")
    set (RTLLIB_TMP_DIR        "${CMAKE_CURRENT_BINARY_DIR}/tmp")
    set (RTLLIB_LOG_DIR        "${CMAKE_CURRENT_BINARY_DIR}/log")
    set (RTLLIB_VIVADO_TMP_DIR "${RTLLIB_TMP_DIR}/vivado")

    # Package the kernel
    set (RTLLIB_VIVADO_PKG_FLAGS
        -mode batch
        -log "${RTLLIB_LOG_DIR}/vivado_${RTL_KERNEL}.log"
        -journal "${RTLLIB_LOG_DIR}/vivado_${RTL_KERNEL}.jou"
        -source ${RTLLIB_PKG}
        -tclargs
            ${RTLLIB_XO}
            ${RTL_KERNEL}_top
            ${RTLLIB_VIVADO_TMP_DIR}/${RTL_KERNEL}
            ${RTLLIB_KERNEL_DIR}
            ${RTLLIB_MODULES}
            ${RTLLIB_GEN_DIR}
    )
    add_custom_command(
        OUTPUT  ${RTLLIB_XO}
        COMMAND ${Vitis_VIVADO} ${RTLLIB_VIVADO_PKG_FLAGS}
        DEPENDS ${RTLLIB_PKG} ${RTLLIB_SRCS}
    )

    # Make targets for elaborate and synth, for verifying the RTL code
    set (RTLLIB_VIVADO_SYNTH_FLAGS
        -mode batch
        -log "${RTLLIB_LOG_DIR}/vivado_synth_${RTL_KERNEL}.log"
        -journal "${RTLLIB_LOG_DIR}/vivado_synth_${RTL_KERNEL}.jou"
        -source ${RTLLIB_SYNTH}
        -tclargs
            ${RTLLIB_KERNEL_DIR}
            ${RTL_KERNEL}
            "${RTLLIB_VIVADO_TMP_DIR}/${RTL_KERNEL}_synth"
            ${RTLLIB_MODULES}
            ${RTLLIB_GEN_DIR}
    )
    add_custom_target(rtllib_elaborate_${PROJECT_NAME}_${RTL_KERNEL}
        COMMAND ${Vitis_VIVADO} ${RTLLIB_VIVADO_SYNTH_FLAGS} -rtl
        DEPENDS ${RTLLIB_SYNTH} ${RTLLIB_SRCS}
    )
    add_custom_target(rtllib_synth_${PROJECT_NAME}_${RTL_KERNEL}
        COMMAND ${Vitis_VIVADO} ${RTLLIB_VIVADO_SYNTH_FLAGS}
        DEPENDS ${RTLLIB_SYNTH} ${RTLLIB_SRCS}
    )
endfunction()
