import coreir
import peak
from hwtypes import BitVector

#Represents a single rewrite rule that can be applied to a flattened CoreIR graph
class RewriteRule:
    def __call__(self,c,app):
        raise NotImplementedError

#Only works with a single debug string
class Peak1to1(RewriteRule):
    def __init__(self,coreir_prim : coreir.module.Module, peak_prim : coreir.module.Module, prim_instr : peak.ISABuilder, io_mapping):
        print(io_mapping)
        self.coreir_prim = coreir_prim
        self.prim_instr = prim_instr
        #Actually construct the coreir definition
        coreir_def = coreir_prim.new_definition()
        c = coreir_prim.context
        param_name = prim_instr.__class__.__name__
        modvalues = c.new_values({param_name : str(prim_instr)})

        peak_inst = coreir_def.add_module_instance(name="inst",module=peak_prim,config=modvalues)
        for coreir_port,peak_port in io_mapping.items():
            print(coreir_port,peak_port)
            pio = peak_inst.select(peak_port)
            if coreir_port == "0":
                coreir.connect_const(pio,0)
            else:
                cio = coreir_def.interface.select(coreir_port)
                coreir_def.connect(pio,cio)
        self.coredef = coreir_def

    #returns a map from instance name to peak instr
    def __call__(self,app : coreir.module.Module):
        c = app.context
        mdef = app.definition
        assert mdef
        mapped_instances = {}
        for inst in mdef.instances:
            inst_mod = inst.module
            if inst_mod == self.coreir_prim:
                mapped_instances[inst.name+"$inst"] = self.prim_instr
                inst_mod.definition = self.coredef
                coreir.inline_instance(inst)

        return mapped_instances

class PeakIO(RewriteRule):
    #Interpreting is_input as an input to the fabric which indicates the io_port_name is an output
    def __init__(self, width, is_input, io_prim : coreir.module.Module):
        io_port_name = None
        for port_name, port_type in io_prim.type.items():
            if port_type.is_output() and is_input:
                io_port_name = port_name
            elif port_type.is_input() and not is_input:
                io_port_name = port_name
        assert io_port_name is not None

        assert io_port_name in dict(io_prim.type.items())
        assert io_prim.type[io_port_name].is_input() == (not is_input)
        assert io_prim.type[io_port_name].is_output() == is_input
        self.io_prim = io_prim
        self.is_input = is_input
        self.io_port_name = io_port_name
        self.width = width

    def __call__(self,app : coreir.module.Module):
        c = app.context
        mdef = app.definition
        io = mdef.interface
        for port_name, port_type in app.type.items():
            if port_type.size != self.width:
                continue
            if port_type.is_input() != self.is_input:
                continue
            #This is a valid port
            pt = mdef.add_passthrough(io.select(port_name))
            
            io_inst = mdef.add_module_instance(name=f"io_{port_name}",module=self.io_prim)
            mdef.connect(pt.select("in"),io_inst.select(self.io_port_name))
            mdef.disconnect(pt.select("in"),io.select(port_name))
            coreir.inline_instance(pt)

#Const_mapping
#mapping = dict(
#    data0=("rega","data0")
#    data1=("regb","data1")
#)

class PeakConstantRewrite(RewriteRule):
    def __init__(self, pe : coreir.module.Module, const_mapping : dict, const_mode, width=16):
        assert width !=1
        self.const = c.get_namespace("coreir").generators['const'](width=width)
        self.pe = peak_prim
    def __call__(self,app : coreir.module.Module):
        c = app.context
        mdef = app.definition
        for inst in mdef.instances:
            inst_mod = inst.module
            if inst_mod == pe:
                #check all the ports of the PE
                for (port_name,mapping) in const_mappings:
                    port = inst.select(port_name)
                    port_driver = port.source
                    port_driver.is_select_of_instance
                    port_driver.is_select_of_interface
                    #Check if this is connected to a constant
                    port.dr

                #Need to check what this is connected to.
                out = inst.select("out")
                inst_conns = out.inst_connections
                io_conns = out.io_connections
                if len(io_conns) !=0:
                    continue
                if len(inst_conns) !=1:
                    continue
                other_conn, other_inst = inst_conns[0]
                if other_inst.module == pe:
                    peak_instr = other_inst._peak_inst_
                    peak_port = other_conn.selectpath[1]
                    if peak_port in const_mapping:
                        #Finally we will actually replace the constant
                        const_val = inst.modargs["value"]
                        mode_path,const_path = const_mapping[peak_port]
                        new_instr = peak_instr.set_value(mode_path,const_mode)
                        new_instr = new_instr.set_value(const_path,const_val)
                        other_inst._peak_inst_ = new_instr
                        
                        
                    

#For now this should is just a constant inside a PE
#Assumes that the pe instance has the instruction attached to it in _peak_inst_
#class PeakConstantRewrite(RewriteRule):
#    def __init__(self, pe : coreir.module.Module, const_mapping : dict, const_mode, width=16):
#        assert width !=1
#        self.const = c.get_namespace("coreir").generators['const'](width=width)
#        self.pe = peak_prim
#    def __call__(self,app : coreir.module.Module):
#        c = app.context
#        mdef = app.definition
#        for inst in mdef.instances:
#            inst_mod = inst.module
#            if inst_mod == self.const:
#                #Need to check what this is connected to.
#                out = inst.select("out")
#                inst_conns = out.inst_connections
#                io_conns = out.io_connections
#                if len(io_conns) !=0:
#                    continue
#                if len(inst_conns) !=1:
#                    continue
#                other_conn, other_inst = inst_conns[0]
#                if other_inst.module == pe:
#                    peak_instr = other_inst._peak_inst_
#                    peak_port = other_conn.selectpath[1]
#                    if peak_port in const_mapping:
#                        #Finally we will actually replace the constant
#                        const_val = inst.modargs["value"]
#                        mode_path,const_path = const_mapping[peak_port]
#                        new_instr = peak_instr.set_value(mode_path,const_mode)
#                        new_instr = new_instr.set_value(const_path,const_val)
#                        other_inst._peak_inst_ = new_instr
#                        
#                        
#                    
#
#                #Turn this const into a PE
#                peak_inst = coreir_def.add_module_instance(name="inst",module=peak_prim,config=modvalues)
>>>>>>> Stashed changes

