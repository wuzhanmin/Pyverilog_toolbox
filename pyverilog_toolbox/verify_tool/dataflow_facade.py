#-------------------------------------------------------------------------------
# get_dataflow_facade.py
#
# interface of register map analyzer
#
#
# Copyright (C) 2015, Ryosuke Fukatani
# License: Apache 2.0
#-------------------------------------------------------------------------------


import sys
import os
import pyverilog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) )

import pyverilog.controlflow.controlflow_analyzer as controlflow_analyzer
from optparse import OptionParser
import pyverilog.utils.util as util
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.optimizer import VerilogDataflowOptimizer
from bindlibrary import BindLibrary
from pyverilog.controlflow.controlflow_analyzer import VerilogControlflowAnalyzer

class dataflow_facade(VerilogControlflowAnalyzer):
    """ [CLASSES]
        Facade pattern for getting dataflow.
        You can get dataflow by dataflow_facade(Verilog file name).
        If commandline option exists, first argument is regard as verilog file name.
    """
    def __init__(self, code_file_name, topmodule='', config_file=None):
        topmodule, terms, binddict, resolved_terms, resolved_binddict, constlist, fsm_vars = self.get_dataflow(code_file_name)
        VerilogControlflowAnalyzer.__init__(self, topmodule, terms, binddict,
        resolved_terms, resolved_binddict,constlist,fsm_vars)
        self.binds = BindLibrary(binddict, terms)

    def get_dataflow(self, code_file_name, topmodule='', config_file=None):
        optparser = OptionParser()
        optparser.add_option("-t","--top",dest="topmodule",
                             default="TOP",help="Top module, Default=TOP")

        optparser.add_option("-I","--include",dest="include",action="append",
                             default=[],help="Include path")
        optparser.add_option("-D",dest="define",action="append",
                             default=[],help="Macro Definition")
        optparser.add_option("-S",dest="config_file",default=[],help="config_file")
        optparser.add_option("-s","--search",dest="searchtarget",action="append",
                             default=[],help="Search Target Signal")

        (options, args) = optparser.parse_args()

        if args:
            filelist = args
        elif code_file_name:
            if hasattr(code_file_name, "__iter__"):
                filelist = code_file_name
            else:
                filelist = (code_file_name,)
        else:
            raise Exception("Verilog file is not assigned.")

        for f in filelist:
            if not os.path.exists(f): raise IOError("file not found: " + f)

        if not topmodule:
            topmodule = options.topmodule

        analyzer = VerilogDataflowAnalyzer(filelist, topmodule,
                                           preprocess_include=options.include,
                                           preprocess_define=options.define)
        analyzer.generate()

        directives = analyzer.get_directives()
        terms = analyzer.getTerms()
        binddict = analyzer.getBinddict()

        optimizer = VerilogDataflowOptimizer(terms, binddict)

        optimizer.resolveConstant()
        resolved_terms = optimizer.getResolvedTerms()
        resolved_binddict = optimizer.getResolvedBinddict()
        constlist = optimizer.getConstlist()
        if config_file:
            self.config_file = config_file
        elif options.config_file:
            self.config_file = options.config_file

        fsm_vars = (['fsm', 'state', 'count', 'cnt', 'step', 'mode'] + options.searchtarget)
        return options.topmodule, terms, binddict, resolved_terms, resolved_binddict, constlist, fsm_vars

    def make_term_ref_dict(self):
        self.term_ref_dict ={}
        for tv,tk,bvi,bit,term_lsb in self.binds.walk_reg_each_bit():
            if 'Rename' in tv.termtype: continue
            target_tree = self.makeTree(tk)
            tree_list = self.binds.extract_all_dfxxx(target_tree, set([]), bit - term_lsb, pyverilog.dataflow.dataflow.DFTerminal)
            for tree, bit in tree_list:
                if str(tree) not in self.term_ref_dict.keys():
                    self.term_ref_dict[str(tree)] = set([])
                self.term_ref_dict[str(tree)].add(str(tk))

    def make_extract_dfterm_dict(self):
        return_dict = {}
        binds = BindLibrary(self.resolved_binddict, self.resolved_terms)
        for tv,tk,bvi,bit,term_lsb in binds.walk_reg_each_bit():
            tree = self.makeTree(tk)
            trees = binds.extract_all_dfxxx(tree, set([]), bit - term_lsb, pyverilog.dataflow.dataflow.DFTerminal)
            return_dict[(str(tk), bit)] = set([str(tree) for tree in trees])
            #print str(tk) + '[' + str(bit) + ']: ' + str(trees)
            #return_str += str(tk) + '[' + str(bit) + ']: ' + str(trees)
        return return_dict

    def print_dataflow(self):
        """[FUNCTIONS]
        print dataflow information.
        Compatible with Pyverilog. (Mainly used in gui_main.py)
        """
        terms = self.binds._terms
        print('Term:')
        for tk, tv in sorted(terms.items(), key=lambda x:len(x[0])):
            print(tv.tostr())

        binddict = self.binds._binddict
        print('Bind:')
        for bk, bv in sorted(binddict.items(), key=lambda x:len(x[0])):
            for bvi in bv:
                print(bvi.tostr())

    def print_controlflow(self):
        """[FUNCTIONS]
        print controlflow information.
        Compatible with Pyverilog. (Mainly used in gui_main.py)
        """
        fsms = self.getFiniteStateMachines()

        for signame, fsm in fsms.items():
            print('# SIGNAL NAME: %s' % signame)
            print('# DELAY CNT: %d' % fsm.delaycnt)
            fsm.view()
            if not options.nograph:
                fsm.tograph(filename=util.toFlatname(signame)+'.'+options.graphformat, nolabel=options.nolabel)
            loops = fsm.get_loop()
            print('Loop')
            for loop in loops:
                print(loop)

if __name__ == '__main__':
    #df = dataflow_facade("../testcode/complex_partselect.v")
    df = dataflow_facade("../testcode/regmap2.v")
    df.print_dataflow()
    df.print_controlflow()
