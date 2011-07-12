#!/usr/bin/env python
import argparse
from collections import namedtuple
from itertools import product, groupby, chain
import json
from pprint import pprint
import subprocess
import sys

import numpy as np
import scipy as sp

class ConstraintList(object):
    pass

class Constraint(object):
    def __init__(self, keys, values):
        self.keys = keys
        self.values = values

    def __repr__(self):
        constrained = ', '.join('{}={}'.format(k,v) for k,v in zip(self.keys, self.values)) or 'nothing'
        return '<{} constrains {}>'.format(self.__class__.__name__, constrained)

    def __key(self):
        return tuple(chain.from_iterable([self.keys, self.values]))

    def allows(self, result):
        return all(result[k] == v for k, v in zip(self.keys, self.values))

    def allows_count(self, results):
        return len(filter(None, (self.allows(result) for result in results)))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()



class ResultTable(object):
    def __init__(self, results, column_names, row_names):
        self.column_names = column_names
        self.row_names = row_names
        self.results = results
        self.columns = self._constraints(self.column_names)
        self.rows = self._constraints(self.row_names)
        self.table = self._build_table()

    def _constraints(self, keys):
        row_tuples = list(tuple(elem[key] for key in keys) for elem in self.results)
        row_tuples = sorted(set(row_tuples))
        return [Constraint(keys, row_tuple) for row_tuple in row_tuples]

    def _build_table(self):
        table = np.empty((len(self.rows), len(self.columns)), dtype=object)
        for i, row in enumerate(self.rows):
            for j, column in enumerate(self.columns):
                results_for_cell = [result for result in self.results
                                    if row.allows(result) and column.allows(result)]
                if len(results_for_cell) > 1:
                    msg = "Cell {},{} is underconstrained. ".format(i,j)
                    msg += "Row constraint {} and column constraint {} fit {} results\n"\
                        .format(row, column, len(results_for_cell))
                    for i, result in enumerate(results_for_cell):
                        msg += "\t{}: {}\n".format(i+1, result)
                    raise StandardError(msg)
                elif len(results_for_cell) == 1:
                    table[i,j] = results_for_cell[0]

        return table

    def constraint_spans(self, constraints, dim):
        i = 0
        for k, group in groupby(constraints, lambda c: c.values[dim]):
            col_group = list(group)
            yield (i, i + len(col_group)), col_group[0].values[dim]
            i += len(col_group)


class LatexTableRow(object):
    def __init__(self):
        self._cells = []

    def _add_cell(self, name, span, dir, prepend, bf):
        name = name.replace("_", r"\_")
        if bf:
            name = "\\bf{%s}" % name

        if span > 1 and dir == 'col':
            cell_def = "\\multicolumn{%d}{c}{%s}" % (span, name)
        elif span > 1 and dir == 'row':
            cell_def = "\\multirow{%d}{*}{%s}" % (span, name)
        else:
            cell_def = name

        if prepend:
            self._cells = [cell_def] + self._cells
        else:
            self._cells.append(cell_def)

    def append_cell(self, name, span=1, dir='col', bf=False):
        return self._add_cell(name, span, dir, prepend=False, bf=bf)

    def prepend_cell(self, name, span=1, dir='col', bf=False):
        return self._add_cell(name, span, dir, prepend=True, bf=bf)

    def build(self):
        return ' & '.join(self._cells) + r" \\"

class LatexTableFormatter(object):
    def __init__(self, result_table):
        self._rt = result_table

    def build(self):
        lines = []
        lines.extend(self._header())
        lines.extend(self._body())
        lines.extend(self._footer())
        return "\n".join(lines)

    def _header(self):
        prepend_width = len(self._rt.row_names)
        inner_width = self._rt.table.shape[1]
        lines = []
        lines.append("\\begin{tabular}{%s%s}" % ("l"*prepend_width, "c"*inner_width))
        lines.append("\\toprule")

        for i, column_name in enumerate(self._rt.column_names):
            midrules = []
            row = LatexTableRow()
            row.append_cell('', span=prepend_width)
            if i == 0:
                row.append_cell(self._format_legend(column_name), inner_width, bf=True)
                midrules.append("\\cmidrule(lr){%i-%i}" % (prepend_width+1, prepend_width+inner_width))
            else:
                distinct_values = set(constr.values[i-1] for constr in self._rt.columns)
                width = inner_width / len(distinct_values)
                for j in range(len(distinct_values)):
                    row.append_cell(self._format_legend(column_name), width, bf=True)
                    midrules.append("\\cmidrule(lr){%i-%i}" % (1+prepend_width+j*width,
                                                          prepend_width+(j+1)*width ))
            lines.append(row.build())
            lines.extend(midrules)

            row = LatexTableRow()

            row.append_cell('', span=prepend_width)
            for span, name in self._rt.constraint_spans(self._rt.columns, i):
                row.append_cell(self._format_legend(name), span[1] - span[0])
            lines.append(row.build())
            lines.extend(midrules)


#        lines.append("\\cmidrule(lr){%i-%i}" % (prepend_width+1, prepend_width+inner_width))

        # Build type legend
        row = LatexTableRow()
        row.append_cell('', span=prepend_width)
        for i in range(inner_width):
            row.append_cell("\\%")

        lines.append(row.build())
        lines.append("\\midrule")

        # Build row name legend
        row = LatexTableRow()
        for row_name in self._rt.row_names:
            row.append_cell(self._format_legend(row_name), bf=True)
        row.append_cell('', span=inner_width)
        lines.append(row.build())

        return lines


    def _body(self):
        lines = []
        # Iterate over table rows
        for i in range(self._rt.table.shape[0]):
            row = LatexTableRow()
            midrule_above = False

            # Determine if a span begins at this row
            for dim in range(len(self._rt.row_names)):
                found = False
                for span, val in self._rt.constraint_spans(self._rt.rows, dim):
                    if span[0] == i:
                        found = (span, val)
                        if i > 0 and (span[1]-span[0]) > 1:
                            midrule_above = True
                if found:
                    span, val = found
                    row.append_cell(self._format_legend(val), span=span[1]-span[0], dir='row')
                else:
                    row.append_cell('')

            for j in range(self._rt.table.shape[1]):
                row.append_cell(self._format_value(self._rt.table[i,j]))
            if midrule_above:
                lines.append("\\midrule")
            lines.append(row.build())
        return lines


    def _footer(self):
        return ["\\bottomrule", "\\end{tabular}"]

    def _format_value(self, result):
        return "%.02f" % (result['precision']*100)

    def _format_legend(self, name):
        name = name.replace("_", " ")
        return name[0:1].upper() + name[1:]

parser = argparse.ArgumentParser()
parser.add_argument('file', type=argparse.FileType('r'))
parser.add_argument('--rows', nargs='*')
parser.add_argument('--columns', nargs='*')
parser.add_argument('--wrap', action='store_true', help='wraps table in a standalone LaTeX document')
parser.add_argument('--open', action='store_true', help='renders the table as a pdf file and opens the it. Implies --wrap')
args = parser.parse_args()


results = json.loads(args.file.read())
rt = ResultTable(results, row_names=args.rows, column_names=args.columns)
formatter = LatexTableFormatter(rt)

if args.wrap or args.open:
    template = r"""\documentclass{standalone}
\setlength\PreviewBorder{10mm}
\usepackage{graphicx}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{multirow}

\begin{document}
%s
\end{document}"""
else:
    template = "%s"

latex_source = template % formatter.build()

if args.open:
    proc = subprocess.Popen('pdflatex', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write(latex_source)
    proc.stdin.close()
    log = proc.stdout.read()
    ret_code = proc.wait()
    if ret_code == 0:
        subprocess.Popen('open texput.pdf', shell=True)
    else:
        print >>sys.stderr, "PDF file creation failed"
        print >>sys.stderr, log
else:
    print latex_source

