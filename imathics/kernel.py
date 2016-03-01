import sys
import traceback

from ipykernel.kernelbase import Kernel

from mathics.core.definitions import Definitions
from mathics.core.evaluation import Evaluation, Message, Result
from mathics.core.expression import Integer
from mathics.core.parser import parse_lines, IncompleteSyntaxError, TranslateError
from mathics.builtin import builtins
from mathics import settings
from mathics.version import __version__
from mathics.doc.doc import Doc


class MathicsKernel(Kernel):
    implementation = 'Mathics'
    implementation_version = '0.1'
    language_info = {
        'version': __version__,
        'name': 'Mathematica',
        'mimetype': 'text/x-mathematica',
    }
    banner = "Mathics kernel"   # TODO

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.definitions = Definitions(add_builtin=True)        # TODO Cache
        self.definitions.set_ownvalue('$Line', Integer(0))  # Reset the line number

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        # TODO update user definitions

        response = {
            'payload': [],
            'user_expressions': {},
        }

        evaluation = Evaluation(self.definitions, out_callback=self.out_callback)
        try:
            results = evaluation.parse_evaluate(code, timeout=settings.TIMEOUT)
        except Exception as exc:
            # internal error
            response['status'] = 'error'
            response['ename'] = 'System:exception'
            response['traceback'] = traceback.format_exception(*sys.exc_info())
            results = []
        else:
            response['status'] = 'ok'

        if not silent:
            for result in results:
                if result.result is not None:
                    data = {
                        'text/plain': result.result,
                        # TODO html / mathjax output
                    }
                    content = {'execution_count': result.line_no, 'data': data, 'metadata': {}}
                    self.send_response(self.iopub_socket, 'execute_result', content)

        response['execution_count'] = self.definitions.get_line()

        return response

    def out_callback(self, out):
        if out.is_message:
            content = {
                'name': 'stderr',
                'text': '{symbol}::{tag}: {text}\n'.format(**out.get_data()),
            }
        elif out.is_print:
            content = {
                'name': 'stdout',
                'text': out.text + '\n',
            }
        else:
            raise ValueError('Unknown out')
        self.send_response(self.iopub_socket, 'stream', content)

    def do_inspect(self, code, cursor_pos, detail_level=0):
        # name = code[:cursor_pos]
        name = code

        if '`' not in name:
            name = 'System`' + name

        try:
            instance = builtins[name]
        except KeyError:
            return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

        doc = Doc(instance.__doc__ or '')    # TODO Handle possible ValueError here
        data = {'text/plain': doc.text(detail_level), 'text/html': doc.html()}        # TODO 'application/x-tex': doc.latex()
        return {'status': 'ok', 'found': True, 'data': data, 'metadata': {}}

    def do_is_complete(self, code):
        try:
            # list forces generator evaluation (parse all lines)
            list(parse_lines(code, self.definitions))
        except IncompleteSyntaxError:
            return {'status': 'incomplete', 'indent': ''}
        except TranslateError:
            return {'status': 'invalid'}
        else:
            return {'status': 'complete'}
