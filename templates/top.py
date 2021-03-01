#!/usr/bin/env python3
import argparse
import json
import os
import math

def axis_port(bus_name, bus_type, veclen):
    reverse = bus_type.startswith('m')
    primary_direction = 'output' if reverse else 'input '
    secondary_direction = 'input ' if reverse else 'output'
    vector_width = f'[{veclen-1}:0]' if veclen > 1 else ''
    return f'''
    {primary_direction} wire                            {bus_type}_{bus_name}_tvalid,
    {primary_direction} wire {vector_width}[C_AXIS_TDATA_WIDTH-1:0]   {bus_type}_{bus_name}_tdata,
    {secondary_direction} wire                            {bus_type}_{bus_name}_tready,
    {primary_direction} wire [C_AXIS_TDATA_WIDTH/8-1:0] {bus_type}_{bus_name}_tkeep,
    {primary_direction} wire                            {bus_type}_{bus_name}_tlast,
    '''

def axis_assignment(bus_name, bus_type):
    return f'''
    .{bus_type}_{bus_name}_tvalid ( {bus_type}_{bus_name}_tvalid ),
    .{bus_type}_{bus_name}_tdata  ( {bus_type}_{bus_name}_tdata ),
    .{bus_type}_{bus_name}_tready ( {bus_type}_{bus_name}_tready ),
    .{bus_type}_{bus_name}_tkeep  ( {bus_type}_{bus_name}_tkeep ),
    .{bus_type}_{bus_name}_tlast  ( {bus_type}_{bus_name}_tlast ),
    '''

def kernel_parameter_wire(name, bits):
    return f'wire [{bits-1}:0] {name};\n'

def ctrl_kernel_parameter(name):
    return f'    .{name} ( {name} ),\n'

def top(kernel_name, ctrl_addr_width, ports, kernel_parameter_wires, ctrl_kernel_parameters, bus_assignments):
    return f'''`default_nettype none
`timescale 1 ns / 1 ps

module {kernel_name}_top #(
    parameter integer C_S_AXI_CONTROL_ADDR_WIDTH = {ctrl_addr_width},
    parameter integer C_S_AXI_CONTROL_DATA_WIDTH = 32,
    parameter integer C_AXIS_TDATA_WIDTH         = 32
)
(
    // Control AXI-Lite bus
    input  wire                                    s_axi_control_awvalid,
    output wire                                    s_axi_control_awready,
    input  wire [C_S_AXI_CONTROL_ADDR_WIDTH-1:0]   s_axi_control_awaddr,
    input  wire                                    s_axi_control_wvalid,
    output wire                                    s_axi_control_wready,
    input  wire [C_S_AXI_CONTROL_DATA_WIDTH-1:0]   s_axi_control_wdata,
    input  wire [C_S_AXI_CONTROL_DATA_WIDTH/8-1:0] s_axi_control_wstrb,
    input  wire                                    s_axi_control_arvalid,
    output wire                                    s_axi_control_arready,
    input  wire [C_S_AXI_CONTROL_ADDR_WIDTH-1:0]   s_axi_control_araddr,
    output wire                                    s_axi_control_rvalid,
    input  wire                                    s_axi_control_rready,
    output wire [C_S_AXI_CONTROL_DATA_WIDTH-1:0]   s_axi_control_rdata,
    output wire [2-1:0]                            s_axi_control_rresp,
    output wire                                    s_axi_control_bvalid,
    input  wire                                    s_axi_control_bready,
    output wire [2-1:0]                            s_axi_control_bresp,
{ports}
    input  wire ap_clk,
    input  wire ap_rst_n
);

(* DONT_TOUCH = "yes" *)
reg  areset = 1'b0;
wire ap_idle;
reg  ap_idle_r = 1'b1;
wire ap_done;
reg  ap_done_r = 1'b0;
wire ap_done_w;
wire ap_start;
reg  ap_start_r = 1'b0;
wire ap_start_pulse;

{kernel_parameter_wires}

always @(posedge ap_clk) begin
    areset <= ~ap_rst_n;
end

always @(posedge ap_clk) begin
    begin
        ap_start_r <= ap_start;
    end
end
assign ap_start_pulse = ap_start & ~ap_start_r;

always @(posedge ap_clk) begin
    if (areset) begin
        ap_idle_r <= 1'b1;
    end else begin
        ap_idle_r <= ap_done ? 1'b1 : ap_start_pulse ? 1'b0 : ap_idle;
    end
end
assign ap_idle = ap_idle_r;

always @(posedge ap_clk) begin
    if (areset) begin
        ap_done_r <= 1'b0;
    end else begin
        ap_done_r <= ap_done ? 1'b0 : ap_done_w;
    end
end
assign ap_done = ap_done_r;

{kernel_name}_control #(
    .C_S_AXI_ADDR_WIDTH ( C_S_AXI_CONTROL_ADDR_WIDTH ),
    .C_S_AXI_DATA_WIDTH ( C_S_AXI_CONTROL_DATA_WIDTH )
)
inst_{kernel_name}_control (
    .ACLK       ( ap_clk ),
    .ARESET     ( areset ),
    .ACLK_EN    ( 1'b1 ),
    .AWVALID    ( s_axi_control_awvalid ),
    .AWREADY    ( s_axi_control_awready ),
    .AWADDR     ( s_axi_control_awaddr ),
    .WVALID     ( s_axi_control_wvalid ),
    .WREADY     ( s_axi_control_wready ),
    .WDATA      ( s_axi_control_wdata ),
    .WSTRB      ( s_axi_control_wstrb ),
    .ARVALID    ( s_axi_control_arvalid ),
    .ARREADY    ( s_axi_control_arready ),
    .ARADDR     ( s_axi_control_araddr ),
    .RVALID     ( s_axi_control_rvalid ),
    .RREADY     ( s_axi_control_rready ),
    .RDATA      ( s_axi_control_rdata ),
    .RRESP      ( s_axi_control_rresp ),
    .BVALID     ( s_axi_control_bvalid ),
    .BREADY     ( s_axi_control_bready ),
    .BRESP      ( s_axi_control_bresp ),
    .ap_start   ( ap_start ),
    .ap_done    ( ap_done ),
    .ap_ready   ( ap_done ),
    .ap_idle    ( ap_idle ),
{ctrl_kernel_parameters}
    .interrupt  ( )
);

{kernel_name}
inst_{kernel_name} (
{ctrl_kernel_parameters}
{bus_assignments}
    .ap_start  ( ap_start ),
    .ap_done   ( ap_done_w ),
    .ap_aclk   ( ap_clk ),
    .ap_areset ( areset )
);

endmodule
`default_nettype wire
'''

def generate_from_config(config):
    base_addr = 0x10
    total_bytes = base_addr
    kernel_parameter_wires = ''
    ctrl_kernel_parameters = ''

    for _, params in config['params'].items():
        for name, bits in params.items():
            kernel_parameter_wires += kernel_parameter_wire(name, bits)
            ctrl_kernel_parameters += ctrl_kernel_parameter(name)
            total_bytes += bits // 8

    ctrl_addr_width = math.ceil(math.log2(total_bytes))

    ports = ''
    bus_assignments = ''
    for name, (bus_type, veclen) in config['buses'].items():
        if bus_type.endswith('axis'):
            ports += axis_port(name, bus_type, veclen)
            bus_assignments += axis_assignment(name, bus_type)
        else:
            # TODO reader and writers? If the kernel has regular AXI buses?
            print ('Error, currently only streaming AXI busses are allowed')
            quit(1)

    return top(config['name'], ctrl_addr_width, ports, kernel_parameter_wires, ctrl_kernel_parameters, bus_assignments)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Script for generating a top-level RTL file')

    parser.add_argument('config', nargs=1,
            help='The config file describing the core')
    parser.add_argument('-o', '--output', metavar='<file>', nargs=1,
            default=['package_kernel.tcl'],
            help='The output path for the resulting tcl script')
    parser.add_argument('-f', '--force', action='store_true',
            help='Toggles whether output file should be overwritten')

    args = parser.parse_args()

    if not os.path.exists(args.config[0]):
        print (f'Error, {args.config} does not exist')
        quit(1)
    with open(args.config[0], 'r') as f:
        config = json.load(f)

    file_str = generate_from_config(config)

    if not args.force and os.path.exists(args.output[0]):
        print (f'Error, "{args.output[0]}" already exists. Add -f flag to overwrite')
        quit(1)
    with open(args.output[0], 'w') as f:
        f.write(file_str)

