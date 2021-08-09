#!/usr/bin/env python3
import argparse
import json
import os
import math

# TODO general pretty printing would be nice.

def axis_port(bus_name, bus_type, veclen):
    reverse = bus_type.startswith('m')
    primary_direction = 'output' if reverse else 'input '
    secondary_direction = 'input ' if reverse else 'output'
    vector_width = f'[{veclen-1}:0]' if veclen > 1 else ''
    vector_pad = ' ' * len(vector_width)
    return f'''    {primary_direction} wire {vector_pad}                           {bus_type}_{bus_name}_tvalid,
    {primary_direction} wire {vector_width}[C_AXIS_TDATA_WIDTH-1:0]   {bus_type}_{bus_name}_tdata,
    {secondary_direction} wire {vector_pad}                           {bus_type}_{bus_name}_tready,
    {primary_direction} wire {vector_pad}[C_AXIS_TDATA_WIDTH/8-1:0] {bus_type}_{bus_name}_tkeep,
    {primary_direction} wire {vector_pad}                           {bus_type}_{bus_name}_tlast,
'''

def axis_assignment(top_bus_name, bus_name, bus_type):
    return f'''    .{bus_type}_{bus_name}_tvalid ( {bus_type}_{top_bus_name}_tvalid ),
    .{bus_type}_{bus_name}_tdata  ( {bus_type}_{top_bus_name}_tdata  ),
    .{bus_type}_{bus_name}_tready ( {bus_type}_{top_bus_name}_tready ),
    .{bus_type}_{bus_name}_tkeep  ( {bus_type}_{top_bus_name}_tkeep  ),
    .{bus_type}_{bus_name}_tlast  ( {bus_type}_{top_bus_name}_tlast  ),
'''

def clk_rst_ports(count, indent='    '):
    clks = f'{indent}input wire ap_clk,\n'
    rsts = f'{indent}input wire ap_rst_n,\n'

    for i in range(1, count):
        clks += f'{indent}input wire ap_clk_{i+1},\n'
        rsts += f'{indent}input wire ap_rst_n_{i+1},\n'
    return clks + rsts

def ctrl_assignments(indent):
    return f'''{indent}.ap_start  ( ap_start ),
{indent}.ap_done   ( ap_done_w )'''

def ctrl_kernel_parameter(name):
    return f'    .{name} ( {name} ),\n'

def internal_rsts(count):
    rst_flip_regs = '''(* DONT_TOUCH = "yes" *)
reg  areset = 1'b0;
'''
    rst_flips = '''always @(posedge ap_clk) begin
    areset <= ~ap_rst_n;
end
'''

    for i in range(1, count):
        rst_flip_regs += f'''(* DONT_TOUCH = "yes" *)
reg  areset_{i+1} = 1'b0;
'''
        rst_flips += f'''always @(posedge ap_clk_{i+1}) begin
    areset_{i+1} <= ~ap_rst_n_{i+1};
end
'''
    return rst_flip_regs, rst_flips

def kernel(indent, kernel_name, postfix, clk_rst_assignments, bus_assignments, ctrl_assignments):
    return f'''{indent}{kernel_name} inst_{kernel_name}{postfix} (
{indent}{clk_rst_assignments}
{indent}{bus_assignments}
{indent}{ctrl_assignments}
{indent});
'''

def kernel_clk_rst(indent, count):
    clk_assignments = f'{indent}.ap_aclk   ( ap_clk ),\n'
    rst_assignments = f'{indent}.ap_areset ( areset ),\n'

    for i in range(1, count):
        clk_assignments += f'{indent}.ap_aclk_{i+1} ( ap_clk_{i+1} ),\n'
        rst_assignments += f'{indent}.ap_areset_{i+1} ( areset_{i+1} ),\n'

    return clk_assignments + rst_assignments

def kernel_parameter_wire(name, bits):
    return f'wire [{bits-1}:0] {name};\n'

def top(kernel_name, ctrl_addr_width, ports, kernel_parameter_wires, ctrl_kernel_parameters, clks_rsts, rst_flip_regs, rst_flips, kernel_instantiations):
    return f'''`default_nettype none
`timescale 1 ns / 1 ps

module {kernel_name}_top #(
    parameter integer C_S_AXI_CONTROL_ADDR_WIDTH = {ctrl_addr_width},
    parameter integer C_S_AXI_CONTROL_DATA_WIDTH = 32,
    parameter integer C_AXIS_TDATA_WIDTH         = 32
)
(
{clks_rsts}
{ports}
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
    output wire [2-1:0]                            s_axi_control_bresp
);

{rst_flip_regs}
wire ap_idle;
reg  ap_idle_r = 1'b1;
wire ap_done;
reg  ap_done_r = 1'b0;
wire ap_done_w;
wire ap_start;
reg  ap_start_r = 1'b0;
wire ap_start_pulse;

{kernel_parameter_wires}
{rst_flips}
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

{kernel_instantiations}
endmodule
`default_nettype wire
'''

def generate_from_config(config):
    num_clk_rst = config['clocks'] if 'clocks' in config else 1
    clks_rsts = clk_rst_ports(num_clk_rst)

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

    ports = []
    bus_assignments = ''
    unroll_factor = config['unroll'] if 'unroll' in config else 1
    for name, (bus_type, veclen) in config['buses'].items():
        if bus_type.endswith('axis'):
            if unroll_factor == 1:
                ports += [axis_port(name, bus_type, veclen)]
                bus_assignments += axis_assignment(name, name, bus_type)
            else:
                for i in range(unroll_factor):
                    ports += [axis_port(f'{name}_{i}', bus_type, veclen)]
                bus_assignments += axis_assignment(f'{name}_{{i}}', name, bus_type)
        else:
            # TODO reader and writers? If the kernel has regular AXI buses?
            print ('Error, currently only streaming AXI busses are allowed')
            quit(1)
    ports = '\n'.join(ports)

    rst_flip_regs, rst_flips = internal_rsts(num_clk_rst)

    clk_rst_assignments = kernel_clk_rst(' ' * 4, num_clk_rst)

    indent = ''# if unroll_factor == 1 else ' ' * 8
    ctrl_flags = ctrl_assignments(' ' * 4)

    postfix = '' if unroll_factor == 1 else '_{i}'
    kernel_temp = kernel(indent, config['name'], postfix, clk_rst_assignments, bus_assignments, ctrl_flags)
    if unroll_factor > 1:
        kernel_insts = []
        for i in range(unroll_factor):
            kernel_insts += [kernel_temp.format(i=str(i))]
        kernel_inst = '\n'.join(kernel_insts)
    else:
        kernel_inst = kernel_temp

    return top(config['name'], ctrl_addr_width, ports, kernel_parameter_wires, ctrl_kernel_parameters, clks_rsts, rst_flip_regs, rst_flips, kernel_inst)

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

